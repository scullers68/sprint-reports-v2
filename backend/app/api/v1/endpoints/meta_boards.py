"""
Meta-board portfolio dashboard API endpoints.

Provides RESTful endpoints for project portfolio management, aggregation,
and reporting within meta-board sprint contexts.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import create_success_response
from app.core.exceptions import ValidationError, NotFoundError
from app.core.logging import get_logger
from app.schemas.meta_boards import (
    ProjectPortfolioResponse,
    ProjectPortfolioFilters,
    ProjectCompletionForecast,
    ResourceAllocation,
    ProjectRanking,
    ProjectRankingCriteria,
    CacheMetrics
)
from app.services.sprint_service import SprintService
from app.services.sprint_cache_service import SprintCacheService

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/{board_id}/project-portfolio",
    response_model=Dict[str, Any],
    summary="Get project portfolio dashboard",
    description="Retrieve comprehensive project portfolio data for meta-board sprint dashboard"
)
async def get_project_portfolio(
    board_id: int,
    sprint_id: Optional[int] = Query(None, description="Specific sprint ID, if not provided uses active sprint"),
    project_keys: Optional[List[str]] = Query(None, description="Filter by specific project keys"),
    priority: Optional[List[str]] = Query(None, description="Filter by project priority"),
    health_status: Optional[List[str]] = Query(None, description="Filter by health status"),
    include_completed: bool = Query(True, description="Include completed projects"),
    include_cached: bool = Query(True, description="Use cached data when available"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get project portfolio dashboard data for a meta-board.
    
    Returns aggregated project metrics, health indicators, and progress tracking
    for all projects within the current sprint context.
    """
    try:
        logger.info(f"Fetching project portfolio for meta-board {board_id}")
        
        # Create service instances
        sprint_service = SprintService(db)
        cache_service = SprintCacheService(db)
        
        # Build filters
        filters = ProjectPortfolioFilters(
            project_keys=project_keys,
            priority=priority,
            health_status=health_status,
            include_completed=include_completed
        )
        
        # Get portfolio data using service layer
        portfolio_data = await sprint_service.get_project_portfolio(
            board_id=board_id,
            sprint_id=sprint_id,
            filters=filters,
            use_cache=include_cached
        )
        
        return create_success_response(
            data=portfolio_data,
            message="Project portfolio retrieved successfully"
        )
        
    except NotFoundError as e:
        logger.warning(f"Meta-board {board_id} not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        logger.warning(f"Validation error for portfolio request: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching project portfolio for board {board_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve project portfolio")


@router.get(
    "/{board_id}/project-forecasts",
    response_model=Dict[str, Any],
    summary="Get project completion forecasts",
    description="Retrieve project completion forecasts based on velocity and remaining work"
)
async def get_project_forecasts(
    board_id: int,
    sprint_id: Optional[int] = Query(None, description="Specific sprint ID"),
    project_keys: Optional[List[str]] = Query(None, description="Filter by project keys"),
    confidence_threshold: float = Query(0.7, ge=0.0, le=1.0, description="Minimum confidence level"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get project completion forecasts with velocity-based predictions.
    
    Returns estimated completion dates, confidence levels, and risk factors
    for projects within the meta-board sprint context.
    """
    try:
        logger.info(f"Generating project forecasts for meta-board {board_id}")
        
        sprint_service = SprintService(db)
        
        # Get forecasting data
        forecasts = await sprint_service.get_project_completion_forecasts(
            board_id=board_id,
            sprint_id=sprint_id,
            project_keys=project_keys,
            confidence_threshold=confidence_threshold
        )
        
        return create_success_response(
            data={"forecasts": forecasts},
            message="Project forecasts generated successfully"
        )
        
    except NotFoundError as e:
        logger.warning(f"Meta-board {board_id} not found for forecasting: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating forecasts for board {board_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate project forecasts")


@router.get(
    "/{board_id}/resource-allocation",
    response_model=Dict[str, Any],
    summary="Get project resource allocation",
    description="Retrieve resource allocation and capacity utilization across projects"
)
async def get_resource_allocation(
    board_id: int,
    sprint_id: Optional[int] = Query(None, description="Specific sprint ID"),
    include_discipline_breakdown: bool = Query(True, description="Include per-discipline allocation"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get resource allocation data for projects within meta-board sprint.
    
    Returns capacity allocation, utilization metrics, and team distribution
    across all projects in the sprint context.
    """
    try:
        logger.info(f"Fetching resource allocation for meta-board {board_id}")
        
        sprint_service = SprintService(db)
        
        # Get resource allocation data
        allocation_data = await sprint_service.get_project_resource_allocation(
            board_id=board_id,
            sprint_id=sprint_id,
            include_discipline_breakdown=include_discipline_breakdown
        )
        
        return create_success_response(
            data=allocation_data,
            message="Resource allocation retrieved successfully"
        )
        
    except NotFoundError as e:
        logger.warning(f"Meta-board {board_id} not found for resource allocation: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching resource allocation for board {board_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve resource allocation")


@router.get(
    "/{board_id}/project-rankings",
    response_model=Dict[str, Any],
    summary="Get project priority rankings",
    description="Retrieve project rankings based on priority, completion, or other criteria"
)
async def get_project_rankings(
    board_id: int,
    ranking_criteria: ProjectRankingCriteria = Query(
        ProjectRankingCriteria.PRIORITY,
        description="Criteria for ranking projects"
    ),
    sprint_id: Optional[int] = Query(None, description="Specific sprint ID"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of projects to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get project rankings within sprint context.
    
    Returns projects ranked by specified criteria such as priority,
    completion percentage, risk score, or velocity.
    """
    try:
        logger.info(f"Generating project rankings for meta-board {board_id} by {ranking_criteria}")
        
        sprint_service = SprintService(db)
        
        # Get project rankings
        rankings = await sprint_service.get_project_rankings(
            board_id=board_id,
            ranking_criteria=ranking_criteria,
            sprint_id=sprint_id,
            limit=limit
        )
        
        return create_success_response(
            data={
                "rankings": rankings,
                "criteria": ranking_criteria,
                "total_projects": len(rankings)
            },
            message="Project rankings generated successfully"
        )
        
    except NotFoundError as e:
        logger.warning(f"Meta-board {board_id} not found for rankings: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating rankings for board {board_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate project rankings")


@router.get(
    "/{board_id}/cache-metrics",
    response_model=Dict[str, Any],
    summary="Get portfolio cache metrics",
    description="Retrieve cache performance metrics for portfolio queries"
)
async def get_cache_metrics(
    board_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get cache performance metrics for portfolio queries.
    
    Returns cache hit rates, query performance, and cache utilization
    statistics for portfolio dashboard operations.
    """
    try:
        logger.info(f"Fetching cache metrics for meta-board {board_id}")
        
        cache_service = SprintCacheService(db)
        
        # Get cache metrics
        metrics = await cache_service.get_portfolio_cache_metrics(board_id)
        
        return create_success_response(
            data=metrics,
            message="Cache metrics retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error fetching cache metrics for board {board_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve cache metrics")


@router.post(
    "/{board_id}/refresh-cache",
    response_model=Dict[str, Any],
    summary="Refresh portfolio cache",
    description="Force refresh of cached portfolio data for improved performance"
)
async def refresh_portfolio_cache(
    board_id: int,
    sprint_id: Optional[int] = Query(None, description="Specific sprint ID to refresh"),
    db: AsyncSession = Depends(get_db)
):
    """
    Force refresh of portfolio cache data.
    
    Invalidates existing cache and rebuilds portfolio aggregations
    for improved query performance and data freshness.
    """
    try:
        logger.info(f"Refreshing portfolio cache for meta-board {board_id}")
        
        cache_service = SprintCacheService(db)
        
        # Refresh cache
        refresh_result = await cache_service.refresh_portfolio_cache(
            board_id=board_id,
            sprint_id=sprint_id
        )
        
        return create_success_response(
            data=refresh_result,
            message="Portfolio cache refreshed successfully"
        )
        
    except Exception as e:
        logger.error(f"Error refreshing cache for board {board_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to refresh portfolio cache")


@router.get(
    "/{board_id}/health-summary",
    response_model=Dict[str, Any],
    summary="Get portfolio health summary",
    description="Retrieve high-level health indicators and risk metrics for portfolio"
)
async def get_portfolio_health_summary(
    board_id: int,
    sprint_id: Optional[int] = Query(None, description="Specific sprint ID"),
    include_trends: bool = Query(True, description="Include trend analysis"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get portfolio health summary with risk indicators.
    
    Returns high-level health metrics, risk assessments, and trend analysis
    for executive-level portfolio oversight.
    """
    try:
        logger.info(f"Generating health summary for meta-board {board_id}")
        
        sprint_service = SprintService(db)
        
        # Get health summary
        health_summary = await sprint_service.get_portfolio_health_summary(
            board_id=board_id,
            sprint_id=sprint_id,
            include_trends=include_trends
        )
        
        return create_success_response(
            data=health_summary,
            message="Portfolio health summary generated successfully"
        )
        
    except NotFoundError as e:
        logger.warning(f"Meta-board {board_id} not found for health summary: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating health summary for board {board_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate portfolio health summary")