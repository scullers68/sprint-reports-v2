"""
Sprint reporting endpoints.

Handles report generation, snapshots, and analytics.
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.sprint_service import SprintService
from app.core.exceptions import NotFoundError, ValidationError

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


# ========== PROJECT PROGRESS REPORTING ENDPOINTS ==========

@router.get("/project/{project_key}/velocity")
async def get_project_velocity_analysis(
    project_key: str,
    sprint_count: int = Query(5, description="Number of historical sprints to analyze"),
    include_current: bool = Query(True, description="Include current/active sprint"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get project velocity analysis with historical trends.
    
    Args:
        project_key: Project key to analyze
        sprint_count: Number of historical sprints to analyze
        include_current: Whether to include current/active sprint data
        
    Returns:
        Comprehensive velocity analysis with trends and predictions
    """
    try:
        sprint_service = SprintService(db)
        velocity_data = await sprint_service.calculate_project_velocity_with_history(
            project_key=project_key,
            sprint_count=sprint_count,
            include_current=include_current
        )
        return velocity_data
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating velocity: {str(e)}")


@router.post("/project/{project_key}/forecast")
async def get_project_completion_forecast(
    project_key: str,
    remaining_story_points: float,
    simulation_runs: int = Query(1000, description="Number of Monte Carlo simulation runs"),
    confidence_levels: List[float] = Query([0.5, 0.8, 0.95], description="Confidence levels for forecasting"),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate Monte Carlo completion forecast for project.
    
    Args:
        project_key: Project key to forecast
        remaining_story_points: Remaining work in story points
        simulation_runs: Number of simulation iterations
        confidence_levels: Confidence levels for forecasting intervals
        
    Returns:
        Monte Carlo simulation results with completion probabilities
    """
    try:
        sprint_service = SprintService(db)
        forecast_data = await sprint_service.monte_carlo_completion_forecast(
            project_key=project_key,
            remaining_story_points=remaining_story_points,
            simulation_runs=simulation_runs,
            confidence_levels=confidence_levels
        )
        return forecast_data
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating forecast: {str(e)}")


@router.get("/project/{project_key}/burndown")
async def get_project_burndown_data(
    project_key: str,
    sprint_id: int,
    include_burnup: bool = Query(True, description="Include burnup chart data"),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate project burndown and burnup chart data.
    
    Args:
        project_key: Project key to analyze
        sprint_id: Sprint ID for context
        include_burnup: Whether to include burnup chart data
        
    Returns:
        Burndown and burnup chart data with daily tracking
    """
    try:
        sprint_service = SprintService(db)
        burndown_data = await sprint_service.generate_project_burndown_data(
            project_key=project_key,
            sprint_id=sprint_id,
            include_burnup=include_burnup
        )
        return burndown_data
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating burndown data: {str(e)}")


@router.get("/project/{project_key}/risk-assessment")
async def get_project_risk_assessment(
    project_key: str,
    sprint_id: Optional[int] = Query(None, description="Sprint ID, defaults to active sprint"),
    include_capacity_analysis: bool = Query(True, description="Include team capacity analysis"),
    db: AsyncSession = Depends(get_db)
):
    """
    Assess project risks based on velocity trends and capacity constraints.
    
    Args:
        project_key: Project key to analyze
        sprint_id: Optional specific sprint, defaults to active sprint
        include_capacity_analysis: Whether to include team capacity analysis
        
    Returns:
        Comprehensive risk assessment with mitigation recommendations
    """
    try:
        sprint_service = SprintService(db)
        risk_assessment = await sprint_service.assess_project_risks(
            project_key=project_key,
            sprint_id=sprint_id,
            include_capacity_analysis=include_capacity_analysis
        )
        return risk_assessment
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error assessing risks: {str(e)}")


@router.get("/project/{project_key}/milestones")
async def get_project_milestones(
    project_key: str,
    sprint_id: Optional[int] = Query(None, description="Sprint ID, defaults to active sprint"),
    milestone_types: Optional[List[str]] = Query(None, description="Filter for milestone types"),
    db: AsyncSession = Depends(get_db)
):
    """
    Track project milestones within sprint context.
    
    Args:
        project_key: Project key to analyze
        sprint_id: Optional specific sprint, defaults to active sprint
        milestone_types: Optional filter for milestone types
        
    Returns:
        Project milestone tracking data with progress indicators
    """
    try:
        sprint_service = SprintService(db)
        milestone_data = await sprint_service.track_project_milestones(
            project_key=project_key,
            sprint_id=sprint_id,
            milestone_types=milestone_types
        )
        return milestone_data
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error tracking milestones: {str(e)}")


@router.get("/project/{project_key}/dependencies")
async def get_project_dependencies(
    project_key: str,
    sprint_id: Optional[int] = Query(None, description="Sprint ID, defaults to active sprint"),
    include_impact_analysis: bool = Query(True, description="Include dependency impact analysis"),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze project dependencies and their impact on progress.
    
    Args:
        project_key: Project key to analyze
        sprint_id: Optional specific sprint, defaults to active sprint
        include_impact_analysis: Whether to include dependency impact analysis
        
    Returns:
        Project dependency analysis with impact assessment
    """
    try:
        sprint_service = SprintService(db)
        dependency_data = await sprint_service.analyze_project_dependencies(
            project_key=project_key,
            sprint_id=sprint_id,
            include_impact_analysis=include_impact_analysis
        )
        return dependency_data
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing dependencies: {str(e)}")


@router.get("/project/{project_key}/comprehensive")
async def get_comprehensive_project_report(
    project_key: str,
    sprint_id: Optional[int] = Query(None, description="Sprint ID, defaults to active sprint"),
    include_forecast: bool = Query(True, description="Include Monte Carlo forecast"),
    include_dependencies: bool = Query(True, description="Include dependency analysis"),
    include_milestones: bool = Query(True, description="Include milestone tracking"),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate comprehensive project progress report combining all analysis types.
    
    Args:
        project_key: Project key to analyze
        sprint_id: Optional specific sprint, defaults to active sprint
        include_forecast: Whether to include Monte Carlo forecasting
        include_dependencies: Whether to include dependency analysis
        include_milestones: Whether to include milestone tracking
        
    Returns:
        Comprehensive project progress report with all analysis components
    """
    try:
        sprint_service = SprintService(db)
        
        # Get base project information
        if sprint_id:
            sprint = await sprint_service.get_sprint(sprint_id)
        else:
            sprint = await sprint_service._get_active_sprint_for_project(project_key)
        
        if not sprint:
            raise HTTPException(status_code=404, detail="No active sprint found for project")
        
        # Collect all analysis components
        report_components = {}
        
        # Velocity analysis (always included)
        try:
            report_components["velocity_analysis"] = await sprint_service.calculate_project_velocity_with_history(project_key)
        except Exception as e:
            report_components["velocity_analysis"] = {"error": str(e)}
        
        # Risk assessment (always included)
        try:
            report_components["risk_assessment"] = await sprint_service.assess_project_risks(project_key, sprint.id)
        except Exception as e:
            report_components["risk_assessment"] = {"error": str(e)}
        
        # Burndown data (always included)
        try:
            report_components["burndown_data"] = await sprint_service.generate_project_burndown_data(project_key, sprint.id)
        except Exception as e:
            report_components["burndown_data"] = {"error": str(e)}
        
        # Optional components
        if include_forecast and "velocity_analysis" in report_components and "error" not in report_components["velocity_analysis"]:
            try:
                # Calculate remaining story points from burndown data
                burndown = report_components.get("burndown_data", {})
                if "burndown_data" in burndown and burndown["burndown_data"]:
                    remaining_points = burndown["burndown_data"][-1].get("remaining_story_points", 50.0)
                else:
                    remaining_points = 50.0  # Default fallback
                
                report_components["completion_forecast"] = await sprint_service.monte_carlo_completion_forecast(
                    project_key, remaining_points
                )
            except Exception as e:
                report_components["completion_forecast"] = {"error": str(e)}
        
        if include_dependencies:
            try:
                report_components["dependency_analysis"] = await sprint_service.analyze_project_dependencies(
                    project_key, sprint.id
                )
            except Exception as e:
                report_components["dependency_analysis"] = {"error": str(e)}
        
        if include_milestones:
            try:
                report_components["milestone_tracking"] = await sprint_service.track_project_milestones(
                    project_key, sprint.id
                )
            except Exception as e:
                report_components["milestone_tracking"] = {"error": str(e)}
        
        # Generate overall health score
        health_score = 100.0
        health_factors = []
        
        # Adjust based on risk assessment
        if "risk_assessment" in report_components and "error" not in report_components["risk_assessment"]:
            risk = report_components["risk_assessment"]["risk_assessment"]
            health_score -= risk["risk_score"]
            if risk["overall_risk_level"] in ["high", "critical"]:
                health_factors.append(f"High project risk ({risk['overall_risk_level']})")
        
        # Adjust based on velocity trends
        if "velocity_analysis" in report_components and "error" not in report_components["velocity_analysis"]:
            velocity = report_components["velocity_analysis"]["trends"]
            if velocity["trend_direction"] == "declining":
                health_score -= 15
                health_factors.append("Declining velocity trend")
            elif velocity["consistency_score"] < 50:
                health_score -= 10
                health_factors.append("Inconsistent velocity")
        
        # Adjust based on dependencies
        if "dependency_analysis" in report_components and "error" not in report_components["dependency_analysis"]:
            deps = report_components["dependency_analysis"]
            if "impact_analysis" in deps and deps["impact_analysis"]:
                impact = deps["impact_analysis"]
                if impact["risk_level"] in ["high", "critical"]:
                    health_score -= impact["overall_risk_score"] * 0.3
                    health_factors.append(f"High dependency risk ({impact['risk_level']})")
        
        health_score = max(0, health_score)
        health_level = (
            "excellent" if health_score >= 85 else
            "good" if health_score >= 70 else
            "fair" if health_score >= 50 else
            "poor" if health_score >= 25 else
            "critical"
        )
        
        return {
            "project_key": project_key,
            "sprint_id": sprint.id,
            "sprint_name": sprint.name,
            "report_generated": datetime.now(timezone.utc).isoformat(),
            "overall_health": {
                "health_score": round(health_score, 1),
                "health_level": health_level,
                "health_factors": health_factors
            },
            "components": report_components
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating comprehensive report: {str(e)}")