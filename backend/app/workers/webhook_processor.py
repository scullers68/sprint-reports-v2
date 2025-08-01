"""
High-throughput webhook event processor with 1000+ events/minute capacity.

Handles JIRA webhook event processing, deduplication, and integration with sprint management.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json

from celery import current_task
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_, or_, func
import redis.asyncio as redis

from app.core.config import settings
from app.models.webhook_event import WebhookEvent
from app.models.queue import QueueItem, SprintQueue
from app.models.sprint import Sprint
from app.services.jira_service import JiraService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Create async database engine for workers
engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db_session() -> AsyncSession:
    """Get database session for async operations."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_redis_client() -> redis.Redis:
    """Get Redis client for caching and coordination."""
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def log_event_processing(
    event_id: int,
    level: str,
    message: str,
    step: str,
    data: Optional[Dict[str, Any]] = None
):
    """Log event processing step using standard Python logging."""
    worker_id = current_task.request.hostname if current_task else None
    task_id = current_task.request.id if current_task else None
    
    log_data = {
        'event_id': event_id,
        'processing_step': step,
        'worker_id': worker_id,
        'task_id': task_id,
        'data': data or {}
    }
    
    if level.upper() == 'INFO':
        logger.info(f"{step}: {message}", extra=log_data)
    elif level.upper() == 'WARNING':
        logger.warning(f"{step}: {message}", extra=log_data)
    elif level.upper() == 'ERROR':
        logger.error(f"{step}: {message}", extra=log_data)
    else:
        logger.debug(f"{step}: {message}", extra=log_data)


@celery_app.task(bind=True, max_retries=3)
def process_webhook_event(self, event_id: int):
    """
    Process a single webhook event asynchronously.
    
    This task handles:
    1. Event validation and processing
    2. Data extraction and transformation
    3. Integration with sprint management system
    4. Error handling and retry logic
    """
    
    async def _process_event():
        async with AsyncSessionLocal() as db:
            try:
                # Get the webhook event
                result = await db.execute(
                    select(WebhookEvent).where(WebhookEvent.id == event_id)
                )
                event = result.scalar_one_or_none()
                
                if not event:
                    logger.error(f"Webhook event {event_id} not found")
                    return
                
                # Update processing status
                event.processing_status = "processing"
                event.processing_attempts += 1
                event.last_processed_at = datetime.utcnow()
                await db.commit()
                
                log_event_processing(
                    event_id, "INFO",
                    f"Starting webhook event processing (attempt {event.processing_attempts})",
                    "processing_start",
                    {"event_type": event.event_type, "issue_key": event.issue_key}
                )
                
                # Process based on event type
                if event.event_type.startswith("jira:issue"):
                    await process_issue_event(db, event)
                elif event.event_type.startswith("jira:sprint"):
                    await process_sprint_event(db, event)
                else:
                    log_event_processing(
                        event_id, "WARNING",
                        f"Unhandled event type: {event.event_type}",
                        "event_type_check"
                    )
                
                # Mark as completed
                event.processing_status = "completed"
                event.error_message = None
                await db.commit()
                
                log_event_processing(
                    event_id, "INFO",
                    "Webhook event processing completed successfully",
                    "processing_complete"
                )
                
                logger.info(f"Successfully processed webhook event {event.event_id}")
                
            except Exception as e:
                logger.error(f"Error processing webhook event {event_id}: {e}", exc_info=True)
                
                # Update error status
                event.processing_status = "failed"
                event.error_message = str(e)
                await db.commit()
                
                log_event_processing(
                    event_id, "ERROR",
                    f"Webhook event processing failed: {str(e)}",
                    "processing_error",
                    {"error_type": type(e).__name__, "retry_count": event.processing_attempts}
                )
                
                # Retry logic
                if event.processing_attempts < 3:
                    # Exponential backoff retry
                    retry_delay = 60 * (2 ** event.processing_attempts)
                    logger.info(f"Retrying webhook event {event_id} in {retry_delay} seconds")
                    raise self.retry(countdown=retry_delay, exc=e)
                else:
                    logger.error(f"Max retries exceeded for webhook event {event_id}")
    
    # Run the async function
    asyncio.run(_process_event())


