"""
Sprint management endpoints.

Handles CRUD operations for sprints, sprint analysis, and JIRA integration.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.sprint import (
    SprintCreate, SprintRead, SprintUpdate, 
    SprintAnalysisCreate, SprintAnalysisRead
)
from app.services.sprint_service import SprintService
from app.services.jira_service import JiraService
from app.services.sync_service import SyncService

router = APIRouter()


@router.get("/", response_model=List[SprintRead])
async def list_sprints(
    *,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    state: Optional[str] = Query(None, description="Filter by sprint state"),
    active_only: bool = Query(False, description="Only return active sprints")
):
    """List all sprints with optional filtering."""
    sprint_service = SprintService(db)
    
    if active_only:
        return await sprint_service.get_active_sprints()
    
    return await sprint_service.get_sprints(
        skip=skip, 
        limit=limit, 
        state=state
    )


@router.get("/{sprint_id}", response_model=SprintRead)
async def get_sprint(
    sprint_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific sprint by ID."""
    sprint_service = SprintService(db)
    sprint = await sprint_service.get_sprint(sprint_id)
    
    if not sprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sprint not found"
        )
    
    return sprint


@router.get("/by-name/{sprint_name}", response_model=SprintRead)
async def get_sprint_by_name(
    sprint_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a sprint by name."""
    sprint_service = SprintService(db)
    sprint = await sprint_service.get_sprint_by_name(sprint_name)
    
    if not sprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sprint '{sprint_name}' not found"
        )
    
    return sprint


@router.post("/", response_model=SprintRead)
async def create_sprint(
    *,
    db: AsyncSession = Depends(get_db),
    sprint_in: SprintCreate
):
    """Create a new sprint."""
    sprint_service = SprintService(db)
    return await sprint_service.create_sprint(sprint_in)


@router.put("/{sprint_id}", response_model=SprintRead)
async def update_sprint(
    *,
    db: AsyncSession = Depends(get_db),
    sprint_id: int,
    sprint_in: SprintUpdate
):
    """Update an existing sprint."""
    sprint_service = SprintService(db)
    sprint = await sprint_service.update_sprint(sprint_id, sprint_in)
    
    if not sprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sprint not found"
        )
    
    return sprint


@router.delete("/{sprint_id}")
async def delete_sprint(
    sprint_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a sprint."""
    sprint_service = SprintService(db)
    success = await sprint_service.delete_sprint(sprint_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sprint not found"
        )
    
    return {"message": "Sprint deleted successfully"}


@router.post("/sync-from-jira")
async def sync_sprints_from_jira(
    db: AsyncSession = Depends(get_db),
    board_id: Optional[int] = Query(None, description="Specific board ID to sync")
):
    """Sync sprints from JIRA."""
    jira_service = JiraService()
    sprint_service = SprintService(db)
    
    try:
        synced_sprints = await sprint_service.sync_from_jira(
            jira_service, 
            board_id=board_id
        )
        
        return {
            "message": f"Successfully synced {len(synced_sprints)} sprints",
            "synced_sprints": [sprint.name for sprint in synced_sprints]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync sprints from JIRA: {str(e)}"
        )


@router.post("/{sprint_id}/analyze", response_model=SprintAnalysisRead)
async def analyze_sprint(
    *,
    db: AsyncSession = Depends(get_db),
    sprint_id: int,
    analysis_in: SprintAnalysisCreate
):
    """Analyze a sprint and create discipline team breakdown."""
    sprint_service = SprintService(db)
    
    try:
        analysis = await sprint_service.analyze_sprint(sprint_id, analysis_in)
        return analysis
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze sprint: {str(e)}"
        )


@router.get("/{sprint_id}/analyses", response_model=List[SprintAnalysisRead])
async def get_sprint_analyses(
    sprint_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all analyses for a sprint."""
    sprint_service = SprintService(db)
    return await sprint_service.get_sprint_analyses(sprint_id)


@router.get("/{sprint_id}/latest-analysis", response_model=SprintAnalysisRead)
async def get_latest_sprint_analysis(
    sprint_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get the latest analysis for a sprint."""
    sprint_service = SprintService(db)
    analysis = await sprint_service.get_latest_analysis(sprint_id)
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No analysis found for this sprint"
        )
    
    return analysis


