"""
Meta-board portfolio dashboard API schemas.

Provides Pydantic models for project portfolio dashboard responses,
following existing schema patterns for consistent API design.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field


class ProjectHealthStatus(str, Enum):
    """Project health status enumeration."""
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BEHIND = "behind"
    BLOCKED = "blocked"


class ProjectPriority(str, Enum):
    """Project priority enumeration."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProjectMetrics(BaseModel):
    """Project-level metrics within sprint context."""
    project_key: str = Field(..., description="Project key identifier")
    project_name: str = Field(..., description="Project name")
    
    # Issue metrics
    total_issues: int = Field(default=0, ge=0)
    completed_issues: int = Field(default=0, ge=0)
    in_progress_issues: int = Field(default=0, ge=0)
    blocked_issues: int = Field(default=0, ge=0)
    
    # Story point metrics
    total_story_points: float = Field(default=0.0, ge=0)
    completed_story_points: float = Field(default=0.0, ge=0)
    in_progress_story_points: float = Field(default=0.0, ge=0)
    
    # Progress indicators
    completion_percentage: float = Field(default=0.0, ge=0, le=100)
    velocity: Optional[float] = Field(None, ge=0, description="Story points per day")
    burndown_rate: Optional[float] = Field(None, description="Rate of completion")
    
    # Health indicators
    health_status: ProjectHealthStatus = Field(default=ProjectHealthStatus.ON_TRACK)
    risk_score: float = Field(default=0.0, ge=0, le=100, description="Risk score (0-100)")
    priority: ProjectPriority = Field(default=ProjectPriority.MEDIUM)
    
    # Resource allocation
    team_allocation_percentage: Optional[float] = Field(None, ge=0, le=100)
    capacity_utilization: Optional[float] = Field(None, ge=0)
    
    # Forecasting
    estimated_completion_date: Optional[datetime] = None
    days_remaining: Optional[int] = None
    confidence_level: Optional[float] = Field(None, ge=0, le=100)


class ProjectCompletionForecast(BaseModel):
    """Project completion forecast based on velocity and remaining work."""
    project_key: str
    project_name: str
    current_velocity: Optional[float] = Field(None, ge=0)
    remaining_story_points: float = Field(default=0.0, ge=0)
    estimated_completion_date: Optional[datetime] = None
    confidence_level: float = Field(default=0.0, ge=0, le=100)
    risk_factors: List[str] = Field(default_factory=list)
    scenarios: Dict[str, Any] = Field(default_factory=dict, description="Best/worst/likely case scenarios")


class ResourceAllocation(BaseModel):
    """Resource allocation data for project within sprint."""
    project_key: str
    project_name: str
    allocated_capacity: float = Field(default=0.0, ge=0)
    utilized_capacity: float = Field(default=0.0, ge=0)
    utilization_percentage: float = Field(default=0.0, ge=0, le=100)
    team_members_assigned: int = Field(default=0, ge=0)
    disciplines_involved: List[str] = Field(default_factory=list)
    capacity_status: str = Field(default="normal")  # normal, over, under


class SprintHealthIndicator(BaseModel):
    """Overall sprint health indicator."""
    metric_name: str
    current_value: float
    target_value: Optional[float] = None
    status: str  # good, warning, critical
    trend: str  # improving, stable, declining
    details: Optional[str] = None


class ProjectPortfolioSummary(BaseModel):
    """Summary data for project portfolio dashboard."""
    meta_board_id: int
    meta_board_name: str
    sprint_id: Optional[int] = None
    sprint_name: Optional[str] = None
    
    # Portfolio metrics
    total_projects: int = Field(default=0, ge=0)
    active_projects: int = Field(default=0, ge=0)
    completed_projects: int = Field(default=0, ge=0)
    blocked_projects: int = Field(default=0, ge=0)
    
    # Aggregate metrics
    total_story_points: float = Field(default=0.0, ge=0)
    completed_story_points: float = Field(default=0.0, ge=0)
    overall_completion_percentage: float = Field(default=0.0, ge=0, le=100)
    
    # Team metrics
    total_team_capacity: float = Field(default=0.0, ge=0)
    utilized_capacity: float = Field(default=0.0, ge=0)
    capacity_utilization_percentage: float = Field(default=0.0, ge=0, le=100)
    
    # Health indicators
    projects_on_track: int = Field(default=0, ge=0)
    projects_at_risk: int = Field(default=0, ge=0)
    projects_behind: int = Field(default=0, ge=0)
    average_risk_score: float = Field(default=0.0, ge=0, le=100)
    
    # Forecasting
    estimated_sprint_completion: Optional[datetime] = None
    forecast_confidence: Optional[float] = Field(None, ge=0, le=100)
    
    # Timestamps
    last_updated: datetime
    cache_expires_at: Optional[datetime] = None


class ProjectPortfolioResponse(BaseModel):
    """Complete project portfolio dashboard response."""
    summary: ProjectPortfolioSummary
    projects: List[ProjectMetrics]
    health_indicators: List[SprintHealthIndicator]
    last_sync: Optional[datetime] = None
    data_freshness: str = Field(default="current")  # current, stale, cached


class ProjectPortfolioFilters(BaseModel):
    """Filtering options for project portfolio queries."""
    project_keys: Optional[List[str]] = None
    priority: Optional[List[ProjectPriority]] = None
    health_status: Optional[List[ProjectHealthStatus]] = None
    min_completion_percentage: Optional[float] = Field(None, ge=0, le=100)
    max_completion_percentage: Optional[float] = Field(None, ge=0, le=100)
    include_completed: bool = Field(default=True)
    include_blocked: bool = Field(default=True)


class ProjectRankingCriteria(str, Enum):
    """Criteria for project ranking."""
    PRIORITY = "priority"
    COMPLETION = "completion"
    RISK_SCORE = "risk_score"
    VELOCITY = "velocity"
    CAPACITY_UTILIZATION = "capacity_utilization"


class ProjectRanking(BaseModel):
    """Project ranking within sprint context."""
    project_key: str
    project_name: str
    rank: int = Field(..., ge=1)
    score: float
    ranking_criteria: ProjectRankingCriteria
    justification: Optional[str] = None


class CacheMetrics(BaseModel):
    """Cache performance metrics for portfolio queries."""
    cache_hit_rate: float = Field(default=0.0, ge=0, le=100)
    avg_query_time_ms: float = Field(default=0.0, ge=0)
    cache_size_mb: float = Field(default=0.0, ge=0)
    cache_entries: int = Field(default=0, ge=0)
    last_cache_refresh: Optional[datetime] = None


class PortfolioCacheStrategy(BaseModel):
    """Portfolio cache strategy configuration."""
    cache_ttl_minutes: int = Field(default=5, ge=1, le=60)
    enable_background_refresh: bool = Field(default=True)
    invalidate_on_sprint_update: bool = Field(default=True)
    max_cache_entries: int = Field(default=1000, ge=100)