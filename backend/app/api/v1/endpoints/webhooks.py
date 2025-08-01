"""
JIRA webhook endpoints for real-time event processing.

Handles webhook registration, event receiving, and processing coordination.
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import APIRouter, Request, HTTPException, status, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as redis

from app.core.config import settings
from app.core.database import get_db
from app.models.webhook_event import WebhookEvent
from app.services.jira_service import JiraService

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_redis() -> redis.Redis:
    """Get Redis connection for caching and deduplication."""
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify JIRA webhook signature using HMAC-SHA256.
    
    Args:
        payload: Raw request body
        signature: X-Hub-Signature-256 header value
        secret: Webhook secret from configuration
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature or not signature.startswith('sha256='):
        return False
        
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    received_signature = signature[7:]  # Remove 'sha256=' prefix
    return hmac.compare_digest(expected_signature, received_signature)


async def check_event_deduplication(redis_client: redis.Redis, event_id: str) -> bool:
    """
    Check if event has already been processed using Redis.
    
    Args:
        redis_client: Redis connection
        event_id: Unique event identifier
        
    Returns:
        True if event is duplicate, False if new
    """
    key = f"webhook:processed:{event_id}"
    exists = await redis_client.exists(key)
    
    if not exists:
        # Mark as seen for 24 hours (86400 seconds)
        await redis_client.setex(key, 86400, "1")
        return False
    
    return True


async def extract_event_metadata(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key metadata from JIRA webhook payload.
    
    Args:
        payload: Full webhook payload
        
    Returns:
        Extracted metadata dictionary
    """
    metadata = {
        'event_id': None,
        'event_type': payload.get('webhookEvent'),
        'timestamp': payload.get('timestamp'),
        'user_account_id': None,
        'user_display_name': None,
        'issue_key': None,
        'issue_id': None,
        'project_key': None,
        'priority': 100  # Default priority
    }
    
    # Extract user information
    if 'user' in payload:
        user = payload['user']
        metadata['user_account_id'] = user.get('accountId')
        metadata['user_display_name'] = user.get('displayName')
    
    # Extract issue information
    if 'issue' in payload:
        issue = payload['issue']
        metadata['issue_key'] = issue.get('key')
        metadata['issue_id'] = int(issue.get('id')) if issue.get('id') else None
        if 'fields' in issue and 'project' in issue['fields']:
            metadata['project_key'] = issue['fields']['project'].get('key')
    
    # Generate event ID if not provided
    if not metadata['event_id']:
        # Create deterministic event ID from payload
        payload_str = json.dumps(payload, sort_keys=True)
        metadata['event_id'] = hashlib.sha256(payload_str.encode()).hexdigest()[:32]
    
    # Set priority based on event type
    high_priority_events = [
        'jira:issue_created',
        'jira:issue_updated',
        'jira:issue_deleted',
        'jira:sprint_started',
        'jira:sprint_closed'
    ]
    
    if metadata['event_type'] in high_priority_events:
        metadata['priority'] = 50
    
    return metadata