@router.post("/sync-bidirectional")
async def sync_sprints_bidirectional(
    db: AsyncSession = Depends(get_db),
    board_id: Optional[int] = Query(None, description="Specific board ID to sync"),
    incremental: bool = Query(False, description="Perform incremental sync only")
):
    """Perform bi-directional sprint synchronization with conflict resolution."""
    jira_service = JiraService()
    sync_service = SyncService(db)
    
    try:
        async with jira_service:
            synced_sprints, sync_history = await sync_service.sync_sprints_bidirectional(
                jira_service=jira_service,
                board_id=board_id,
                incremental=incremental
            )
        
        return {
            "message": f"Successfully synced {len(synced_sprints)} sprints",
            "sync_history": {
                "id": sync_history.id,
                "operation_type": sync_history.operation_type,
                "status": sync_history.status.value,
                "entities_processed": sync_history.entities_processed,
                "entities_created": sync_history.entities_created,
                "entities_updated": sync_history.entities_updated,
                "entities_skipped": sync_history.entities_skipped,
                "conflicts_detected": sync_history.conflicts_detected,
                "duration_seconds": sync_history.duration_seconds,
                "api_calls_made": sync_history.api_calls_made
            },
            "synced_sprints": [{"id": s.id, "name": s.name, "jira_id": s.jira_sprint_id} for s in synced_sprints]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync sprints: {str(e)}"
        )


@router.get("/sync/conflicts")
async def get_sync_conflicts(
    db: AsyncSession = Depends(get_db),
    resolved: Optional[bool] = Query(None, description="Filter by resolution status")
):
    """Get synchronization conflicts for sprints."""
    sync_service = SyncService(db)
    
    conflicts = await sync_service.get_sync_conflicts(
        entity_type="sprint",
        resolved=resolved
    )
    
    return {
        "conflicts": [
            {
                "id": conflict.id,
                "conflict_type": conflict.conflict_type,
                "field_name": conflict.field_name,
                "local_value": conflict.local_value,
                "remote_value": conflict.remote_value,
                "resolution_strategy": conflict.resolution_strategy.value,
                "is_resolved": conflict.is_resolved,
                "resolved_at": conflict.resolved_at.isoformat() if conflict.resolved_at else None,
                "resolution_notes": conflict.resolution_notes,
                "created_at": conflict.created_at.isoformat()
            }
            for conflict in conflicts
        ]
    }


@router.post("/sync/conflicts/{conflict_id}/resolve")
async def resolve_sync_conflict(
    conflict_id: int,
    resolution_strategy: str,
    db: AsyncSession = Depends(get_db),
    resolved_value: Optional[str] = None,
    notes: Optional[str] = None
):
    """Manually resolve a synchronization conflict."""
    from app.models.sprint import ConflictResolutionStrategy
    
    sync_service = SyncService(db)
    
    try:
        # Convert string to enum
        strategy_enum = ConflictResolutionStrategy(resolution_strategy)
        
        resolved_conflict = await sync_service.resolve_conflict(
            conflict_id=conflict_id,
            resolution_strategy=strategy_enum,
            resolved_value=resolved_value,
            notes=notes
        )
        
        return {
            "message": "Conflict resolved successfully",
            "conflict": {
                "id": resolved_conflict.id,
                "resolution_strategy": resolved_conflict.resolution_strategy.value,
                "resolved_value": resolved_conflict.resolved_value,
                "resolved_at": resolved_conflict.resolved_at.isoformat(),
                "resolution_notes": resolved_conflict.resolution_notes
            }
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve conflict: {str(e)}"
        )


@router.get("/sync/history")
async def get_sync_history(
    db: AsyncSession = Depends(get_db),
    operation_type: Optional[str] = Query(None, description="Filter by operation type"),
    limit: int = Query(20, ge=1, le=100)
):
    """Get synchronization history."""
    sync_service = SyncService(db)
    
    history = await sync_service.get_sync_history(
        operation_type=operation_type,
        entity_type="sprint",
        limit=limit
    )
    
    return {
        "history": [
            {
                "id": h.id,
                "operation_type": h.operation_type,
                "entity_type": h.entity_type,
                "batch_id": h.batch_id,
                "status": h.status.value,
                "entities_processed": h.entities_processed,
                "entities_created": h.entities_created,
                "entities_updated": h.entities_updated,
                "entities_deleted": h.entities_deleted,
                "entities_skipped": h.entities_skipped,
                "conflicts_detected": h.conflicts_detected,
                "conflicts_resolved": h.conflicts_resolved,
                "duration_seconds": h.duration_seconds,
                "api_calls_made": h.api_calls_made,
                "error_message": h.error_message,
                "created_at": h.created_at.isoformat()
            }
            for h in history
        ]
    }


@router.post("/sync/validate-consistency")
async def validate_data_consistency(
    db: AsyncSession = Depends(get_db)
):
    """Validate data consistency between local and JIRA systems."""
    jira_service = JiraService()
    sync_service = SyncService(db)
    
    try:
        async with jira_service:
            validation_results = await sync_service.validate_data_consistency(
                jira_service=jira_service,
                entity_type="sprint"
            )
        
        return {
            "message": "Data consistency validation completed",
            "validation_results": validation_results
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate data consistency: {str(e)}"
        )