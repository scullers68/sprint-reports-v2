"""
Sprint-related Pydantic schemas for API request/response models.

Defines data validation and serialization for sprint operations.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field, validator
from enum import Enum


class MetaBoardTypeEnum(str, Enum):
    """Enumeration for meta-board types in schemas."""
    SINGLE_PROJECT = "single_project"
    MULTI_PROJECT = "multi_project"
    META_BOARD = "meta_board"


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
    
    # Meta-board support
    meta_board_type: Optional[MetaBoardTypeEnum] = Field(None, description="Type of meta-board configuration")
    project_source: Optional[Dict[str, Any]] = Field(None, description="Project source tracking for meta-boards")


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
    
    # Meta-board support updates
    meta_board_type: Optional[MetaBoardTypeEnum] = Field(None, description="Type of meta-board configuration")
    project_source: Optional[Dict[str, Any]] = Field(None, description="Project source tracking for meta-boards")


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


# Meta-Board Configuration schemas
class MetaBoardConfigurationBase(BaseModel):
    """Base meta-board configuration schema."""
    board_id: int = Field(..., gt=0)
    board_name: str = Field(..., min_length=1, max_length=200)
    configuration_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: bool = Field(default=True)
    require_consistency_validation: bool = Field(default=True)


class MetaBoardConfigurationCreate(MetaBoardConfigurationBase):
    """Schema for creating a meta-board configuration."""
    aggregation_rules: Dict[str, Any] = Field(..., description="Rules for aggregating project data")
    project_mappings: Dict[str, Any] = Field(..., description="Project source mappings and filtering")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Custom validation rules")


class MetaBoardConfigurationUpdate(BaseModel):
    """Schema for updating a meta-board configuration."""
    configuration_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    aggregation_rules: Optional[Dict[str, Any]] = Field(None, description="Rules for aggregating project data")
    project_mappings: Optional[Dict[str, Any]] = Field(None, description="Project source mappings and filtering")
    require_consistency_validation: Optional[bool] = None
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Custom validation rules")
    is_active: Optional[bool] = None


class MetaBoardConfigurationRead(MetaBoardConfigurationBase):
    """Schema for reading meta-board configuration data."""
    id: int
    aggregation_rules: Dict[str, Any]
    project_mappings: Dict[str, Any]
    validation_rules: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MetaBoardDetectionResult(BaseModel):
    """Schema for meta-board detection results."""
    is_meta_board: bool
    board_id: int
    confidence: float = Field(..., ge=0.0, le=1.0)
    analysis: Dict[str, Any]
    suggestions: List[Dict[str, Any]]
    error: Optional[str] = None