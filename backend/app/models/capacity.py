"""
Capacity models for discipline team capacity management.

Handles capacity planning, allocation, and tracking across discipline teams.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, Integer, Float, Text, Boolean, ForeignKey, JSON, Index, CheckConstraint
from sqlalchemy.orm import relationship, validates

from app.models.base import Base


class DisciplineTeamCapacity(Base):
    """Discipline team capacity configuration for sprints."""
    
    __tablename__ = "discipline_team_capacities"
    
    # Foreign keys
    sprint_id = Column(Integer, ForeignKey("sprints.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Team identification
    discipline_team = Column(String(100), nullable=False, index=True)
    
    # Capacity configuration
    capacity_points = Column(Float, nullable=False, default=0.0)
    capacity_type = Column(String(50), nullable=False, default="story_points")  # story_points, hours, issues
    
    # Allocation tracking
    allocated_points = Column(Float, nullable=False, default=0.0)
    remaining_points = Column(Float, nullable=False, default=0.0)
    utilization_percentage = Column(Float, nullable=False, default=0.0)
    
    # Configuration metadata
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    auto_calculated = Column(Boolean, default=False, nullable=False)
    
    # Historical tracking
    previous_capacity = Column(Float, nullable=True)
    capacity_history = Column(JSON, nullable=True)  # [{date, capacity, reason}]
    
    # Relationships
    sprint = relationship("Sprint")
    created_by_user = relationship("User")
    
    # Table constraints and indexes
    __table_args__ = (
        # Ensure capacity type is valid
        CheckConstraint("capacity_type IN ('story_points', 'hours', 'issues')", name='valid_capacity_type'),
        # Ensure non-negative capacity values
        CheckConstraint("capacity_points >= 0", name='non_negative_capacity'),
        CheckConstraint("allocated_points >= 0", name='non_negative_allocated'),
        CheckConstraint("remaining_points >= 0", name='non_negative_remaining'),
        CheckConstraint("utilization_percentage >= 0 AND utilization_percentage <= 200", name='valid_utilization_range'),
        # Ensure discipline team name is not empty
        CheckConstraint("trim(discipline_team) != ''", name='team_name_not_empty'),
        # Performance indexes
        Index('idx_capacity_sprint_team', 'sprint_id', 'discipline_team', 'is_active'),
        Index('idx_capacity_utilization', 'utilization_percentage', 'is_active'),
        Index('idx_capacity_type', 'capacity_type', 'is_active'),
    )
    
    @validates('capacity_points', 'allocated_points', 'remaining_points')
    def validate_non_negative_capacity(self, key, value):
        """Validate non-negative capacity values."""
        if value is not None and value < 0:
            raise ValueError(f"{key} cannot be negative")
        return value
    
    @validates('utilization_percentage')
    def validate_utilization(self, key, value):
        """Validate utilization percentage range."""
        if value is not None and (value < 0 or value > 200):
            raise ValueError("Utilization percentage must be between 0 and 200")
        return value
    
    @validates('discipline_team')
    def validate_team_name(self, key, value):
        """Validate team name is not empty."""
        if value and len(value.strip()) == 0:
            raise ValueError("Discipline team name cannot be empty")
        return value.strip() if value else value
    
    def __repr__(self) -> str:
        return f"<DisciplineTeamCapacity(id={self.id}, team='{self.discipline_team}', capacity={self.capacity_points})>"
    
    @property
    def is_over_capacity(self) -> bool:
        """Check if team is over capacity."""
        return self.allocated_points > self.capacity_points
    
    @property
    def available_capacity(self) -> float:
        """Calculate available capacity."""
        return max(0.0, self.capacity_points - self.allocated_points)
    
    def update_allocation(self, allocated_points: float) -> None:
        """Update allocation and recalculate derived fields."""
        self.allocated_points = allocated_points
        self.remaining_points = max(0.0, self.capacity_points - allocated_points)
        
        if self.capacity_points > 0:
            self.utilization_percentage = (allocated_points / self.capacity_points) * 100
        else:
            self.utilization_percentage = 0.0


class TeamCapacityPlan(Base):
    """Long-term capacity planning for discipline teams."""
    
    __tablename__ = "team_capacity_plans"
    
    # Team identification
    discipline_team = Column(String(100), nullable=False, index=True)
    
    # Planning period
    plan_name = Column(String(200), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    
    # Capacity planning
    default_capacity = Column(Float, nullable=False, default=30.0)
    capacity_unit = Column(String(50), nullable=False, default="story_points")
    
    # Team composition
    team_size = Column(Integer, nullable=True)
    team_members = Column(JSON, nullable=True)  # [{"name": str, "capacity": float, "role": str}]
    
    # Adjustments and exceptions
    holiday_adjustments = Column(JSON, nullable=True)  # [{date_range, adjustment_factor}]
    sprint_exceptions = Column(JSON, nullable=True)  # [{sprint_name, custom_capacity, reason}]
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    created_by_user = relationship("User")
    
    # Table constraints and indexes
    __table_args__ = (
        # Ensure capacity unit is valid
        CheckConstraint("capacity_unit IN ('story_points', 'hours', 'issues')", name='valid_plan_capacity_unit'),
        # Ensure non-negative values
        CheckConstraint("default_capacity >= 0", name='non_negative_default_capacity'),
        CheckConstraint("team_size IS NULL OR team_size > 0", name='positive_team_size'),
        # Ensure date logic
        CheckConstraint("start_date <= end_date", name='valid_plan_date_range'),
        # Ensure names are not empty
        CheckConstraint("trim(discipline_team) != ''", name='plan_team_name_not_empty'),
        CheckConstraint("trim(plan_name) != ''", name='plan_name_not_empty'),
        # Performance indexes
        Index('idx_plan_team_dates', 'discipline_team', 'start_date', 'end_date', 'is_active'),
        Index('idx_plan_active', 'is_active', 'end_date'),
    )
    
    @validates('default_capacity')
    def validate_default_capacity(self, key, value):
        """Validate default capacity is non-negative."""
        if value is not None and value < 0:
            raise ValueError("Default capacity cannot be negative")
        return value
    
    @validates('team_size')
    def validate_team_size(self, key, value):
        """Validate team size is positive."""
        if value is not None and value <= 0:
            raise ValueError("Team size must be positive")
        return value
    
    @validates('discipline_team', 'plan_name')
    def validate_not_empty(self, key, value):
        """Validate string fields are not empty."""
        if value and len(value.strip()) == 0:
            raise ValueError(f"{key} cannot be empty")
        return value.strip() if value else value
    
    def __repr__(self) -> str:
        return f"<TeamCapacityPlan(id={self.id}, team='{self.discipline_team}', plan='{self.plan_name}')>"


class ProjectCapacityAllocation(Base):
    """Project-specific capacity allocation tracking for multi-project context."""
    
    __tablename__ = "project_capacity_allocations"
    
    # Foreign keys
    sprint_id = Column(Integer, ForeignKey("sprints.id"), nullable=False, index=True)
    project_workstream_id = Column(Integer, ForeignKey("project_workstreams.id"), nullable=False, index=True)
    discipline_team_capacity_id = Column(Integer, ForeignKey("discipline_team_capacities.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Project identification (denormalized for performance)
    project_key = Column(String(50), nullable=False, index=True)
    discipline_team = Column(String(100), nullable=False, index=True)
    
    # Allocation details
    allocated_capacity = Column(Float, nullable=False, default=0.0)
    capacity_percentage = Column(Float, nullable=False, default=0.0)  # % of total team capacity
    capacity_type = Column(String(50), nullable=False, default="story_points")
    
    # Utilization tracking
    utilized_capacity = Column(Float, nullable=False, default=0.0)
    remaining_capacity = Column(Float, nullable=False, default=0.0)
    utilization_percentage = Column(Float, nullable=False, default=0.0)
    
    # Forecasting data
    forecasted_capacity_need = Column(Float, nullable=True)
    capacity_trend = Column(String(20), nullable=True)  # increasing, decreasing, stable
    
    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    allocation_priority = Column(Integer, nullable=True)  # Priority within sprint
    notes = Column(Text, nullable=True)
    
    # Historical tracking
    allocation_history = Column(JSON, nullable=True)  # [{date, allocation, reason}]
    
    # Relationships
    sprint = relationship("Sprint")
    project_workstream = relationship("ProjectWorkstream")
    discipline_team_capacity = relationship("DisciplineTeamCapacity")
    created_by_user = relationship("User")
    
    # Table constraints and indexes
    __table_args__ = (
        # Unique constraint to prevent duplicate allocations
        Index('idx_unique_sprint_project_team', 'sprint_id', 'project_workstream_id', 'discipline_team_capacity_id', unique=True),
        # Ensure capacity type is valid
        CheckConstraint("capacity_type IN ('story_points', 'hours', 'issues')", name='valid_project_capacity_type'),
        # Ensure non-negative capacity values
        CheckConstraint("allocated_capacity >= 0", name='non_negative_allocated_capacity'),
        CheckConstraint("utilized_capacity >= 0", name='non_negative_utilized_capacity'),
        CheckConstraint("remaining_capacity >= 0", name='non_negative_remaining_capacity'),
        CheckConstraint("capacity_percentage >= 0 AND capacity_percentage <= 100", name='valid_capacity_percentage'),
        CheckConstraint("utilization_percentage >= 0", name='non_negative_utilization_percentage'),
        CheckConstraint("allocation_priority IS NULL OR allocation_priority > 0", name='positive_allocation_priority'),
        # Ensure names are not empty
        CheckConstraint("trim(project_key) != ''", name='project_key_not_empty_allocation'),
        CheckConstraint("trim(discipline_team) != ''", name='team_name_not_empty_allocation'),
        # Ensure valid capacity trend
        CheckConstraint("capacity_trend IS NULL OR capacity_trend IN ('increasing', 'decreasing', 'stable')", name='valid_capacity_trend'),
        # Performance indexes
        Index('idx_allocation_sprint_project', 'sprint_id', 'project_key', 'is_active'),
        Index('idx_allocation_team_utilization', 'discipline_team', 'utilization_percentage', 'is_active'),
        Index('idx_allocation_capacity_type', 'capacity_type', 'is_active'),
        Index('idx_allocation_priority', 'allocation_priority', 'is_active'),
    )
    
    @validates('allocated_capacity', 'utilized_capacity', 'remaining_capacity')
    def validate_non_negative_capacity(self, key, value):
        """Validate non-negative capacity values."""
        if value is not None and value < 0:
            raise ValueError(f"{key} cannot be negative")
        return value
    
    @validates('capacity_percentage')
    def validate_capacity_percentage(self, key, value):
        """Validate capacity percentage range."""
        if value is not None and (value < 0 or value > 100):
            raise ValueError("Capacity percentage must be between 0 and 100")
        return value
    
    @validates('utilization_percentage')
    def validate_utilization_percentage(self, key, value):
        """Validate utilization percentage is non-negative."""
        if value is not None and value < 0:
            raise ValueError("Utilization percentage cannot be negative")
        return value
    
    @validates('allocation_priority')
    def validate_allocation_priority(self, key, value):
        """Validate allocation priority is positive."""
        if value is not None and value <= 0:
            raise ValueError("Allocation priority must be positive")
        return value
    
    @validates('project_key', 'discipline_team')
    def validate_not_empty(self, key, value):
        """Validate string fields are not empty."""
        if value and len(value.strip()) == 0:
            raise ValueError(f"{key} cannot be empty")
        return value.strip() if value else value
    
    @validates('capacity_trend')
    def validate_capacity_trend(self, key, value):
        """Validate capacity trend."""
        if value and value not in ['increasing', 'decreasing', 'stable']:
            raise ValueError("Capacity trend must be one of: increasing, decreasing, stable")
        return value
    
    def __repr__(self) -> str:
        return f"<ProjectCapacityAllocation(id={self.id}, project='{self.project_key}', team='{self.discipline_team}', allocation={self.allocated_capacity})>"
    
    @property
    def is_over_allocated(self) -> bool:
        """Check if project allocation exceeds planned capacity."""
        return self.utilized_capacity > self.allocated_capacity
    
    @property
    def available_capacity(self) -> float:
        """Calculate available capacity for this project allocation."""
        return max(0.0, self.allocated_capacity - self.utilized_capacity)
    
    @property
    def efficiency_ratio(self) -> float:
        """Calculate capacity efficiency ratio (utilized/allocated)."""
        if self.allocated_capacity > 0:
            return self.utilized_capacity / self.allocated_capacity
        return 0.0
    
    def update_utilization(self, utilized_capacity: float) -> None:
        """Update utilization and recalculate derived fields."""
        self.utilized_capacity = utilized_capacity
        self.remaining_capacity = max(0.0, self.allocated_capacity - utilized_capacity)
        
        if self.allocated_capacity > 0:
            self.utilization_percentage = (utilized_capacity / self.allocated_capacity) * 100
        else:
            self.utilization_percentage = 0.0