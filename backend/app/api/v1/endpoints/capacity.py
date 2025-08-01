"""
Discipline team capacity management endpoints.

Handles capacity configuration, allocation, and tracking.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/sprint/{sprint_id}")
async def get_sprint_capacities():
    """Get capacity configuration for a sprint."""
    return {"message": "Get sprint capacities endpoint - to be implemented"}


@router.post("/sprint/{sprint_id}")
async def configure_sprint_capacities():
    """Configure capacity for discipline teams in a sprint."""
    return {"message": "Configure capacities endpoint - to be implemented"}


@router.get("/teams")
async def list_discipline_teams():
    """List all discipline teams."""
    return {"message": "List discipline teams endpoint - to be implemented"}