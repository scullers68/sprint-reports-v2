"""
JIRA synchronization tasks for background processing.

Handles sprint data synchronization and issue updates triggered by webhooks.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import settings
from app.models.sprint import Sprint
from app.models.queue import SprintQueue, QueueItem
from app.services.jira_service import JiraService
from app.workers.celery_app import celery_app
from app.workers.webhook_processor import AsyncSessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=5, default_retry_delay=120)
def sync_sprint_data(self, sprint_id: int):
    """
    Synchronize sprint data from JIRA triggered by webhook events.
    
    Args:
        sprint_id: JIRA sprint ID to synchronize
    """
    
    async def _sync_sprint():
        async with AsyncSessionLocal() as db:
            try:
                jira_service = JiraService()
                
                # Get sprint data from JIRA
                logger.info(f"Syncing sprint data for sprint {sprint_id}")
                
                # This would typically call JIRA API
                # For now, we'll create a placeholder implementation
                sprint_data = await get_sprint_from_jira(jira_service, sprint_id)
                
                if not sprint_data:
                    logger.warning(f"Sprint {sprint_id} not found in JIRA")
                    return
                
                # Find or create sprint record
                result = await db.execute(
                    select(Sprint).where(Sprint.jira_sprint_id == sprint_id)
                )
                sprint = result.scalar_one_or_none()
                
                if not sprint:
                    # Create new sprint
                    sprint = Sprint(
                        jira_sprint_id=sprint_id,
                        name=sprint_data["name"],
                        state=sprint_data["state"],
                        start_date=sprint_data.get("start_date"),
                        end_date=sprint_data.get("end_date"),
                        goal=sprint_data.get("goal"),
                        board_id=sprint_data.get("board_id")
                    )
                    db.add(sprint)
                    logger.info(f"Created new sprint record for {sprint_id}")
                else:
                    # Update existing sprint
                    sprint.name = sprint_data["name"]
                    sprint.state = sprint_data["state"]
                    sprint.start_date = sprint_data.get("start_date")
                    sprint.end_date = sprint_data.get("end_date")
                    sprint.goal = sprint_data.get("goal")
                    sprint.updated_at = datetime.utcnow()
                    logger.info(f"Updated sprint record for {sprint_id}")
                
                await db.commit()
                
                # If sprint is active, sync associated issues
                if sprint_data["state"] in ["ACTIVE", "CLOSED"]:
                    sync_sprint_issues.delay(sprint_id)
                
                logger.info(f"Successfully synced sprint {sprint_id}")
                
            except Exception as e:
                logger.error(f"Error syncing sprint {sprint_id}: {e}", exc_info=True)
                
                # Retry with exponential backoff
                if self.request.retries < 5:
                    retry_delay = 120 * (2 ** self.request.retries)
                    logger.info(f"Retrying sprint sync for {sprint_id} in {retry_delay} seconds")
                    raise self.retry(countdown=retry_delay, exc=e)
                else:
                    logger.error(f"Max retries exceeded for sprint sync {sprint_id}")
                    raise
    
    asyncio.run(_sync_sprint())


@celery_app.task(bind=True, max_retries=3)
def sync_sprint_issues(self, sprint_id: int):
    """
    Synchronize issues for a specific sprint.
    
    Args:
        sprint_id: JIRA sprint ID
    """
    
    async def _sync_issues():
        async with AsyncSessionLocal() as db:
            try:
                jira_service = JiraService()
                
                logger.info(f"Syncing issues for sprint {sprint_id}")
                
                # Get issues from JIRA
                issues = await get_sprint_issues_from_jira(jira_service, sprint_id)
                
                if not issues:
                    logger.info(f"No issues found for sprint {sprint_id}")
                    return
                
                # Find associated sprint queues
                result = await db.execute(
                    select(SprintQueue)
                    .join(Sprint)
                    .where(Sprint.jira_sprint_id == sprint_id)
                )
                queues = result.scalars().all()
                
                # Update queue items with fresh data
                for queue in queues:
                    await update_queue_with_jira_data(db, queue, issues)
                
                logger.info(f"Synced {len(issues)} issues for sprint {sprint_id} across {len(queues)} queues")
                
            except Exception as e:
                logger.error(f"Error syncing issues for sprint {sprint_id}: {e}", exc_info=True)
                raise self.retry(countdown=300, exc=e)  # 5 minute retry
    
    asyncio.run(_sync_issues())


@celery_app.task(bind=True, max_retries=3)
def sync_issue_data(self, issue_key: str):
    """
    Synchronize individual issue data from JIRA.
    
    Args:
        issue_key: JIRA issue key (e.g., "PROJ-123")
    """
    
    async def _sync_issue():
        async with AsyncSessionLocal() as db:
            try:
                jira_service = JiraService()
                
                logger.info(f"Syncing data for issue {issue_key}")
                
                # Get issue from JIRA
                issue_data = await get_issue_from_jira(jira_service, issue_key)
                
                if not issue_data:
                    logger.warning(f"Issue {issue_key} not found in JIRA")
                    return
                
                # Find all queue items for this issue
                result = await db.execute(
                    select(QueueItem).where(QueueItem.jira_issue_key == issue_key)
                )
                queue_items = result.scalars().all()
                
                # Update each queue item
                for item in queue_items:
                    await update_queue_item_from_jira(item, issue_data)
                
                if queue_items:
                    await db.commit()
                    logger.info(f"Updated {len(queue_items)} queue items for issue {issue_key}")
                else:
                    logger.info(f"No queue items found for issue {issue_key}")
                
            except Exception as e:
                logger.error(f"Error syncing issue {issue_key}: {e}", exc_info=True)
                raise self.retry(countdown=180, exc=e)  # 3 minute retry
    
    asyncio.run(_sync_issue())


async def get_sprint_from_jira(jira_service: JiraService, sprint_id: int) -> Optional[Dict[str, Any]]:
    """Get sprint data from JIRA API."""
    # This is a placeholder - actual implementation would call JIRA API
    # For the actual implementation, you would extend JiraService
    return {
        "id": sprint_id,
        "name": f"Sprint {sprint_id}",
        "state": "ACTIVE",
        "start_date": datetime.utcnow(),
        "end_date": None,
        "goal": "Sample sprint goal",
        "board_id": 1
    }


async def get_sprint_issues_from_jira(jira_service: JiraService, sprint_id: int) -> List[Dict[str, Any]]:
    """Get issues for a sprint from JIRA API."""
    # Placeholder implementation
    return await jira_service.get_sprint_issues(sprint_id)


async def get_issue_from_jira(jira_service: JiraService, issue_key: str) -> Optional[Dict[str, Any]]:
    """Get individual issue data from JIRA API."""
    # This would call the actual JIRA API
    return {
        "key": issue_key,
        "id": "10001",
        "fields": {
            "summary": f"Updated summary for {issue_key}",
            "issuetype": {"name": "Story"},
            "status": {"name": "In Progress"},
            "priority": {"name": "High"},
            "assignee": {
                "accountId": "12345",
                "displayName": "John Doe"
            },
            "customfield_10002": 5.0,  # Story points
            "customfield_10741": {"value": "Backend Team"},  # Discipline team
            "labels": ["backend", "api"],
            "components": [{"name": "Authentication"}]
        }
    }


async def update_queue_with_jira_data(db: AsyncSession, queue: SprintQueue, issues: List[Dict[str, Any]]):
    """Update queue items with fresh JIRA data."""
    issue_map = {issue["key"]: issue for issue in issues}
    
    # Get existing queue items
    result = await db.execute(
        select(QueueItem).where(QueueItem.queue_id == queue.id)
    )
    queue_items = result.scalars().all()
    
    updated_count = 0
    for item in queue_items:
        if item.jira_issue_key in issue_map:
            issue_data = issue_map[item.jira_issue_key]
            await update_queue_item_from_jira(item, issue_data)
            updated_count += 1
    
    if updated_count > 0:
        await db.commit()
        logger.info(f"Updated {updated_count} items in queue {queue.name}")


async def update_queue_item_from_jira(item: QueueItem, issue_data: Dict[str, Any]):
    """Update a single queue item with JIRA data."""
    fields = issue_data.get("fields", {})
    
    # Update basic fields
    item.summary = fields.get("summary", item.summary)
    
    if fields.get("issuetype"):
        item.issue_type = fields["issuetype"].get("name", item.issue_type)
    
    if fields.get("status"):
        item.status = fields["status"].get("name", item.status)
    
    if fields.get("priority"):
        item.priority = fields["priority"].get("name", item.priority)
    
    # Update assignee
    if fields.get("assignee"):
        assignee = fields["assignee"]
        item.assignee_account_id = assignee.get("accountId")
        item.assignee_display_name = assignee.get("displayName")
    
    # Update story points and custom fields
    for field_key, field_value in fields.items():
        if "story" in field_key.lower() and "point" in field_key.lower():
            try:
                item.story_points = float(field_value) if field_value else None
            except (ValueError, TypeError):
                pass
        elif "discipline" in field_key.lower() or "team" in field_key.lower():
            if isinstance(field_value, dict) and "value" in field_value:
                item.discipline_team = field_value["value"]
    
    # Update metadata
    item.labels = fields.get("labels", [])
    item.components = [c.get("name") for c in fields.get("components", [])]
    
    # Store custom fields
    custom_fields = {}
    for field_key, field_value in fields.items():
        if field_key.startswith("customfield_"):
            custom_fields[field_key] = field_value
    
    if custom_fields:
        item.custom_fields = custom_fields