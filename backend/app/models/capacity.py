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