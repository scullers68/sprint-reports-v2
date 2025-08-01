"""
Queue models for sprint queue management and distribution.

Handles sprint queues, queue items, and distribution algorithms.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, Integer, Float, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.models.base import Base


class SprintQueue(Base):
    """Sprint queue with discipline team capacity management."""
    
    __tablename__ = "sprint_queues"
    
    # Foreign keys
    sprint_id = Column(Integer, ForeignKey("sprints.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Queue metadata
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="draft")  # draft, active, completed, archived
    
    # Generation settings
    algorithm = Column(String(100), nullable=False, default="fair_distribution")
    use_discipline_capacity = Column(Boolean, default=True, nullable=False)
    exclude_subtasks = Column(Boolean, default=True, nullable=False)
    
    # Queue metrics
    total_items = Column(Integer, nullable=False, default=0)
    total_story_points = Column(Float, nullable=False, default=0.0)
    discipline_teams_count = Column(Integer, nullable=False, default=0)
    
    # Distribution results (JSON)
    distribution_summary = Column(JSON, nullable=True)  # {team_name: {items: n, points: n, capacity: n}}
    generation_log = Column(JSON, nullable=True)  # Algorithm execution log
    
    # Timestamps
    generated_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    sprint = relationship("Sprint", back_populates="queues")
    created_by_user = relationship("User")
    items = relationship("QueueItem", back_populates="queue", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<SprintQueue(id={self.id}, name='{self.name}', status='{self.status}')>"


class QueueItem(Base):
    """Individual items in a sprint queue."""
    
    __tablename__ = "queue_items"
    
    # Foreign keys
    queue_id = Column(Integer, ForeignKey("sprint_queues.id"), nullable=False, index=True)
    
    # JIRA issue info
    jira_issue_key = Column(String(50), nullable=False, index=True)
    jira_issue_id = Column(Integer, nullable=False)
    
    # Issue details
    summary = Column(Text, nullable=False)
    issue_type = Column(String(100), nullable=False)
    priority = Column(String(50), nullable=True)
    status = Column(String(100), nullable=False)
    
    # Assignment and capacity
    discipline_team = Column(String(100), nullable=True, index=True)
    assignee_account_id = Column(String(128), nullable=True)
    assignee_display_name = Column(String(255), nullable=True)
    
    # Effort and ranking
    story_points = Column(Float, nullable=True)
    original_rank = Column(Integer, nullable=True)
    queue_rank = Column(Integer, nullable=False)
    
    # Additional metadata (JSON)
    labels = Column(JSON, nullable=True)  # JIRA labels array
    components = Column(JSON, nullable=True)  # JIRA components array
    custom_fields = Column(JSON, nullable=True)  # Relevant custom field values
    
    # Relationships
    queue = relationship("SprintQueue", back_populates="items")
    
    def __repr__(self) -> str:
        return f"<QueueItem(id={self.id}, key='{self.jira_issue_key}', rank={self.queue_rank})>"