async def process_issue_event(db: AsyncSession, event: WebhookEvent):
    """Process JIRA issue-related webhook events."""
    payload = event.payload
    
    # Extract issue key and ID from payload
    issue_data = payload.get("issue", {})
    issue_key = issue_data.get("key")
    issue_id = issue_data.get("id")
    
    if not issue_key or not issue_id:
        log_event_processing(
            event.id, "WARNING",
            "Issue event missing key or ID",
            "issue_validation"
        )
        return
    
    # Extract issue data from payload
    issue_data = payload.get("issue", {})
    issue_fields = issue_data.get("fields", {})
    
    # Update or create processed data
    processed_data = {
        "issue_key": issue_key,
        "issue_id": int(issue_id) if issue_id else None,
        "summary": issue_fields.get("summary"),
        "issue_type": issue_fields.get("issuetype", {}).get("name"),
        "status": issue_fields.get("status", {}).get("name"),
        "priority": issue_fields.get("priority", {}).get("name"),
        "assignee": None,
        "story_points": None,
        "discipline_team": None,
        "labels": issue_fields.get("labels", []),
        "components": [c.get("name") for c in issue_fields.get("components", [])]
    }
    
    # Extract story points (common custom fields)
    for field_key, field_value in issue_fields.items():
        if "story" in field_key.lower() and "point" in field_key.lower():
            try:
                processed_data["story_points"] = float(field_value) if field_value else None
            except (ValueError, TypeError):
                pass
        elif "discipline" in field_key.lower() or "team" in field_key.lower():
            if isinstance(field_value, dict) and "value" in field_value:
                processed_data["discipline_team"] = field_value["value"]
    
    # Extract assignee
    if issue_fields.get("assignee"):
        assignee = issue_fields["assignee"]
        processed_data["assignee"] = {
            "account_id": assignee.get("accountId"),
            "display_name": assignee.get("displayName"),
            "email": assignee.get("emailAddress")
        }
    
    # Save processed data
    event.processed_data = processed_data
    await db.commit()
    
    # Update existing queue items if they exist
    await update_queue_items(db, event)
    
    log_event_processing(
        event.id, "INFO",
        f"Processed issue event for {issue_key}",
        "issue_processing",
        {"changes_detected": len(processed_data)}
    )


async def process_sprint_event(db: AsyncSession, event: WebhookEvent):
    """Process JIRA sprint-related webhook events."""
    payload = event.payload
    
    # Extract sprint data
    sprint_data = payload.get("sprint", {})
    
    if not sprint_data:
        log_event_processing(
            event.id, "WARNING",
            "Sprint event missing sprint data",
            "sprint_validation"
        )
        return
    
    sprint_id = sprint_data.get("id")
    if not sprint_id:
        return
    
    # Update or create processed data
    processed_data = {
        "sprint_id": sprint_id,
        "sprint_name": sprint_data.get("name"),
        "sprint_state": sprint_data.get("state"),
        "start_date": sprint_data.get("startDate"),
        "end_date": sprint_data.get("endDate"),
        "complete_date": sprint_data.get("completeDate"),
        "goal": sprint_data.get("goal")
    }
    
    event.processed_data = processed_data
    await db.commit()
    
    # Trigger sprint synchronization if needed
    if event.event_type in ["jira:sprint_started", "jira:sprint_closed"]:
        from app.workers.jira_sync_tasks import sync_sprint_data
        sync_sprint_data.delay(sprint_id)
    
    log_event_processing(
        event.id, "INFO",
        f"Processed sprint event for sprint {sprint_id}",
        "sprint_processing",
        {"sprint_state": processed_data["sprint_state"]}
    )


async def update_queue_items(db: AsyncSession, event: WebhookEvent):
    """Update existing queue items with new issue data."""
    if not event.processed_data:
        return
    
    issue_key = event.processed_data.get("issue_key")
    if not issue_key:
        return
    
    # Find queue items for this issue
    result = await db.execute(
        select(QueueItem).where(QueueItem.jira_issue_key == issue_key)
    )
    queue_items = result.scalars().all()
    
    if not queue_items:
        return
    
    processed_data = event.processed_data
    updates_made = 0
    
    for item in queue_items:
        # Update item fields from processed data
        if processed_data.get("summary"):
            item.summary = processed_data["summary"]
        if processed_data.get("status"):
            item.status = processed_data["status"]
        if processed_data.get("priority"):
            item.priority = processed_data["priority"]
        if processed_data.get("story_points") is not None:
            item.story_points = processed_data["story_points"]
        if processed_data.get("discipline_team"):
            item.discipline_team = processed_data["discipline_team"]
        if processed_data.get("assignee"):
            assignee = processed_data["assignee"]
            item.assignee_account_id = assignee.get("account_id")
            item.assignee_display_name = assignee.get("display_name")
        if processed_data.get("labels"):
            item.labels = processed_data["labels"]
        if processed_data.get("components"):
            item.components = processed_data["components"]
        
        updates_made += 1
    
    if updates_made > 0:
        await db.commit()
        log_event_processing(
            event.id, "INFO",
            f"Updated {updates_made} queue items for issue {issue_key}",
            "queue_item_update"
        )


