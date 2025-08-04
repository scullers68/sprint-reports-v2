"""
Cached Sprint model for storing JIRA sprint data locally.

This model stores sprint information fetched from JIRA for fast lookups
and to reduce API calls to JIRA during discovery operations.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base

from app.core.database import Base


class CachedSprint(Base):
    """
    Cached JIRA sprint information for fast lookups and discovery.
    
    This table stores sprint data fetched from JIRA to enable fast search
    and discovery without making real-time API calls to JIRA.
    """
    __tablename__ = "cached_sprints"

    id = Column(Integer, primary_key=True, index=True)
    
    # JIRA Sprint Information
    jira_sprint_id = Column(Integer, unique=True, nullable=False, index=True, comment="JIRA sprint ID")
    name = Column(String(255), nullable=False, index=True, comment="Sprint name")
    state = Column(String(50), nullable=False, index=True, comment="Sprint state (active, future, closed)")
    goal = Column(Text, nullable=True, comment="Sprint goal description")
    
    # Sprint Dates
    start_date = Column(DateTime(timezone=True), nullable=True, comment="Sprint start date")
    end_date = Column(DateTime(timezone=True), nullable=True, comment="Sprint end date")
    complete_date = Column(DateTime(timezone=True), nullable=True, comment="Sprint completion date")
    
    # Board and Project Information
    board_id = Column(Integer, nullable=False, index=True, comment="JIRA board ID")
    board_name = Column(String(255), nullable=False, comment="Board name")
    board_type = Column(String(50), nullable=False, comment="Board type (scrum, kanban)")
    project_key = Column(String(50), nullable=True, index=True, comment="Project key")
    project_name = Column(String(255), nullable=True, comment="Project name")
    
    # Additional Metadata
    origin_board_id = Column(Integer, nullable=True, comment="Origin board ID from JIRA")
    jira_self_url = Column(String(500), nullable=True, comment="JIRA self URL")
    raw_data = Column(JSON, nullable=True, comment="Raw sprint data from JIRA API")
    
    # Discovery and Search
    is_active = Column(Boolean, default=True, nullable=False, index=True, comment="Is sprint active for discovery")
    is_discoverable = Column(Boolean, default=True, nullable=False, index=True, comment="Should appear in discovery results")
    discovery_source = Column(String(100), default="api_sync", nullable=False, comment="How this sprint was discovered")
    search_keywords = Column(Text, nullable=True, comment="Additional search keywords")
    
    # Cache Management
    last_fetched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, comment="When this was last fetched from JIRA")
    last_updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False, comment="Last update timestamp")
    fetch_error_count = Column(Integer, default=0, nullable=False, comment="Number of consecutive fetch errors")
    last_fetch_error = Column(Text, nullable=True, comment="Last fetch error message")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<CachedSprint(id={self.id}, jira_id={self.jira_sprint_id}, name='{self.name}', state='{self.state}')>"

    @property
    def is_current(self) -> bool:
        """Check if sprint is currently active or upcoming."""
        return self.state.lower() in ['active', 'future']

    @property
    def is_stale(self, max_age_hours: int = 2) -> bool:
        """Check if cached data is stale and needs refresh."""
        if not self.last_fetched_at:
            return True
        
        now = datetime.now(timezone.utc)
        age = now - self.last_fetched_at
        return age.total_seconds() > (max_age_hours * 3600)

    def update_from_jira_data(self, jira_data: dict) -> None:
        """Update sprint information from JIRA API response data."""
        self.name = jira_data.get('name', self.name)
        self.state = jira_data.get('state', self.state)
        self.goal = jira_data.get('goal', self.goal)
        
        # Parse dates
        if jira_data.get('startDate'):
            try:
                self.start_date = datetime.fromisoformat(jira_data['startDate'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
                
        if jira_data.get('endDate'):
            try:
                self.end_date = datetime.fromisoformat(jira_data['endDate'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
                
        if jira_data.get('completeDate'):
            try:
                self.complete_date = datetime.fromisoformat(jira_data['completeDate'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        
        # Update metadata
        self.origin_board_id = jira_data.get('originBoardId', self.origin_board_id)
        self.jira_self_url = jira_data.get('self', self.jira_self_url)
        self.raw_data = jira_data
        self.last_fetched_at = datetime.now(timezone.utc)
        self.fetch_error_count = 0  # Reset error count on successful update
        self.last_fetch_error = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            'id': self.jira_sprint_id,  # Use JIRA ID for external consumers
            'name': self.name,
            'state': self.state,
            'goal': self.goal,
            'startDate': self.start_date.isoformat() if self.start_date else None,
            'endDate': self.end_date.isoformat() if self.end_date else None,
            'completeDate': self.complete_date.isoformat() if self.complete_date else None,
            'originBoardId': self.origin_board_id,
            'self': self.jira_self_url,
            'board': {
                'id': self.board_id,
                'name': self.board_name,
                'type': self.board_type,
                'projectKey': self.project_key
            },
            'cached': True,
            'lastFetched': self.last_fetched_at.isoformat() if self.last_fetched_at else None
        }