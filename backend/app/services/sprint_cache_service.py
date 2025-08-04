"""
Sprint Cache Service for managing cached JIRA sprint data.

This service handles the caching, refreshing, and retrieval of JIRA sprint
information to provide fast discovery without real-time API calls.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.cached_sprint import CachedSprint
from app.services.jira_service import JiraService
from app.services.jira_configuration_service import JiraConfigurationService

logger = logging.getLogger(__name__)


class SprintCacheService:
    """
    Service for managing cached JIRA sprint data.
    
    Provides functionality to:
    - Fetch and cache sprints from JIRA
    - Search cached sprints quickly
    - Refresh stale data
    - Manage cache lifecycle
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_cached_sprints(
        self,
        search: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 50,
        include_closed: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search cached sprints with filtering.
        
        Args:
            search: Search term for sprint name, board name, or project key
            state: Filter by sprint state (active, future, closed)
            limit: Maximum number of results
            include_closed: Whether to include closed sprints
            
        Returns:
            List of sprint dictionaries
        """
        query = select(CachedSprint).where(
            CachedSprint.is_active == True,
            CachedSprint.is_discoverable == True
        )

        # Apply state filter
        if state:
            query = query.where(CachedSprint.state.ilike(f"%{state}%"))
        elif not include_closed:
            # Default: exclude closed sprints
            query = query.where(CachedSprint.state.in_(['active', 'future']))

        # Apply search filter
        if search:
            search_lower = f"%{search.lower()}%"
            query = query.where(
                or_(
                    CachedSprint.name.ilike(search_lower),
                    CachedSprint.board_name.ilike(search_lower),
                    CachedSprint.project_key.ilike(search_lower),
                    CachedSprint.project_name.ilike(search_lower),
                    CachedSprint.search_keywords.ilike(search_lower)
                )
            )

        # Order by state priority and name
        query = query.order_by(
            CachedSprint.state.asc(),  # active, future, closed
            CachedSprint.name.asc()
        ).limit(limit)

        result = await self.db.execute(query)
        sprints = result.scalars().all()

        return [sprint.to_dict() for sprint in sprints]

    async def get_sprint_by_jira_id(self, jira_sprint_id: int) -> Optional[CachedSprint]:
        """Get a cached sprint by its JIRA ID."""
        query = select(CachedSprint).where(CachedSprint.jira_sprint_id == jira_sprint_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def upsert_sprint(
        self,
        jira_sprint_data: dict,
        board_data: dict,
        project_data: Optional[dict] = None
    ) -> CachedSprint:
        """
        Insert or update a sprint in the cache.
        
        Args:
            jira_sprint_data: Raw sprint data from JIRA API
            board_data: Board information
            project_data: Optional project information
            
        Returns:
            The cached sprint record
        """
        jira_sprint_id = jira_sprint_data.get('id')
        if not jira_sprint_id:
            raise ValueError("Sprint data must include 'id' field")

        # Try to find existing sprint
        existing_sprint = await self.get_sprint_by_jira_id(jira_sprint_id)

        if existing_sprint:
            # Update existing sprint
            existing_sprint.update_from_jira_data(jira_sprint_data)
            
            # Update board information
            existing_sprint.board_name = board_data.get('name', existing_sprint.board_name)
            existing_sprint.board_type = board_data.get('type', existing_sprint.board_type)
            
            # Update project information if provided
            if project_data:
                existing_sprint.project_key = project_data.get('key', existing_sprint.project_key)
                existing_sprint.project_name = project_data.get('name', existing_sprint.project_name)
            
            cached_sprint = existing_sprint
        else:
            # Create new sprint
            cached_sprint = CachedSprint(
                jira_sprint_id=jira_sprint_id,
                name=jira_sprint_data.get('name', ''),
                state=jira_sprint_data.get('state', 'unknown'),
                goal=jira_sprint_data.get('goal'),
                board_id=board_data.get('id'),
                board_name=board_data.get('name', ''),
                board_type=board_data.get('type', 'unknown'),
                project_key=project_data.get('key') if project_data else None,
                project_name=project_data.get('name') if project_data else None,
                discovery_source="api_sync"
            )
            
            # Update from JIRA data
            cached_sprint.update_from_jira_data(jira_sprint_data)
            
            self.db.add(cached_sprint)

        await self.db.commit()
        await self.db.refresh(cached_sprint)
        
        return cached_sprint

    async def refresh_all_sprints(self) -> Dict[str, Any]:
        """
        Refresh all sprints from JIRA.
        
        Returns:
            Summary of the refresh operation
        """
        start_time = datetime.utcnow()
        stats = {
            'start_time': start_time,
            'boards_scanned': 0,
            'sprints_found': 0,
            'sprints_updated': 0,
            'sprints_created': 0,
            'errors': [],
            'duration_seconds': 0
        }

        try:
            # Use environment variables for JIRA configuration
            from app.core.config import settings
            
            if not settings.JIRA_URL or not settings.JIRA_API_TOKEN or not settings.JIRA_EMAIL:
                error_msg = "JIRA environment variables not configured. Please set JIRA_URL, JIRA_API_TOKEN, and JIRA_EMAIL."
                stats['errors'].append(error_msg)
                logger.warning(error_msg)
                return stats
            
            # Create JIRA service
            jira_service = JiraService(self.db)
            
            # Create JIRA client with environment configuration
            from app.services.jira_service import JiraAPIClient
            
            client = JiraAPIClient(
                url=settings.JIRA_URL,
                auth_method="token",
                email=settings.JIRA_EMAIL,
                api_token=settings.JIRA_API_TOKEN,
                cloud=True  # Assume cloud for .atlassian.net URLs
            )
            
            jira_service._client = client

            # Get all boards
            all_boards = await jira_service.get_boards()
            stats['boards_scanned'] = len(all_boards)
            
            logger.info(f"Starting sprint refresh: scanning {len(all_boards)} boards")

            # Process each board
            for board in all_boards:
                try:
                    # Only process Scrum boards (they have sprints)
                    if board.get('type', '').lower() != 'scrum':
                        continue

                    board_id = board.get('id')
                    logger.debug(f"Processing board {board_id}: {board.get('name')}")

                    # Get sprints for this board
                    board_sprints = await jira_service.get_sprints(board_id=board_id)
                    
                    if not board_sprints:
                        continue

                    stats['sprints_found'] += len(board_sprints)

                    # Get project info if available
                    project_data = None
                    if board.get('location', {}).get('projectKey'):
                        project_key = board['location']['projectKey']
                        # We could fetch project details here, but for now use basic info
                        project_data = {'key': project_key, 'name': project_key}

                    # Process each sprint
                    for sprint_data in board_sprints:
                        try:
                            # Check if this is a new or updated sprint
                            existing_sprint = await self.get_sprint_by_jira_id(sprint_data.get('id'))
                            
                            cached_sprint = await self.upsert_sprint(
                                jira_sprint_data=sprint_data,
                                board_data=board,
                                project_data=project_data
                            )
                            
                            if existing_sprint:
                                stats['sprints_updated'] += 1
                            else:
                                stats['sprints_created'] += 1
                                
                        except Exception as e:
                            error_msg = f"Error processing sprint {sprint_data.get('id', 'unknown')}: {str(e)}"
                            stats['errors'].append(error_msg)
                            logger.warning(error_msg)

                except Exception as e:
                    error_msg = f"Error processing board {board.get('id', 'unknown')}: {str(e)}"
                    stats['errors'].append(error_msg)
                    logger.warning(error_msg)

            await jira_service.close()
            await client.close()

        except Exception as e:
            error_msg = f"Critical error during sprint refresh: {str(e)}"
            stats['errors'].append(error_msg)
            logger.error(error_msg, exc_info=True)

        # Calculate duration
        end_time = datetime.utcnow()
        stats['end_time'] = end_time
        stats['duration_seconds'] = (end_time - start_time).total_seconds()

        # Log summary
        total_sprints = stats['sprints_created'] + stats['sprints_updated']
        logger.info(
            f"Sprint refresh completed: Found {total_sprints} total sprints "
            f"({stats['sprints_created']} new, {stats['sprints_updated']} updated) "
            f"in {stats['duration_seconds']:.1f}s. "
            f"Scanned {stats['boards_scanned']} boards, found {stats['sprints_found']} sprints. "
            f"Errors: {len(stats['errors'])}"
        )

        return stats

    async def cleanup_stale_sprints(self, max_age_days: int = 30) -> int:
        """
        Remove sprints that haven't been updated in a long time.
        
        Args:
            max_age_days: Maximum age in days before a sprint is considered stale
            
        Returns:
            Number of sprints cleaned up
        """
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        
        query = select(CachedSprint).where(
            CachedSprint.last_fetched_at < cutoff_date,
            CachedSprint.state == 'closed'  # Only cleanup closed sprints
        )
        
        result = await self.db.execute(query)
        stale_sprints = result.scalars().all()
        
        for sprint in stale_sprints:
            await self.db.delete(sprint)
        
        await self.db.commit()
        
        logger.info(f"Cleaned up {len(stale_sprints)} stale sprints older than {max_age_days} days")
        return len(stale_sprints)

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the sprint cache."""
        # Count by state
        from sqlalchemy import func
        active_count = await self.db.scalar(
            select(func.count(CachedSprint.id)).where(CachedSprint.state == 'active')
        ) or 0
        future_count = await self.db.scalar(
            select(func.count(CachedSprint.id)).where(CachedSprint.state == 'future')
        ) or 0
        closed_count = await self.db.scalar(
            select(func.count(CachedSprint.id)).where(CachedSprint.state == 'closed')
        ) or 0
        
        # Get oldest and newest
        oldest_result = await self.db.execute(
            select(CachedSprint.last_fetched_at).order_by(CachedSprint.last_fetched_at.asc()).limit(1)
        )
        oldest_fetch = oldest_result.scalar_one_or_none()
        
        newest_result = await self.db.execute(
            select(CachedSprint.last_fetched_at).order_by(CachedSprint.last_fetched_at.desc()).limit(1)
        )
        newest_fetch = newest_result.scalar_one_or_none()

        return {
            'total_sprints': active_count + future_count + closed_count,
            'active_sprints': active_count,
            'future_sprints': future_count,
            'closed_sprints': closed_count,
            'oldest_fetch': oldest_fetch.isoformat() if oldest_fetch else None,
            'newest_fetch': newest_fetch.isoformat() if newest_fetch else None,
        }