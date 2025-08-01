"""
Sync State service using the architectural specification compliant SyncState model.

This service demonstrates using the unified SyncState model that maps to sync_metadata table.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync_state import SyncState
from app.core.logging import get_logger

logger = get_logger(__name__)


class SyncStateService:
    """Service for managing sync state using the architectural specification."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_sync_state(
        self,
        entity_type: str,
        entity_id: str,
        jira_id: str,
        sync_direction: str = "bidirectional",
        sync_batch_id: Optional[str] = None
    ) -> SyncState:
        """Create a new sync state record."""
        sync_state = SyncState(
            entity_type=entity_type,
            entity_id=entity_id,
            jira_id=jira_id,
            sync_status="pending",
            sync_direction=sync_direction,
            sync_batch_id=sync_batch_id
        )
        
        self.db.add(sync_state)
        await self.db.commit()
        await self.db.refresh(sync_state)
        
        return sync_state
    
    async def get_sync_state(
        self,
        entity_type: str,
        entity_id: str
    ) -> Optional[SyncState]:
        """Get sync state by entity type and ID."""
        query = select(SyncState).where(
            and_(
                SyncState.entity_type == entity_type,
                SyncState.entity_id == entity_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def update_sync_state_success(
        self,
        sync_state: SyncState,
        duration_ms: Optional[int] = None,
        api_calls: Optional[int] = None
    ) -> SyncState:
        """Update sync state after successful sync."""
        now = datetime.now(timezone.utc)
        sync_state.sync_status = "completed"
        sync_state.last_sync_attempt = now
        sync_state.last_successful_sync = now
        sync_state.error_count = 0
        sync_state.last_error = None
        
        if duration_ms is not None:
            sync_state.sync_duration_ms = duration_ms
        if api_calls is not None:
            sync_state.api_calls_count = api_calls
        
        await self.db.commit()
        await self.db.refresh(sync_state)
        return sync_state
    
    async def update_sync_state_error(
        self,
        sync_state: SyncState,
        error_message: str
    ) -> SyncState:
        """Update sync state after sync error."""
        sync_state.sync_status = "failed"
        sync_state.last_sync_attempt = datetime.now(timezone.utc)
        sync_state.error_count += 1
        sync_state.last_error = error_message
        
        await self.db.commit()
        await self.db.refresh(sync_state)
        return sync_state
    
    async def record_conflict(
        self,
        sync_state: SyncState,
        conflicts: Dict[str, Any],
        resolution_strategy: str = "manual"
    ) -> SyncState:
        """Record conflicts in sync state."""
        sync_state.conflicts = conflicts
        sync_state.resolution_strategy = resolution_strategy
        
        await self.db.commit()
        await self.db.refresh(sync_state)
        return sync_state
    
    async def get_pending_sync_states(
        self,
        entity_type: Optional[str] = None,
        limit: int = 100
    ) -> List[SyncState]:
        """Get sync states that are pending synchronization."""
        query = select(SyncState).where(SyncState.sync_status == "pending")
        
        if entity_type:
            query = query.where(SyncState.entity_type == entity_type)
        
        query = query.order_by(SyncState.created_at).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_failed_sync_states(
        self,
        entity_type: Optional[str] = None,
        min_error_count: int = 1
    ) -> List[SyncState]:
        """Get sync states that have failed synchronization."""
        query = select(SyncState).where(
            and_(
                SyncState.sync_status == "failed",
                SyncState.error_count >= min_error_count
            )
        )
        
        if entity_type:
            query = query.where(SyncState.entity_type == entity_type)
        
        query = query.order_by(desc(SyncState.error_count), desc(SyncState.last_sync_attempt))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_sync_states_with_conflicts(
        self,
        entity_type: Optional[str] = None
    ) -> List[SyncState]:
        """Get sync states that have unresolved conflicts."""
        query = select(SyncState).where(
            and_(
                SyncState.conflicts.is_not(None),
                or_(
                    SyncState.resolution_strategy == "manual",
                    SyncState.resolution_strategy.is_(None)
                )
            )
        )
        
        if entity_type:
            query = query.where(SyncState.entity_type == entity_type)
        
        query = query.order_by(desc(SyncState.created_at))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_sync_performance_stats(
        self,
        entity_type: Optional[str] = None,
        hours_back: int = 24
    ) -> Dict[str, Any]:
        """Get sync performance statistics."""
        cutoff_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        if hours_back < 24:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        
        query = select(SyncState).where(
            and_(
                SyncState.last_sync_attempt >= cutoff_time,
                SyncState.sync_duration_ms.is_not(None)
            )
        )
        
        if entity_type:
            query = query.where(SyncState.entity_type == entity_type)
        
        result = await self.db.execute(query)
        sync_states = result.scalars().all()
        
        if not sync_states:
            return {
                "total_syncs": 0,
                "successful_syncs": 0,
                "failed_syncs": 0,
                "avg_duration_ms": 0,
                "total_api_calls": 0,
                "success_rate": 0.0
            }
        
        successful = [s for s in sync_states if s.sync_status == "completed"]
        failed = [s for s in sync_states if s.sync_status == "failed"]
        
        total_duration = sum(s.sync_duration_ms for s in sync_states if s.sync_duration_ms)
        total_api_calls = sum(s.api_calls_count for s in sync_states)
        
        return {
            "total_syncs": len(sync_states),
            "successful_syncs": len(successful),
            "failed_syncs": len(failed),
            "avg_duration_ms": total_duration // len(sync_states) if sync_states else 0,
            "total_api_calls": total_api_calls,
            "success_rate": len(successful) / len(sync_states) if sync_states else 0.0
        }