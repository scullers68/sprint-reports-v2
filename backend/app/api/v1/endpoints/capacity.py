"""
Discipline team capacity management endpoints.

Handles capacity configuration, allocation, and tracking for multi-project context.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.capacity_service import (
    CapacityAnalysisService, CapacityPlanningService,
    OptimizationStrategy, CapacityConflictType
)
from app.core.logging import get_logger
from app.core.exceptions import NotFoundError, ValidationError

router = APIRouter()
logger = get_logger(__name__)


@router.get("/sprint/{sprint_id}")
async def get_sprint_capacities(
    sprint_id: int,
    include_projects: Optional[List[str]] = Query(None, description="Filter by project keys"),
    db: AsyncSession = Depends(get_db)
):
    """Get capacity configuration and distribution for a sprint."""
    try:
        service = CapacityAnalysisService(db)
        distributions = await service.analyze_capacity_distribution(
            sprint_id=sprint_id,
            include_projects=include_projects
        )
        
        # Transform to API response format
        response = {
            "sprint_id": sprint_id,
            "total_teams": len(distributions),
            "capacity_distributions": [
                {
                    "team_name": dist.team_name,
                    "total_capacity": dist.total_capacity,
                    "total_allocated": dist.total_allocated,
                    "utilization_percentage": dist.utilization_percentage,
                    "is_over_capacity": dist.is_over_capacity,
                    "available_capacity": dist.available_capacity,
                    "project_allocations": dist.project_allocations
                }
                for dist in distributions
            ]
        }
        
        return response
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting sprint capacities: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sprint/{sprint_id}/conflicts")
async def detect_capacity_conflicts(
    sprint_id: int,
    over_allocation_threshold: float = Query(1.1, description="Over-allocation threshold (1.1 = 110%)"),
    under_utilization_threshold: float = Query(0.5, description="Under-utilization threshold (0.5 = 50%)"),
    db: AsyncSession = Depends(get_db)
):
    """Detect capacity conflicts and issues within a sprint."""
    try:
        service = CapacityAnalysisService(db)
        conflicts = await service.detect_capacity_conflicts(
            sprint_id=sprint_id,
            threshold_over_allocation=over_allocation_threshold,
            threshold_under_utilization=under_utilization_threshold
        )
        
        # Group conflicts by severity
        conflicts_by_severity = {"high": [], "medium": [], "low": []}
        for conflict in conflicts:
            conflicts_by_severity[conflict.severity].append({
                "conflict_id": conflict.conflict_id,
                "conflict_type": conflict.conflict_type.value,
                "team_name": conflict.team_name,
                "project_key": conflict.project_key,
                "description": conflict.description,
                "impact_assessment": conflict.impact_assessment,
                "recommended_actions": conflict.recommended_actions,
                "metadata": conflict.metadata
            })
        
        return {
            "sprint_id": sprint_id,
            "total_conflicts": len(conflicts),
            "conflicts_by_severity": conflicts_by_severity,
            "thresholds": {
                "over_allocation": over_allocation_threshold,
                "under_utilization": under_utilization_threshold
            }
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error detecting capacity conflicts: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sprint/{sprint_id}")
async def configure_sprint_capacities():
    """Configure capacity for discipline teams in a sprint."""
    return {"message": "Configure capacities endpoint - to be implemented"}


@router.get("/forecast/project/{project_key}")
async def forecast_project_capacity(
    project_key: str,
    team_name: Optional[str] = Query(None, description="Specific team to forecast for"),
    forecast_periods: int = Query(3, description="Number of periods to forecast"),
    db: AsyncSession = Depends(get_db)
):
    """Forecast capacity needs for a project based on historical patterns."""
    try:
        service = CapacityAnalysisService(db)
        forecasts = await service.forecast_project_capacity_needs(
            project_key=project_key,
            team_name=team_name,
            forecast_periods=forecast_periods
        )
        
        response = {
            "project_key": project_key,
            "forecast_periods": forecast_periods,
            "team_filter": team_name,
            "forecasts": [
                {
                    "team_name": forecast.team_name,
                    "current_capacity": forecast.current_capacity,
                    "forecasted_need": forecast.forecasted_need,
                    "confidence_level": forecast.confidence_level,
                    "trend": forecast.trend,
                    "risk_factors": forecast.risk_factors,
                    "recommendations": forecast.recommendations
                }
                for forecast in forecasts
            ]
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error forecasting project capacity: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/optimization/sprint/{sprint_id}")
async def get_optimization_recommendations(
    sprint_id: int,
    strategy: OptimizationStrategy = Query(
        OptimizationStrategy.BALANCE_UTILIZATION,
        description="Optimization strategy to apply"
    ),
    db: AsyncSession = Depends(get_db)
):
    """Generate capacity optimization recommendations for a sprint."""
    try:
        service = CapacityAnalysisService(db)
        recommendations = await service.generate_optimization_recommendations(
            sprint_id=sprint_id,
            strategy=strategy
        )
        
        response = {
            "sprint_id": sprint_id,
            "strategy": strategy.value,
            "total_recommendations": len(recommendations),
            "recommendations": [
                {
                    "recommendation_id": rec.recommendation_id,
                    "strategy": rec.strategy.value,
                    "description": rec.description,
                    "expected_impact": rec.expected_impact,
                    "implementation_effort": rec.implementation_effort,
                    "affected_teams": rec.affected_teams,
                    "affected_projects": rec.affected_projects,
                    "specific_actions": rec.specific_actions,
                    "priority": rec.priority
                }
                for rec in recommendations
            ]
        }
        
        return response
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating optimization recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/utilization/project/{project_key}")
async def get_project_capacity_utilization(
    project_key: str,
    sprint_id: Optional[int] = Query(None, description="Specific sprint to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """Get capacity utilization report for a specific project."""
    try:
        service = CapacityAnalysisService(db)
        
        if sprint_id:
            # Get utilization for specific sprint
            distributions = await service.analyze_capacity_distribution(
                sprint_id=sprint_id,
                include_projects=[project_key]
            )
            
            project_utilization = {
                "project_key": project_key,
                "sprint_id": sprint_id,
                "teams": []
            }
            
            for dist in distributions:
                project_allocation = next(
                    (p for p in dist.project_allocations if p["project_key"] == project_key),
                    None
                )
                
                if project_allocation:
                    project_utilization["teams"].append({
                        "team_name": dist.team_name,
                        "allocated_capacity": project_allocation["allocated_capacity"],
                        "utilized_capacity": project_allocation["utilized_capacity"],
                        "capacity_percentage": project_allocation["capacity_percentage"],
                        "utilization_percentage": project_allocation["utilization_percentage"],
                        "priority": project_allocation.get("priority"),
                        "trend": project_allocation.get("trend")
                    })
            
            return project_utilization
        else:
            # Get historical utilization analysis
            historical_analysis = await service.get_historical_capacity_analysis(
                project_key=project_key
            )
            
            return {
                "project_key": project_key,
                "analysis_type": "historical",
                "analysis_data": historical_analysis
            }
        
    except Exception as e:
        logger.error(f"Error getting project utilization: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/utilization/team/{team_name}")
async def get_team_capacity_utilization(
    team_name: str,
    sprint_id: Optional[int] = Query(None, description="Specific sprint to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """Get capacity utilization report for a specific team."""
    try:
        service = CapacityAnalysisService(db)
        
        if sprint_id:
            # Get utilization for specific sprint
            distributions = await service.analyze_capacity_distribution(sprint_id)
            team_distribution = next(
                (d for d in distributions if d.team_name == team_name),
                None
            )
            
            if not team_distribution:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Team {team_name} not found in sprint {sprint_id}"
                )
            
            return {
                "team_name": team_name,
                "sprint_id": sprint_id,
                "total_capacity": team_distribution.total_capacity,
                "total_allocated": team_distribution.total_allocated,
                "utilization_percentage": team_distribution.utilization_percentage,
                "is_over_capacity": team_distribution.is_over_capacity,
                "available_capacity": team_distribution.available_capacity,
                "project_breakdown": team_distribution.project_allocations
            }
        else:
            # Get historical utilization analysis
            historical_analysis = await service.get_historical_capacity_analysis(
                team_name=team_name
            )
            
            return {
                "team_name": team_name,
                "analysis_type": "historical",
                "analysis_data": historical_analysis
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team utilization: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analysis/historical")
async def get_historical_capacity_analysis(
    team_name: Optional[str] = Query(None, description="Filter by team name"),
    project_key: Optional[str] = Query(None, description="Filter by project key"),
    periods: int = Query(6, description="Number of historical periods to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """Get historical capacity analysis with patterns and insights."""
    try:
        service = CapacityAnalysisService(db)
        analysis = await service.get_historical_capacity_analysis(
            team_name=team_name,
            project_key=project_key,
            periods=periods
        )
        
        return {
            "filters": {
                "team_name": team_name,
                "project_key": project_key,
                "periods": periods
            },
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"Error getting historical analysis: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/teams")
async def list_discipline_teams():
    """List all discipline teams."""
    return {"message": "List discipline teams endpoint - to be implemented"}


@router.get("/health")
async def capacity_service_health():
    """Health check endpoint for capacity service."""
    return {
        "service": "capacity",
        "status": "healthy",
        "features": [
            "multi_project_analysis",
            "capacity_distribution",
            "conflict_detection", 
            "forecasting",
            "optimization_recommendations",
            "historical_analysis"
        ]
    }