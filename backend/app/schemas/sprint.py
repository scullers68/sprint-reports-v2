"""
Sprint-related Pydantic schemas for API request/response models.

Defines data validation and serialization for sprint operations.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field, validator


# Sprint schemas
class SprintBase(BaseModel):
    """Base sprint schema with common fields."""
    name: str = Field(..., min_length=1, max_length=200)
    state: str = Field(..., pattern="^(future|active|closed)$")
    goal: Optional[str] = None
    board_id: Optional[int] = None
    origin_board_id: Optional[int] = None
    
    # JIRA sync metadata (optional for base schema)
    sync_status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed|failed|skipped)$")
    sync_conflicts: Optional[Dict[str, Any]] = None
    
    # Enhanced JIRA metadata
    jira_board_name: Optional[str] = Field(None, max_length=200)
    jira_project_key: Optional[str] = Field(None, max_length=50)
    jira_version: Optional[str] = Field(None, max_length=20)


class SprintCreate(SprintBase):
    """Schema for creating a new sprint."""
    jira_sprint_id: int = Field(..., gt=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    complete_date: Optional[datetime] = None
    jira_last_updated: Optional[datetime] = None


class SprintUpdate(BaseModel):
    """Schema for updating an existing sprint."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    state: Optional[str] = Field(None, pattern="^(future|active|closed)$")
    goal: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    complete_date: Optional[datetime] = None
    
    # JIRA sync metadata updates
    jira_last_updated: Optional[datetime] = None
    sync_status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed|failed|skipped)$")
    sync_conflicts: Optional[Dict[str, Any]] = None
    
    # Enhanced JIRA metadata updates
    jira_board_name: Optional[str] = Field(None, max_length=200)
    jira_project_key: Optional[str] = Field(None, max_length=50)
    jira_version: Optional[str] = Field(None, max_length=20)


class SprintRead(SprintBase):
    """Schema for reading sprint data."""
    id: int
    jira_sprint_id: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    complete_date: Optional[datetime] = None
    jira_last_updated: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Sprint Analysis schemas
class SprintAnalysisBase(BaseModel):
    """Base sprint analysis schema."""
    analysis_type: str = Field(default="discipline_team")
    jql_filter: Optional[str] = None
    exclude_subtasks: bool = Field(default=True)


class SprintAnalysisCreate(SprintAnalysisBase):
    """Schema for creating a sprint analysis."""
    pass


class SprintAnalysisRead(SprintAnalysisBase):
    """Schema for reading sprint analysis data."""
    id: int
    sprint_id: int
    total_issues: int
    total_story_points: float
    discipline_teams_count: int
    discipline_breakdown: Optional[Dict[str, Any]] = None
    issue_details: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DisciplineTeamStats(BaseModel):
    """Schema for discipline team statistics."""
    team_name: str
    issue_count: int
    story_points: float
    capacity: Optional[float] = None
    utilization: Optional[float] = None
    over_capacity: bool = False


class SprintAnalysisSummary(BaseModel):
    """Schema for sprint analysis summary with team breakdown."""
    sprint_name: str
    total_issues: int
    total_story_points: float
    discipline_teams: List[DisciplineTeamStats]
    analysis_date: datetime
    has_capacity_configured: bool = False