"""
Project-based task organization models for sprint management.

Enables tracking and reporting on multiple project workstreams within sprints.
"""

from datetime import datetime
from typing import Optional
import enum

from sqlalchemy import Column, String, DateTime, Integer, Float, Text, Boolean, ForeignKey, JSON, Index, CheckConstraint, Enum
from sqlalchemy.orm import relationship, validates

from app.models.base import Base


class WorkstreamType(enum.Enum):
    """Enumeration for workstream types."""
    STANDARD = "standard"
    EPIC = "epic"  
    INITIATIVE = "initiative"


class AssociationType(enum.Enum):
    """Enumeration for project-sprint association types."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    DEPENDENCY = "dependency"


class ProjectWorkstream(Base):
    """Project workstream model for representing project sources within meta-board sprints."""
    
    __tablename__ = "project_workstreams"
    
    # Project identification
    project_key = Column(String(50), nullable=False, unique=True, index=True)
    project_name = Column(String(200), nullable=False, index=True)
    project_id = Column(String(100), nullable=True, index=True)  # External project ID (e.g., JIRA project ID)
    
    # JIRA integration metadata
    jira_board_id = Column(Integer, nullable=True, index=True)
    jira_board_name = Column(String(200), nullable=True)
    
    # Workstream classification
    workstream_type = Column(Enum(WorkstreamType), default=WorkstreamType.STANDARD, nullable=False, index=True)
    
    # Status and configuration
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    project_category = Column(String(100), nullable=True, index=True)  # Development, Research, Operations, etc.
    
    # Extensible metadata
    project_metadata = Column(JSON, nullable=True)  # Additional project-specific configuration
    
    # Audit fields
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    last_modified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    created_by_user = relationship("User", foreign_keys=[created_by])
    last_modified_by_user = relationship("User", foreign_keys=[last_modified_by])
    sprint_associations = relationship("ProjectSprintAssociation", back_populates="project_workstream", cascade="all, delete-orphan")
    
    # Table constraints and indexes
    __table_args__ = (
        # Ensure project key and name are not empty
        CheckConstraint("trim(project_key) != ''", name='project_key_not_empty'),
        CheckConstraint("trim(project_name) != ''", name='project_name_not_empty'),
        # Performance indexes
        Index('idx_project_active_type', 'is_active', 'workstream_type'),
        Index('idx_project_category', 'project_category', 'is_active'),
        Index('idx_project_jira_board', 'jira_board_id', 'is_active'),
    )
    
    @validates('project_key', 'project_name')
    def validate_not_empty(self, key, value):
        """Validate string fields are not empty."""
        if value and len(value.strip()) == 0:
            raise ValueError(f"{key} cannot be empty")
        return value.strip() if value else value
    
    @validates('workstream_type')
    def validate_workstream_type(self, key, workstream_type):
        """Validate workstream type."""
        if workstream_type and not isinstance(workstream_type, WorkstreamType):
            try:
                # Try to convert string to enum if needed
                if isinstance(workstream_type, str):
                    workstream_type = WorkstreamType(workstream_type)
            except ValueError:
                valid_types = [t.value for t in WorkstreamType]
                raise ValueError(f"Invalid workstream type. Must be one of: {valid_types}")
        return workstream_type
    
    def __repr__(self) -> str:
        return f"<ProjectWorkstream(id={self.id}, key='{self.project_key}', name='{self.project_name}')>"


class ProjectSprintAssociation(Base):
    """Many-to-many association between Sprint and ProjectWorkstream."""
    
    __tablename__ = "project_sprint_associations"
    
    # Foreign keys
    sprint_id = Column(Integer, ForeignKey("sprints.id"), nullable=False, index=True)
    project_workstream_id = Column(Integer, ForeignKey("project_workstreams.id"), nullable=False, index=True)
    
    # Association metadata
    association_type = Column(Enum(AssociationType), default=AssociationType.PRIMARY, nullable=False, index=True)
    project_priority = Column(Integer, nullable=True)  # Priority within the sprint context
    
    # Capacity tracking
    expected_story_points = Column(Float, nullable=True, default=0.0)
    actual_story_points = Column(Float, nullable=True, default=0.0)
    
    # Status and notes
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    
    # Audit fields
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    sprint = relationship("Sprint")
    project_workstream = relationship("ProjectWorkstream", back_populates="sprint_associations")
    created_by_user = relationship("User")
    
    # Table constraints and indexes
    __table_args__ = (
        # Unique constraint to prevent duplicate associations
        Index('idx_unique_sprint_project', 'sprint_id', 'project_workstream_id', unique=True),
        # Ensure non-negative story points
        CheckConstraint("expected_story_points IS NULL OR expected_story_points >= 0", name='non_negative_expected_points'),
        CheckConstraint("actual_story_points IS NULL OR actual_story_points >= 0", name='non_negative_actual_points'),
        CheckConstraint("project_priority IS NULL OR project_priority > 0", name='positive_priority'),
        # Performance indexes
        Index('idx_association_sprint_type', 'sprint_id', 'association_type', 'is_active'),
        Index('idx_association_project_active', 'project_workstream_id', 'is_active'),
        Index('idx_association_priority', 'project_priority', 'is_active'),
    )
    
    @validates('expected_story_points', 'actual_story_points')
    def validate_non_negative_points(self, key, value):
        """Validate non-negative story points."""
        if value is not None and value < 0:
            raise ValueError(f"{key} cannot be negative")
        return value
    
    @validates('project_priority')
    def validate_priority(self, key, value):
        """Validate priority is positive."""
        if value is not None and value <= 0:
            raise ValueError("Project priority must be positive")
        return value
    
    @validates('association_type')
    def validate_association_type(self, key, association_type):
        """Validate association type."""
        if association_type and not isinstance(association_type, AssociationType):
            try:
                # Try to convert string to enum if needed
                if isinstance(association_type, str):
                    association_type = AssociationType(association_type)
            except ValueError:
                valid_types = [t.value for t in AssociationType]
                raise ValueError(f"Invalid association type. Must be one of: {valid_types}")
        return association_type
    
    def __repr__(self) -> str:
        return f"<ProjectSprintAssociation(id={self.id}, sprint_id={self.sprint_id}, project_id={self.project_workstream_id})>"


class ProjectSprintMetrics(Base):
    """Project-level metrics tracking within sprints."""
    
    __tablename__ = "project_sprint_metrics"
    
    # Foreign keys
    sprint_id = Column(Integer, ForeignKey("sprints.id"), nullable=False, index=True)
    project_workstream_id = Column(Integer, ForeignKey("project_workstreams.id"), nullable=False, index=True)
    
    # Issue metrics
    total_issues = Column(Integer, nullable=False, default=0)
    completed_issues = Column(Integer, nullable=False, default=0)
    in_progress_issues = Column(Integer, nullable=False, default=0)
    blocked_issues = Column(Integer, nullable=False, default=0)
    
    # Story point metrics
    total_story_points = Column(Float, nullable=False, default=0.0)
    completed_story_points = Column(Float, nullable=False, default=0.0)
    in_progress_story_points = Column(Float, nullable=False, default=0.0)
    
    # Progress metrics (percentages)
    completion_percentage = Column(Float, nullable=False, default=0.0)
    velocity = Column(Float, nullable=True)  # Story points per day/week
    burndown_rate = Column(Float, nullable=True)  # Rate of completion
    
    # Quality metrics
    bug_count = Column(Integer, nullable=False, default=0)
    critical_issues_count = Column(Integer, nullable=False, default=0)
    
    # Team allocation
    team_allocation_percentage = Column(Float, nullable=True)  # % of team working on this project
    capacity_utilization = Column(Float, nullable=True)  # How much of allocated capacity is used
    
    # Scope tracking
    scope_change_count = Column(Integer, nullable=False, default=0)
    scope_added_points = Column(Float, nullable=False, default=0.0)
    scope_removed_points = Column(Float, nullable=False, default=0.0)
    
    # Detailed breakdowns (JSON)
    issue_breakdown = Column(JSON, nullable=True)  # Detailed issue analysis
    team_breakdown = Column(JSON, nullable=True)  # Per-team contribution breakdown
    timeline_breakdown = Column(JSON, nullable=True)  # Progress over time
    
    # Historical comparison
    previous_velocity = Column(Float, nullable=True)
    velocity_trend = Column(String(20), nullable=True)  # improving, declining, stable
    
    # Metadata
    metrics_date = Column(DateTime(timezone=True), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    sprint = relationship("Sprint")
    project_workstream = relationship("ProjectWorkstream")
    created_by_user = relationship("User")
    
    # Table constraints and indexes
    __table_args__ = (
        # Unique constraint for one metrics record per sprint-project combination per date
        Index('idx_unique_sprint_project_date', 'sprint_id', 'project_workstream_id', 'metrics_date', unique=True),
        # Ensure non-negative counts
        CheckConstraint("total_issues >= 0", name='non_negative_total_issues'),
        CheckConstraint("completed_issues >= 0", name='non_negative_completed_issues'),
        CheckConstraint("in_progress_issues >= 0", name='non_negative_in_progress_issues'),
        CheckConstraint("blocked_issues >= 0", name='non_negative_blocked_issues'),
        CheckConstraint("bug_count >= 0", name='non_negative_bugs'),
        CheckConstraint("critical_issues_count >= 0", name='non_negative_critical'),
        CheckConstraint("scope_change_count >= 0", name='non_negative_scope_changes'),
        # Ensure non-negative story points
        CheckConstraint("total_story_points >= 0", name='non_negative_total_points'),
        CheckConstraint("completed_story_points >= 0", name='non_negative_completed_points'),
        CheckConstraint("in_progress_story_points >= 0", name='non_negative_in_progress_points'),
        CheckConstraint("scope_added_points >= 0", name='non_negative_added_points'),
        CheckConstraint("scope_removed_points >= 0", name='non_negative_removed_points'),
        # Ensure valid percentages
        CheckConstraint("completion_percentage >= 0 AND completion_percentage <= 100", name='valid_completion_percentage'),
        CheckConstraint("team_allocation_percentage IS NULL OR (team_allocation_percentage >= 0 AND team_allocation_percentage <= 100)", name='valid_allocation_percentage'),
        CheckConstraint("capacity_utilization IS NULL OR capacity_utilization >= 0", name='non_negative_utilization'),
        # Logical constraints
        CheckConstraint("completed_issues <= total_issues", name='completed_not_greater_than_total'),
        CheckConstraint("completed_story_points <= total_story_points", name='completed_points_not_greater_than_total'),
        # Ensure valid velocity trend
        CheckConstraint("velocity_trend IS NULL OR velocity_trend IN ('improving', 'declining', 'stable')", name='valid_velocity_trend'),
        # Performance indexes
        Index('idx_metrics_sprint_date', 'sprint_id', 'metrics_date'),
        Index('idx_metrics_project_date', 'project_workstream_id', 'metrics_date'),
        Index('idx_metrics_completion', 'completion_percentage', 'metrics_date'),
        Index('idx_metrics_velocity', 'velocity', 'metrics_date'),
    )
    
    @validates('total_issues', 'completed_issues', 'in_progress_issues', 'blocked_issues', 'bug_count', 'critical_issues_count', 'scope_change_count')
    def validate_non_negative_counts(self, key, value):
        """Validate non-negative count values."""
        if value is not None and value < 0:
            raise ValueError(f"{key} cannot be negative")
        return value
    
    @validates('total_story_points', 'completed_story_points', 'in_progress_story_points', 'scope_added_points', 'scope_removed_points')
    def validate_non_negative_points(self, key, value):
        """Validate non-negative story point values."""
        if value is not None and value < 0:
            raise ValueError(f"{key} cannot be negative")
        return value
    
    @validates('completion_percentage')
    def validate_completion_percentage(self, key, value):
        """Validate completion percentage range."""
        if value is not None and (value < 0 or value > 100):
            raise ValueError("Completion percentage must be between 0 and 100")
        return value
    
    @validates('team_allocation_percentage')
    def validate_allocation_percentage(self, key, value):
        """Validate team allocation percentage range."""
        if value is not None and (value < 0 or value > 100):
            raise ValueError("Team allocation percentage must be between 0 and 100")
        return value
    
    @validates('capacity_utilization')
    def validate_capacity_utilization(self, key, value):
        """Validate capacity utilization is non-negative."""
        if value is not None and value < 0:
            raise ValueError("Capacity utilization cannot be negative")
        return value
    
    @validates('velocity_trend')
    def validate_velocity_trend(self, key, value):
        """Validate velocity trend."""
        if value and value not in ['improving', 'declining', 'stable']:
            raise ValueError("Velocity trend must be one of: improving, declining, stable")
        return value
    
    def __repr__(self) -> str:
        return f"<ProjectSprintMetrics(id={self.id}, sprint_id={self.sprint_id}, project_id={self.project_workstream_id}, completion={self.completion_percentage}%)>"
    
    @property
    def remaining_issues(self) -> int:
        """Calculate remaining issues."""
        return max(0, self.total_issues - self.completed_issues)
    
    @property
    def remaining_story_points(self) -> float:
        """Calculate remaining story points."""
        return max(0.0, self.total_story_points - self.completed_story_points)
    
    @property
    def is_on_track(self) -> bool:
        """Check if project is on track based on completion percentage and time progress."""
        # This is a simplified check - could be enhanced with actual sprint timeline
        return self.completion_percentage >= 50.0  # Basic threshold
    
    def update_completion_percentage(self) -> None:
        """Recalculate completion percentage based on current metrics."""
        if self.total_story_points > 0:
            self.completion_percentage = (self.completed_story_points / self.total_story_points) * 100
        elif self.total_issues > 0:
            self.completion_percentage = (self.completed_issues / self.total_issues) * 100
        else:
            self.completion_percentage = 0.0