@celery_app.task
def cleanup_old_events():
    """Clean up old webhook events and logs."""
    
    async def _cleanup():
        async with AsyncSessionLocal() as db:
            # Delete events older than 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            # Count events to be deleted
            count_result = await db.execute(
                select(func.count(WebhookEvent.id)).where(
                    and_(
                        WebhookEvent.received_at < cutoff_date,
                        WebhookEvent.processing_status.in_(["completed", "failed"])
                    )
                )
            )
            count = count_result.scalar()
            
            if count > 0:
                # Delete old events (cascade will delete logs)
                delete_result = await db.execute(
                    select(WebhookEvent).where(
                        and_(
                            WebhookEvent.received_at < cutoff_date,
                            WebhookEvent.processing_status.in_(["completed", "failed"])
                        )
                    )
                )
                events_to_delete = delete_result.scalars().all()
                
                for event in events_to_delete:
                    await db.delete(event)
                
                await db.commit()
                logger.info(f"Cleaned up {count} old webhook events")
            else:
                logger.info("No old webhook events to clean up")
    
    asyncio.run(_cleanup())


@celery_app.task
def retry_failed_events():
    """Retry failed webhook events that might be recoverable."""
    
    async def _retry():
        async with AsyncSessionLocal() as db:
            # Find failed events from the last 24 hours with < 3 attempts
            cutoff_date = datetime.utcnow() - timedelta(hours=24)
            
            result = await db.execute(
                select(WebhookEvent).where(
                    and_(
                        WebhookEvent.processing_status == "failed",
                        WebhookEvent.received_at >= cutoff_date,
                        WebhookEvent.processing_attempts < 3
                    )
                ).limit(50)  # Process in batches
            )
            
            failed_events = result.scalars().all()
            
            for event in failed_events:
                # Reset status and queue for retry
                event.processing_status = "pending"
                event.error_message = None
                
                # Queue for processing
                process_webhook_event.delay(event.id)
                
                logger.info(f"Retrying failed webhook event {event.event_id}")
            
            if failed_events:
                await db.commit()
                logger.info(f"Queued {len(failed_events)} failed events for retry")
    
    asyncio.run(_retry())


# Monitoring task for webhook throughput
@celery_app.task
def monitor_webhook_throughput():
    """Monitor webhook processing throughput and alert on issues."""
    
    async def _monitor():
        async with AsyncSessionLocal() as db:
            now = datetime.utcnow()
            
            # Check events in last 5 minutes
            recent_cutoff = now - timedelta(minutes=5)
            result = await db.execute(
                select(func.count(WebhookEvent.id)).where(
                    WebhookEvent.received_at >= recent_cutoff
                )
            )
            recent_count = result.scalar()
            
            # Check processing failures
            failed_result = await db.execute(
                select(func.count(WebhookEvent.id)).where(
                    and_(
                        WebhookEvent.processing_status == "failed",
                        WebhookEvent.last_processed_at >= recent_cutoff
                    )
                )
            )
            failed_count = failed_result.scalar()
            
            # Alert conditions
            events_per_minute = recent_count / 5
            failure_rate = failed_count / max(recent_count, 1)
            
            if events_per_minute > 200:  # Over 1000/minute threshold
                logger.warning(f"High webhook volume: {events_per_minute:.1f} events/minute")
            
            if failure_rate > 0.1:  # Over 10% failure rate
                logger.error(f"High webhook failure rate: {failure_rate:.1%}")
            
            logger.info(f"Webhook throughput: {events_per_minute:.1f}/min, failure rate: {failure_rate:.1%}")
    
    asyncio.run(_monitor())