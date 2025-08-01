"""
Synchronization service for JIRA data synchronization.

Handles bi-directional sync, conflict resolution, and incremental updates.
"""

import hashlib
import json
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone

from sqlalchemy import select, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.sprint import (
    Sprint, SyncMetadata, ConflictResolution, SyncHistory,
    SyncStatus, ConflictResolutionStrategy
)
from app.models.sync_state import SyncState
from app.schemas.sprint import SprintCreate, SprintUpdate
from app.services.jira_service import JiraService
from app.services.sprint_service import SprintService
from app.core.logging import get_logger

logger = get_logger(__name__)


class SyncService:
    """Service for managing JIRA data synchronization."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sprint_service = SprintService(db)
    
    async def sync_sprints_bidirectional(
        self,
        jira_service: JiraService,
        board_id: Optional[int] = None,
        incremental: bool = False,
        batch_id: Optional[str] = None
    ) -> Tuple[List[Sprint], SyncHistory]:
        """
        Perform bi-directional sprint synchronization with conflict resolution.
        
        Args:
            jira_service: JIRA service instance
            board_id: Optional board ID to filter sprints
            incremental: Whether to perform incremental sync
            batch_id: Optional batch ID for grouping sync operations
        
        Returns:
            Tuple of synced sprints and sync history record
        """
        if not batch_id:
            batch_id = str(uuid.uuid4())
        
        # Start sync history tracking
        sync_history = SyncHistory(
            operation_type="incremental_sync" if incremental else "full_sync",
            entity_type="sprint",
            batch_id=batch_id,
            status=SyncStatus.IN_PROGRESS
        )
        self.db.add(sync_history)
        await self.db.commit()
        await self.db.refresh(sync_history)
        
        start_time = datetime.now(timezone.utc)
        synced_sprints = []
        api_calls = 0
        
        try:
            # Get sprints from JIRA
            jira_sprints = await jira_service.get_sprints(board_id=board_id)
            api_calls += 1
            
            for jira_sprint in jira_sprints:
                try:
                    # Get or create sync metadata
                    sync_metadata = await self._get_or_create_sync_metadata(
                        entity_type="sprint",
                        entity_id=str(jira_sprint["id"]),
                        jira_id=str(jira_sprint["id"]),
                        batch_id=batch_id
                    )
                    
                    # Check if incremental sync should skip this sprint
                    if incremental and await self._should_skip_incremental_sync(sync_metadata, jira_sprint):
                        sync_history.entities_skipped += 1
                        continue
                    
                    # Check if sprint already exists locally
                    existing = await self.sprint_service.get_sprint_by_jira_id(jira_sprint["id"])
                    
                    if existing:
                        # Handle potential conflicts and update
                        sprint, conflicts = await self._handle_sprint_update_with_conflicts(
                            existing, jira_sprint, sync_metadata
                        )
                        if conflicts > 0:
                            sync_history.conflicts_detected += conflicts
                        sync_history.entities_updated += 1
                    else:
                        # Create new sprint
                        sprint = await self._create_sprint_from_jira_data(jira_sprint)
                        sync_history.entities_created += 1
                    
                    # Update sync metadata
                    await self._update_sync_metadata_success(sync_metadata, jira_sprint)
                    synced_sprints.append(sprint)
                    
                except Exception as e:
                    logger.error(f"Error syncing sprint {jira_sprint.get('id', 'unknown')}: {e}")
                    sync_history.entities_skipped += 1
                    
                    # Update sync metadata with error
                    if 'sync_metadata' in locals():
                        await self._update_sync_metadata_error(sync_metadata, str(e))
            
            # Update sync history with success
            end_time = datetime.now(timezone.utc)
            sync_history.duration_seconds = (end_time - start_time).total_seconds()
            sync_history.api_calls_made = api_calls
            sync_history.entities_processed = len(jira_sprints)
            sync_history.status = SyncStatus.COMPLETED
            
        except Exception as e:
            # Update sync history with failure
            logger.error(f"Sync operation failed: {e}")
            end_time = datetime.now(timezone.utc)
            sync_history.duration_seconds = (end_time - start_time).total_seconds()
            sync_history.api_calls_made = api_calls
            sync_history.status = SyncStatus.FAILED
            sync_history.error_message = str(e)
            raise
        
        finally:
            await self.db.commit()
        
        return synced_sprints, sync_history
    
    async def sync_incremental(
        self,
        jira_service: JiraService,
        since: Optional[datetime] = None,
        entity_types: Optional[List[str]] = None
    ) -> SyncHistory:
        """
        Perform incremental synchronization for entities modified since timestamp.
        
        Args:
            jira_service: JIRA service instance
            since: Timestamp to sync from (defaults to last successful sync)
            entity_types: List of entity types to sync (defaults to all)
        
        Returns:
            Sync history record
        """
        if not since:
            # Get last successful sync timestamp
            since = await self._get_last_sync_timestamp()
        
        if not entity_types:
            entity_types = ["sprint"]
        
        batch_id = str(uuid.uuid4())
        sync_history = SyncHistory(
            operation_type="incremental_sync",
            entity_type="mixed",
            batch_id=batch_id,
            status=SyncStatus.IN_PROGRESS
        )
        self.db.add(sync_history)
        await self.db.commit()
        await self.db.refresh(sync_history)
        
        try:
            # Sync each entity type
            for entity_type in entity_types:
                if entity_type == "sprint":
                    await self.sync_sprints_bidirectional(
                        jira_service=jira_service,
                        incremental=True,
                        batch_id=batch_id
                    )
            
            sync_history.status = SyncStatus.COMPLETED
            
        except Exception as e:
            sync_history.status = SyncStatus.FAILED
            sync_history.error_message = str(e)
            raise
        
        finally:
            await self.db.commit()
        
        return sync_history
    
    async def _get_or_create_sync_metadata(
        self,
        entity_type: str,
        entity_id: str,
        jira_id: str,
        batch_id: str
    ) -> SyncMetadata:
        """Get or create sync metadata for an entity."""
        query = select(SyncMetadata).where(
            and_(
                SyncMetadata.entity_type == entity_type,
                SyncMetadata.entity_id == entity_id
            )
        )
        result = await self.db.execute(query)
        sync_metadata = result.scalar_one_or_none()
        
        if not sync_metadata:
            sync_metadata = SyncMetadata(
                entity_type=entity_type,
                entity_id=entity_id,
                jira_id=jira_id,
                sync_batch_id=batch_id,
                sync_status=SyncStatus.PENDING
            )
            self.db.add(sync_metadata)
            await self.db.commit()
            await self.db.refresh(sync_metadata)
        else:
            # Update batch ID for existing metadata
            sync_metadata.sync_batch_id = batch_id
        
        return sync_metadata
    
    async def _should_skip_incremental_sync(self, sync_metadata: SyncMetadata, jira_data: Dict) -> bool:
        """Determine if entity should be skipped in incremental sync."""
        if not sync_metadata.last_successful_sync:
            return False  # Never synced, don't skip
        
        # Check if JIRA data has lastModified timestamp
        jira_modified = jira_data.get('lastModified')
        if not jira_modified:
            return False  # No timestamp, don't skip
        
        try:
            jira_modified_dt = datetime.fromisoformat(jira_modified.replace('Z', '+00:00'))
            return jira_modified_dt <= sync_metadata.last_successful_sync
        except (ValueError, AttributeError):
            return False  # Invalid timestamp, don't skip
    
    async def _handle_sprint_update_with_conflicts(
        self,
        existing_sprint: Sprint,
        jira_data: Dict,
        sync_metadata: SyncMetadata
    ) -> Tuple[Sprint, int]:
        """Handle sprint update with conflict detection and resolution."""
        conflicts_detected = 0
        
        # Prepare update data
        sprint_update_data = {
            "name": jira_data["name"],
            "state": jira_data["state"].lower(),
            "goal": jira_data.get("goal"),
            "start_date": jira_data.get("startDate"),
            "end_date": jira_data.get("endDate"),
            "complete_date": jira_data.get("completeDate"),
            "board_id": jira_data.get("originBoardId"),
            "origin_board_id": jira_data.get("originBoardId")
        }
        
        # Check for conflicts
        for field, new_value in sprint_update_data.items():
            current_value = getattr(existing_sprint, field)
            
            # Handle datetime fields
            if field in ["start_date", "end_date", "complete_date"] and new_value:
                try:
                    new_value = datetime.fromisoformat(new_value.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    new_value = None
            
            # Detect conflict (local value differs from remote and both modified after last sync)
            if current_value != new_value and self._is_field_conflict(
                existing_sprint, field, current_value, new_value, sync_metadata
            ):
                conflicts_detected += 1
                
                # Create conflict resolution record
                conflict = ConflictResolution(
                    sync_metadata_id=sync_metadata.id,
                    conflict_type="field_conflict",
                    field_name=field,
                    local_value=self._serialize_field_value(current_value),
                    remote_value=self._serialize_field_value(new_value),
                    resolution_strategy=ConflictResolutionStrategy.REMOTE_WINS,  # Default to remote wins
                    resolved_value=self._serialize_field_value(new_value),
                    is_resolved=True,
                    resolved_at=datetime.now(timezone.utc),
                    resolution_notes="Auto-resolved: Remote wins policy"
                )
                self.db.add(conflict)
        
        # Apply updates (using remote wins for now)
        sprint_update = SprintUpdate(**{k: v for k, v in sprint_update_data.items() if v is not None})
        updated_sprint = await self.sprint_service.update_sprint(existing_sprint.id, sprint_update)
        
        return updated_sprint, conflicts_detected
    
    def _is_field_conflict(
        self,
        existing_sprint: Sprint,
        field: str,
        current_value: Any,
        new_value: Any,
        sync_metadata: SyncMetadata
    ) -> bool:
        """Determine if a field change represents a conflict."""
        # Simple conflict detection: if local entity was modified after last sync
        # and the field values differ, it's a potential conflict
        if not sync_metadata.last_successful_sync:
            return False  # No previous sync, no conflict
        
        return (
            existing_sprint.updated_at > sync_metadata.last_successful_sync and 
            current_value != new_value
        )
    
    def _serialize_field_value(self, value: Any) -> Any:
        """Serialize field value for JSON storage."""
        if isinstance(value, datetime):
            return value.isoformat()
        return value
    
    async def _create_sprint_from_jira_data(self, jira_data: Dict) -> Sprint:
        """Create sprint from JIRA data."""
        sprint_create = SprintCreate(
            jira_sprint_id=jira_data["id"],
            name=jira_data["name"],
            state=jira_data["state"].lower(),
            goal=jira_data.get("goal"),
            start_date=jira_data.get("startDate"),
            end_date=jira_data.get("endDate"),
            complete_date=jira_data.get("completeDate"),
            board_id=jira_data.get("originBoardId"),
            origin_board_id=jira_data.get("originBoardId")
        )
        return await self.sprint_service.create_sprint(sprint_create)
    
    async def _update_sync_metadata_success(self, sync_metadata: SyncMetadata, jira_data: Dict):
        """Update sync metadata after successful sync."""
        now = datetime.now(timezone.utc)
        sync_metadata.sync_status = SyncStatus.COMPLETED
        sync_metadata.last_sync_attempt = now
        sync_metadata.last_successful_sync = now
        sync_metadata.error_count = 0
        sync_metadata.last_error = None
        
        # Update content hash for change detection
        content_hash = hashlib.sha256(json.dumps(jira_data, sort_keys=True).encode()).hexdigest()
        sync_metadata.content_hash = content_hash
        
        # Update remote modified timestamp if available
        if jira_data.get('lastModified'):
            try:
                sync_metadata.remote_modified = datetime.fromisoformat(
                    jira_data['lastModified'].replace('Z', '+00:00')
                )
            except (ValueError, AttributeError):
                pass
        
        await self.db.commit()
    
    async def _update_sync_metadata_error(self, sync_metadata: SyncMetadata, error_message: str):
        """Update sync metadata after sync error."""
        sync_metadata.sync_status = SyncStatus.FAILED
        sync_metadata.last_sync_attempt = datetime.now(timezone.utc)
        sync_metadata.error_count += 1
        sync_metadata.last_error = error_message
        await self.db.commit()
    
    async def _get_last_sync_timestamp(self) -> Optional[datetime]:
        """Get timestamp of last successful sync."""
        query = select(SyncHistory).where(
            SyncHistory.status == SyncStatus.COMPLETED
        ).order_by(desc(SyncHistory.created_at)).limit(1)
        
        result = await self.db.execute(query)
        last_sync = result.scalar_one_or_none()
        
        return last_sync.created_at if last_sync else None
    
    async def get_sync_conflicts(
        self,
        entity_type: Optional[str] = None,
        resolved: Optional[bool] = None
    ) -> List[ConflictResolution]:
        """Get synchronization conflicts."""
        query = select(ConflictResolution).join(SyncMetadata)
        
        if entity_type:
            query = query.where(SyncMetadata.entity_type == entity_type)
        
        if resolved is not None:
            query = query.where(ConflictResolution.is_resolved == resolved)
        
        query = query.order_by(desc(ConflictResolution.created_at))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def resolve_conflict(
        self,
        conflict_id: int,
        resolution_strategy: ConflictResolutionStrategy,
        resolved_value: Any = None,
        user_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> ConflictResolution:
        """Manually resolve a synchronization conflict."""
        query = select(ConflictResolution).where(ConflictResolution.id == conflict_id)
        result = await self.db.execute(query)
        conflict = result.scalar_one_or_none()
        
        if not conflict:
            raise ValueError(f"Conflict with ID {conflict_id} not found")
        
        if conflict.is_resolved:
            raise ValueError(f"Conflict {conflict_id} is already resolved")
        
        # Apply resolution strategy
        if resolution_strategy == ConflictResolutionStrategy.LOCAL_WINS:
            final_value = conflict.local_value
        elif resolution_strategy == ConflictResolutionStrategy.REMOTE_WINS:
            final_value = conflict.remote_value
        elif resolution_strategy == ConflictResolutionStrategy.MANUAL:
            if resolved_value is None:
                raise ValueError("Manual resolution requires resolved_value")
            final_value = resolved_value
        else:  # MERGE strategy would need specific implementation
            raise ValueError(f"Resolution strategy {resolution_strategy} not implemented")
        
        # Update conflict record
        conflict.resolution_strategy = resolution_strategy
        conflict.resolved_value = final_value
        conflict.resolved_by = user_id
        conflict.resolved_at = datetime.now(timezone.utc)
        conflict.is_resolved = True
        conflict.resolution_notes = notes
        
        await self.db.commit()
        await self.db.refresh(conflict)
        
        return conflict
    
    async def get_sync_history(
        self,
        operation_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 50
    ) -> List[SyncHistory]:
        """Get synchronization history."""
        query = select(SyncHistory)
        
        if operation_type:
            query = query.where(SyncHistory.operation_type == operation_type)
        
        if entity_type:
            query = query.where(SyncHistory.entity_type == entity_type)
        
        query = query.order_by(desc(SyncHistory.created_at)).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def validate_data_consistency(
        self,
        jira_service: JiraService,
        entity_type: str = "sprint"
    ) -> Dict[str, Any]:
        """Validate data consistency between local and remote systems."""
        validation_results = {
            "entity_type": entity_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "local_count": 0,
            "remote_count": 0,
            "inconsistencies": [],
            "missing_local": [],
            "missing_remote": []
        }
        
        if entity_type == "sprint":
            # Get local sprints
            local_sprints = await self.sprint_service.get_sprints(limit=1000)
            validation_results["local_count"] = len(local_sprints)
            
            # Get remote sprints
            remote_sprints = await jira_service.get_sprints()
            validation_results["remote_count"] = len(remote_sprints)
            
            # Create lookup dictionaries
            local_by_jira_id = {str(s.jira_sprint_id): s for s in local_sprints}
            remote_by_id = {str(s["id"]): s for s in remote_sprints}
            
            # Check for missing local sprints
            for remote_id, remote_sprint in remote_by_id.items():
                if remote_id not in local_by_jira_id:
                    validation_results["missing_local"].append({
                        "jira_id": remote_id,
                        "name": remote_sprint["name"]
                    })
            
            # Check for missing remote sprints and inconsistencies
            for local_sprint in local_sprints:
                jira_id = str(local_sprint.jira_sprint_id)
                
                if jira_id not in remote_by_id:
                    validation_results["missing_remote"].append({
                        "id": local_sprint.id,
                        "jira_id": jira_id,
                        "name": local_sprint.name
                    })
                else:
                    # Check for inconsistencies
                    remote_sprint = remote_by_id[jira_id]
                    inconsistencies = []
                    
                    if local_sprint.name != remote_sprint["name"]:
                        inconsistencies.append({
                            "field": "name",
                            "local": local_sprint.name,
                            "remote": remote_sprint["name"]
                        })
                    
                    if local_sprint.state != remote_sprint["state"].lower():
                        inconsistencies.append({
                            "field": "state",
                            "local": local_sprint.state,
                            "remote": remote_sprint["state"].lower()
                        })
                    
                    if inconsistencies:
                        validation_results["inconsistencies"].append({
                            "jira_id": jira_id,
                            "name": local_sprint.name,
                            "differences": inconsistencies
                        })
        
        return validation_results
    
    async def _handle_single_sprint_sync(self, jira_sprint: Dict[str, Any], batch_id: str):
        """Handle synchronization of a single sprint (helper for webhook processing)."""
        # Get or create sync metadata
        sync_metadata = await self._get_or_create_sync_metadata(
            entity_type="sprint",
            entity_id=str(jira_sprint["id"]),
            jira_id=str(jira_sprint["id"]),
            batch_id=batch_id
        )
        
        # Check if sprint already exists locally
        existing = await self.sprint_service.get_sprint_by_jira_id(jira_sprint["id"])
        
        if existing:
            # Handle potential conflicts and update
            sprint, conflicts = await self._handle_sprint_update_with_conflicts(
                existing, jira_sprint, sync_metadata
            )
        else:
            # Create new sprint
            sprint = await self._create_sprint_from_jira_data(jira_sprint)
        
        # Update sync metadata
        await self._update_sync_metadata_success(sync_metadata, jira_sprint)
        
        return sprint