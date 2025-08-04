"""
Cached Sprint model for storing JIRA sprint data locally.

This model stores sprint information fetched from JIRA for fast lookups
and to reduce API calls to JIRA during discovery operations.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any

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

    # ========== PROJECT METRICS CALCULATION METHODS ==========

    def calculate_project_velocity(self, completed_story_points: float, sprint_duration_days: int) -> Optional[float]:
        """
        Calculate project velocity based on completed story points and sprint duration.
        
        Args:
            completed_story_points: Total story points completed
            sprint_duration_days: Duration of the sprint in days
            
        Returns:
            Velocity as story points per day, or None if calculation not possible
        """
        if sprint_duration_days <= 0 or completed_story_points < 0:
            return None
        
        return completed_story_points / sprint_duration_days

    def calculate_burndown_rate(
        self, 
        completed_story_points: float, 
        total_story_points: float, 
        days_elapsed: int
    ) -> Optional[float]:
        """
        Calculate burndown rate for project progress tracking.
        
        Args:
            completed_story_points: Story points completed so far
            total_story_points: Total story points in sprint
            days_elapsed: Number of days elapsed in sprint
            
        Returns:
            Burndown rate as percentage per day, or None if calculation not possible
        """
        if days_elapsed <= 0 or total_story_points <= 0:
            return None
        
        completion_percentage = (completed_story_points / total_story_points) * 100
        return completion_percentage / days_elapsed

    def calculate_completion_forecast(
        self, 
        completed_story_points: float,
        total_story_points: float,
        current_velocity: Optional[float]
    ) -> Dict[str, Any]:
        """
        Calculate completion forecast based on current progress and velocity.
        
        Args:
            completed_story_points: Story points completed
            total_story_points: Total story points in sprint
            current_velocity: Current velocity (points per day)
            
        Returns:
            Dictionary with forecast data including estimated completion date
        """
        remaining_points = max(0.0, total_story_points - completed_story_points)
        completion_percentage = (completed_story_points / total_story_points * 100) if total_story_points > 0 else 0.0
        
        forecast = {
            'remaining_story_points': remaining_points,
            'completion_percentage': completion_percentage,
            'estimated_completion_date': None,
            'days_remaining': None,
            'confidence_level': 0.0,
            'is_on_track': completion_percentage >= 50.0  # Basic threshold
        }
        
        if current_velocity and current_velocity > 0 and remaining_points > 0:
            days_remaining = remaining_points / current_velocity
            forecast['days_remaining'] = days_remaining
            
            if self.start_date:
                from datetime import timedelta
                estimated_completion = self.start_date + timedelta(days=days_remaining)
                forecast['estimated_completion_date'] = estimated_completion.isoformat()
                
                # Calculate confidence based on various factors
                confidence = 0.8  # Base confidence
                
                # Reduce confidence if behind schedule
                if completion_percentage < 50.0:
                    confidence *= 0.7
                
                # Reduce confidence if sprint is ending soon
                if self.end_date:
                    now = datetime.now(timezone.utc)
                    days_until_end = (self.end_date - now).days
                    if days_remaining > days_until_end:
                        confidence *= 0.5
                
                forecast['confidence_level'] = confidence * 100
        
        return forecast

    def calculate_risk_indicators(
        self,
        blocked_issues: int,
        total_issues: int,
        completion_percentage: float,
        velocity_trend: str = "stable"
    ) -> Dict[str, Any]:
        """
        Calculate risk indicators for project health assessment.
        
        Args:
            blocked_issues: Number of blocked issues
            total_issues: Total number of issues
            completion_percentage: Current completion percentage
            velocity_trend: Velocity trend (improving, stable, declining)
            
        Returns:
            Dictionary with risk assessment data
        """
        risk_score = 0.0
        risk_factors = []
        risk_level = "low"
        
        # Blocked issues risk
        if blocked_issues > 0 and total_issues > 0:
            blocked_percentage = (blocked_issues / total_issues) * 100
            if blocked_percentage > 20:
                risk_score += 40.0
                risk_factors.append(f"High percentage of blocked issues ({blocked_percentage:.1f}%)")
            elif blocked_percentage > 10:
                risk_score += 20.0
                risk_factors.append(f"Moderate blocked issues ({blocked_percentage:.1f}%)")
        
        # Completion progress risk
        if completion_percentage < 25.0:
            risk_score += 30.0
            risk_factors.append("Low completion progress")
        elif completion_percentage < 50.0:
            risk_score += 15.0
            risk_factors.append("Below-average completion progress")
        
        # Velocity trend risk
        if velocity_trend == "declining":
            risk_score += 25.0
            risk_factors.append("Declining velocity trend")
        elif velocity_trend == "stable" and completion_percentage < 50.0:
            risk_score += 10.0
            risk_factors.append("Stable velocity but behind schedule")
        
        # Sprint timeline risk
        if self.end_date and self.start_date:
            now = datetime.now(timezone.utc)
            total_days = (self.end_date - self.start_date).days
            elapsed_days = (now - self.start_date).days
            
            if total_days > 0:
                time_progress = (elapsed_days / total_days) * 100
                if time_progress > completion_percentage + 20:  # More than 20% behind time
                    risk_score += 20.0
                    risk_factors.append("Behind schedule relative to time elapsed")
        
        # Determine risk level
        if risk_score >= 70:
            risk_level = "critical"
        elif risk_score >= 40:
            risk_level = "high"
        elif risk_score >= 20:
            risk_level = "medium"
        
        return {
            'risk_score': min(100.0, risk_score),
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'total_risk_factors': len(risk_factors)
        }

    def calculate_capacity_metrics(
        self,
        team_size: int,
        allocated_story_points: float,
        completed_story_points: float,
        sprint_duration_days: int
    ) -> Dict[str, Any]:
        """
        Calculate capacity utilization metrics for resource planning.
        
        Args:
            team_size: Number of team members
            allocated_story_points: Originally allocated story points
            completed_story_points: Actually completed story points
            sprint_duration_days: Sprint duration in days
            
        Returns:
            Dictionary with capacity metrics
        """
        metrics = {
            'team_size': team_size,
            'allocated_capacity': allocated_story_points,
            'utilized_capacity': completed_story_points,
            'capacity_utilization_percentage': 0.0,
            'points_per_person': 0.0,
            'daily_throughput': 0.0,
            'capacity_status': 'normal'
        }
        
        # Calculate utilization percentage
        if allocated_story_points > 0:
            utilization = (completed_story_points / allocated_story_points) * 100
            metrics['capacity_utilization_percentage'] = utilization
            
            # Determine capacity status
            if utilization > 110:
                metrics['capacity_status'] = 'over_capacity'
            elif utilization < 70:
                metrics['capacity_status'] = 'under_utilized'
        
        # Calculate points per person
        if team_size > 0:
            metrics['points_per_person'] = completed_story_points / team_size
        
        # Calculate daily throughput
        if sprint_duration_days > 0:
            metrics['daily_throughput'] = completed_story_points / sprint_duration_days
        
        return metrics

    def get_sprint_health_summary(
        self,
        project_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate overall sprint health summary based on project metrics.
        
        Args:
            project_metrics: Dictionary containing various project metrics
            
        Returns:
            Comprehensive health summary
        """
        health_summary = {
            'sprint_id': self.jira_sprint_id,
            'sprint_name': self.name,
            'sprint_state': self.state,
            'overall_health': 'healthy',
            'health_score': 100.0,
            'key_metrics': {},
            'recommendations': []
        }
        
        # Extract metrics
        completion_percentage = project_metrics.get('completion_percentage', 0.0)
        risk_score = project_metrics.get('risk_score', 0.0)
        velocity = project_metrics.get('velocity', 0.0)
        blocked_issues = project_metrics.get('blocked_issues', 0)
        
        # Calculate health score
        health_score = 100.0
        
        # Deduct points for low completion
        if completion_percentage < 25:
            health_score -= 30
        elif completion_percentage < 50:
            health_score -= 15
        
        # Deduct points for high risk
        health_score -= (risk_score * 0.5)  # Risk score contributes up to 50 points
        
        # Deduct points for blocked issues
        if blocked_issues > 0:
            health_score -= min(20, blocked_issues * 5)
        
        health_score = max(0.0, health_score)
        health_summary['health_score'] = health_score
        
        # Determine overall health status
        if health_score >= 80:
            health_summary['overall_health'] = 'healthy'
        elif health_score >= 60:
            health_summary['overall_health'] = 'at_risk'
        else:
            health_summary['overall_health'] = 'critical'
        
        # Add key metrics
        health_summary['key_metrics'] = {
            'completion_percentage': completion_percentage,
            'risk_score': risk_score,
            'velocity': velocity,
            'blocked_issues': blocked_issues
        }
        
        # Generate recommendations
        recommendations = []
        if completion_percentage < 50:
            recommendations.append("Focus on completing high-priority items")
        if blocked_issues > 0:
            recommendations.append("Address blocked issues immediately")
        if risk_score > 50:
            recommendations.append("Implement risk mitigation strategies")
        if velocity < 1.0:
            recommendations.append("Review team capacity and workload")
        
        health_summary['recommendations'] = recommendations
        
        return health_summary