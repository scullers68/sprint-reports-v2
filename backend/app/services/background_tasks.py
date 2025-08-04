"""
Background task service for Sprint Reports v2.

Handles periodic tasks like sprint cache refresh, cleanup, and monitoring.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.sprint_cache_service import SprintCacheService

logger = logging.getLogger("background_tasks")


class BackgroundTaskService:
    """
    Service for managing background tasks.
    
    Handles:
    - Sprint cache refresh
    - Periodic cleanup
    - Health monitoring
    - Task scheduling
    """

    def __init__(self):
        self.is_running = False
        self.tasks = {}
        self.last_sprint_refresh = None
        self.sprint_refresh_interval = 2 * 3600  # 2 hours in seconds
        self.cleanup_interval = 24 * 3600  # 24 hours in seconds
        self.last_cleanup = None

    async def start(self):
        """Start the background task service."""
        if self.is_running:
            logger.warning("Background task service is already running")
            return

        self.is_running = True
        logger.info("Starting background task service")

        # Start the main task loop
        self.tasks['main_loop'] = asyncio.create_task(self._main_loop())
        
        # Perform initial sprint refresh
        await self._perform_sprint_refresh()

    async def stop(self):
        """Stop the background task service."""
        logger.info("Stopping background task service")
        self.is_running = False

        # Cancel all running tasks
        for task_name, task in self.tasks.items():
            if not task.done():
                logger.info(f"Cancelling task: {task_name}")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self.tasks.clear()
        logger.info("Background task service stopped")

    async def _main_loop(self):
        """Main background task loop."""
        logger.info("Background task main loop started")
        
        while self.is_running:
            try:
                current_time = datetime.utcnow()
                
                # Check if sprint refresh is needed
                if self._should_refresh_sprints(current_time):
                    logger.info("Sprint refresh interval reached, starting refresh")
                    await self._perform_sprint_refresh()
                
                # Check if cleanup is needed
                if self._should_perform_cleanup(current_time):
                    logger.info("Cleanup interval reached, starting cleanup")
                    await self._perform_cleanup()
                
                # Sleep for a minute before next check
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                logger.info("Main loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in background task main loop: {e}", exc_info=True)
                # Sleep longer on error to avoid rapid retries
                await asyncio.sleep(300)  # 5 minutes

        logger.info("Background task main loop ended")

    def _should_refresh_sprints(self, current_time: datetime) -> bool:
        """Check if sprint refresh is needed."""
        if self.last_sprint_refresh is None:
            return True
        
        time_since_refresh = (current_time - self.last_sprint_refresh).total_seconds()
        return time_since_refresh >= self.sprint_refresh_interval

    def _should_perform_cleanup(self, current_time: datetime) -> bool:
        """Check if cleanup is needed."""
        if self.last_cleanup is None:
            return True
        
        time_since_cleanup = (current_time - self.last_cleanup).total_seconds()
        return time_since_cleanup >= self.cleanup_interval

    async def _perform_sprint_refresh(self):
        """Perform sprint cache refresh."""
        try:
            logger.info("Starting scheduled sprint refresh")
            start_time = datetime.utcnow()
            
            async for db in get_db():
                cache_service = SprintCacheService(db)
                refresh_stats = await cache_service.refresh_all_sprints()
                break  # Exit after first iteration

            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Log detailed results
            total_sprints = refresh_stats['sprints_created'] + refresh_stats['sprints_updated']
            logger.info(
                f"Scheduled refresh completed: Successfully refreshed {total_sprints} sprints in {duration:.1f}s"
            )
            logger.info(
                f"  Scanned {refresh_stats['boards_scanned']} boards, found {refresh_stats['sprints_found']} sprints"
            )
            logger.info(f"Final result: Found {total_sprints} total sprints")
            
            # Log individual sprints if there are any
            if total_sprints > 0:
                async for db in get_db():
                    cache_service = SprintCacheService(db)
                    recent_sprints = await cache_service.search_cached_sprints(limit=20)
                    break
                
                for sprint in recent_sprints:
                    logger.info(f"  - {sprint['name']} (State: {sprint['state']}, Source: Sprint Cache)")

            if refresh_stats['errors']:
                logger.warning(f"Refresh completed with {len(refresh_stats['errors'])} errors:")
                for error in refresh_stats['errors']:
                    logger.warning(f"  - {error}")

            self.last_sprint_refresh = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Sprint refresh failed: {e}", exc_info=True)

    async def _perform_cleanup(self):
        """Perform cache cleanup."""
        try:
            logger.info("Starting scheduled cleanup")
            
            async for db in get_db():
                cache_service = SprintCacheService(db)
                cleaned_count = await cache_service.cleanup_stale_sprints(max_age_days=30)
                break

            logger.info(f"Cleanup completed: removed {cleaned_count} stale sprints")
            self.last_cleanup = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}", exc_info=True)

    async def force_sprint_refresh(self) -> Dict[str, Any]:
        """Force an immediate sprint refresh."""
        logger.info("Force sprint refresh requested")
        
        async for db in get_db():
            cache_service = SprintCacheService(db)
            refresh_stats = await cache_service.refresh_all_sprints()
            break

        self.last_sprint_refresh = datetime.utcnow()
        return refresh_stats

    async def get_task_status(self) -> Dict[str, Any]:
        """Get status of background tasks."""
        return {
            'is_running': self.is_running,
            'active_tasks': list(self.tasks.keys()),
            'last_sprint_refresh': self.last_sprint_refresh.isoformat() if self.last_sprint_refresh else None,
            'last_cleanup': self.last_cleanup.isoformat() if self.last_cleanup else None,
            'sprint_refresh_interval_hours': self.sprint_refresh_interval / 3600,
            'cleanup_interval_hours': self.cleanup_interval / 3600,
            'next_sprint_refresh': (
                (self.last_sprint_refresh + timedelta(seconds=self.sprint_refresh_interval)).isoformat()
                if self.last_sprint_refresh else "ASAP"
            ),
            'next_cleanup': (
                (self.last_cleanup + timedelta(seconds=self.cleanup_interval)).isoformat()
                if self.last_cleanup else "ASAP"
            )
        }


# Global instance
background_service = BackgroundTaskService()


async def get_background_service() -> BackgroundTaskService:
    """Get the global background task service instance."""
    return background_service