"""
Sprint reporting endpoints.

Handles report generation, snapshots, and analytics.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_reports():
    """List all reports."""
    return {"message": "List reports endpoint - to be implemented"}


@router.post("/")
async def create_report():
    """Create a new report."""
    return {"message": "Create report endpoint - to be implemented"}


@router.post("/{report_id}/generate")
async def generate_report():
    """Generate report content."""
    return {"message": "Generate report endpoint - to be implemented"}