@router.post("/jira")
async def receive_jira_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Receive and process JIRA webhook events with high throughput.
    
    This endpoint:
    1. Validates webhook signature
    2. Checks for event deduplication
    3. Stores event for background processing
    4. Returns immediate response for high throughput
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        
        # Verify content length
        if len(body) > settings.WEBHOOK_MAX_BODY_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Payload too large. Maximum size: {settings.WEBHOOK_MAX_BODY_SIZE} bytes"
            )
        
        # Verify User-Agent
        user_agent = request.headers.get('User-Agent', '')
        if settings.JIRA_WEBHOOK_USER_AGENT not in user_agent:
            logger.warning(f"Suspicious webhook request from User-Agent: {user_agent}")
        
        # Verify webhook signature
        signature = request.headers.get('X-Hub-Signature-256', '')
        if not verify_webhook_signature(body, signature, settings.JIRA_WEBHOOK_SECRET):
            logger.error("Invalid webhook signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # Parse JSON payload
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
        
        # Extract event metadata
        metadata = await extract_event_metadata(payload)
        
        # Check for event deduplication using Redis
        redis_client = await get_redis()
        is_duplicate = await check_event_deduplication(redis_client, metadata['event_id'])
        
        if is_duplicate:
            logger.info(f"Duplicate event ignored: {metadata['event_id']}")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"status": "duplicate", "event_id": metadata['event_id']}
            )
        
        # Create webhook event record
        webhook_event = WebhookEvent(
            event_id=metadata['event_id'],
            event_type=metadata['event_type'],
            payload=payload
        )
        
        # Save to database
        db.add(webhook_event)
        await db.commit()
        await db.refresh(webhook_event)
        
        # Log the event receipt
        logger.info(f"Webhook event created: {metadata['event_id']} ({metadata['event_type']})")
        
        # Queue for background processing
        from app.workers.webhook_processor import process_webhook_event
        background_tasks.add_task(process_webhook_event, webhook_event.id)
        
        logger.info(f"Webhook event queued: {metadata['event_id']} ({metadata['event_type']})")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "received",
                "event_id": metadata['event_id'],
                "event_type": metadata['event_type'],
                "processing_status": "queued"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing webhook"
        )


@router.get("/events/{event_id}")
async def get_webhook_event(
    event_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get webhook event details and processing status."""
    result = await db.execute(
        select(WebhookEvent).where(WebhookEvent.event_id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook event not found"
        )
    
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "processing_status": event.processing_status,
        "retry_count": event.retry_count,
        "created_at": event.created_at,
        "processed_at": event.processed_at,
        "error_message": event.error_message,
        "processing_duration_ms": event.processing_duration_ms
    }


@router.get("/stats")
async def get_webhook_stats(db: AsyncSession = Depends(get_db)):
    """Get webhook processing statistics and monitoring data."""
    from sqlalchemy import func, and_
    from datetime import timedelta
    
    now = datetime.utcnow()
    hour_ago = now - timedelta(hours=1)
    day_ago = now - timedelta(days=1)
    
    # Count events by status
    status_counts = await db.execute(
        select(
            WebhookEvent.processing_status,
            func.count(WebhookEvent.id).label('count')
        ).group_by(WebhookEvent.processing_status)
    )
    
    # Count events in last hour
    recent_count = await db.execute(
        select(func.count(WebhookEvent.id)).where(
            WebhookEvent.created_at >= hour_ago
        )
    )
    
    # Count events in last day
    daily_count = await db.execute(
        select(func.count(WebhookEvent.id)).where(
            WebhookEvent.created_at >= day_ago
        )
    )
    
    # Count failed events
    failed_count = await db.execute(
        select(func.count(WebhookEvent.id)).where(
            WebhookEvent.processing_status == 'failed'
        )
    )
    
    return {
        "status_counts": {row.processing_status: row.count for row in status_counts},
        "events_last_hour": recent_count.scalar(),
        "events_last_day": daily_count.scalar(),
        "failed_events_total": failed_count.scalar(),
        "timestamp": now.isoformat()
    }


@router.post("/events/{event_id}/retry")
async def retry_webhook_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Retry processing of a failed webhook event."""
    result = await db.execute(
        select(WebhookEvent).where(WebhookEvent.event_id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook event not found"
        )
    
    if event.processing_status not in ['failed', 'completed']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry event with status: {event.processing_status}"
        )
    
    # Reset processing status
    event.processing_status = 'pending'
    event.error_message = None
    event.retry_count += 1
    await db.commit()
    
    # Queue for background processing
    from app.workers.webhook_processor import process_webhook_event
    background_tasks.add_task(process_webhook_event, event.id)
    
    return {
        "status": "retry_queued",
        "event_id": event_id,
        "processing_status": "pending"
    }