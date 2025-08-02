"""
Sprint models for sprint management and analysis.

Handles sprint metadata, analysis, and historical tracking.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, Integer, Float, Text, Boolean, ForeignKey, JSON, Index, CheckConstraint, Enum
from sqlalchemy.orm import relationship, validates
import enum

from app.models.base import Base


class SyncStatus(enum.Enum):
    """Enumeration for synchronization status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ConflictResolutionStrategy(enum.Enum):
    """Enumeration for conflict resolution strategies."""
    LOCAL_WINS = "local_wins"
    REMOTE_WINS = "remote_wins"
    MERGE = "merge"
    MANUAL = "manual"


class Sprint(Base):
    """Sprint model for JIRA sprint tracking."""
    
    __tablename__ = "sprints"
    
    # JIRA sprint info
    jira_sprint_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False, index=True)
    state = Column(String(50), nullable=False)  # future, active, closed
    
    # Sprint dates
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    complete_date = Column(DateTime(timezone=True), nullable=True)
    
    # Sprint metadata
    goal = Column(Text, nullable=True)
    board_id = Column(Integer, nullable=True)
    origin_board_id = Column(Integer, nullable=True)
    
    # JIRA sync metadata
    jira_last_updated = Column(DateTime(timezone=True))
    sync_status = Column(String(20), default='pending')
    sync_conflicts = Column(JSON)  # Track any sync conflicts
    
    # Enhanced JIRA metadata
    jira_board_name = Column(String(200))
    jira_project_key = Column(String(50), index=True)
    jira_version = Column(String(20))  # JIRA version for compatibility
    
    # Relationships - temporarily disabled for MVP authentication testing
    # analyses = relationship("SprintAnalysis", back_populates="sprint", cascade="all, delete-orphan")
    # queues = relationship("SprintQueue", back_populates="sprint", cascade="all, delete-orphan")
    # reports = relationship("Report", back_populates="sprint", cascade="all, delete-orphan")
    
    # Table constraints and indexes
    __table_args__ = (
        # Ensure state is valid
        CheckConstraint("state IN ('future', 'active', 'closed')", name='valid_sprint_state'),
        # Ensure name is not empty
        CheckConstraint("trim(name) != ''", name='sprint_name_not_empty'),
        # Ensure date logic
        CheckConstraint("start_date IS NULL OR end_date IS NULL OR start_date <= end_date", name='valid_date_range'),
        CheckConstraint("complete_date IS NULL OR start_date IS NULL OR complete_date >= start_date", name='complete_after_start'),
        # Ensure valid sync status
        CheckConstraint("sync_status IN ('pending', 'in_progress', 'completed', 'failed', 'skipped')", name='valid_sync_status'),
        # Performance indexes
        Index('idx_sprint_jira_state', 'jira_sprint_id', 'state'),
        Index('idx_sprint_dates', 'start_date', 'end_date'),
        Index('idx_sprint_board', 'board_id', 'state'),
        Index('idx_sprint_sync_status', 'sync_status', 'jira_last_updated'),
        Index('idx_sprint_project_key', 'jira_project_key'),
    )
    
    @validates('state')
    def validate_state(self, key, state):
        """Validate sprint state."""
        valid_states = ['future', 'active', 'closed']
        if state and state not in valid_states:
            raise ValueError(f"Invalid sprint state. Must be one of: {valid_states}")
        return state
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate sprint name."""
        if name and len(name.strip()) == 0:
            raise ValueError("Sprint name cannot be empty")
        return name
    
    @validates('sync_status')
    def validate_sync_status(self, key, sync_status):
        """Validate sync status."""
        valid_statuses = ['pending', 'in_progress', 'completed', 'failed', 'skipped']
        if sync_status and sync_status not in valid_statuses:
            raise ValueError(f"Invalid sync status. Must be one of: {valid_statuses}")
        return sync_status
    
    def __repr__(self) -> str:
        return f"<Sprint(id={self.id}, name='{self.name}', state='{self.state}')>"


class SprintAnalysis(Base):
    """Sprint analysis results with discipline team breakdown."""
    
    __tablename__ = "sprint_analyses"
    
    # Foreign keys
    sprint_id = Column(Integer, ForeignKey("sprints.id"), nullable=False, index=True)
    
    # Analysis metadata
    analysis_type = Column(String(50), nullable=False, default="discipline_team")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Analysis results
    total_issues = Column(Integer, nullable=False, default=0)
    total_story_points = Column(Float, nullable=False, default=0.0)
    discipline_teams_count = Column(Integer, nullable=False, default=0)
    
    # Detailed breakdown (JSON)
    discipline_breakdown = Column(JSON, nullable=True)  # {team_name: {issues: n, story_points: n}}
    issue_details = Column(JSON, nullable=True)  # Full issue data for reference
    
    # Analysis settings
    jql_filter = Column(Text, nullable=True)
    exclude_subtasks = Column(Boolean, default=True, nullable=False)
    
    # Relationships - temporarily disabled for MVP authentication testing
    # sprint = relationship("Sprint", back_populates="analyses")
    created_by_user = relationship("User")
    
    # Table constraints and indexes
    __table_args__ = (
        # Ensure analysis type is valid
        CheckConstraint("analysis_type IN ('discipline_team', 'capacity', 'velocity', 'burndown')", name='valid_analysis_type'),
        # Ensure non-negative values
        CheckConstraint("total_issues >= 0", name='non_negative_issues'),
        CheckConstraint("total_story_points >= 0", name='non_negative_story_points'),
        CheckConstraint("discipline_teams_count >= 0", name='non_negative_teams'),
        # Performance indexes
        Index('idx_analysis_sprint_type', 'sprint_id', 'analysis_type'),
        Index('idx_analysis_created', 'created_at', 'analysis_type'),
    )
    
    @validates('total_issues', 'total_story_points', 'discipline_teams_count')
    def validate_non_negative(self, key, value):
        """Validate non-negative numeric values."""
        if value is not None and value < 0:
            raise ValueError(f"{key} cannot be negative")
        return value
    
    def __repr__(self) -> str:
        return f"<SprintAnalysis(id={self.id}, sprint_id={self.sprint_id}, teams={self.discipline_teams_count})>"


class SyncMetadata(Base):
    """Synchronization metadata for tracking sync operations."""
    
    __tablename__ = "sync_metadata"
    
    # Entity information
    entity_type = Column(String(50), nullable=False, index=True)  # sprint, issue, project
    entity_id = Column(String(100), nullable=False, index=True)  # local ID or JIRA ID
    jira_id = Column(String(100), nullable=True, index=True)  # JIRA entity ID
    
    # Sync status
    sync_status = Column(Enum(SyncStatus), nullable=False, default=SyncStatus.PENDING, index=True)
    last_sync_attempt = Column(DateTime(timezone=True), nullable=True)
    last_successful_sync = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps for incremental sync
    local_modified = Column(DateTime(timezone=True), nullable=True)
    remote_modified = Column(DateTime(timezone=True), nullable=True)
    
    # Error tracking
    error_count = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    
    # Sync metadata
    sync_direction = Column(String(20), nullable=False, default="bidirectional")  # local_to_remote, remote_to_local, bidirectional
    sync_batch_id = Column(String(100), nullable=True, index=True)  # Group related sync operations
    
    # Hash for change detection
    content_hash = Column(String(64), nullable=True)  # SHA-256 hash of entity content
    
    # Table constraints and indexes
    __table_args__ = (
        # Ensure valid entity types
        CheckConstraint("entity_type IN ('sprint', 'issue', 'project', 'board')", name='valid_entity_type'),
        # Ensure valid sync directions
        CheckConstraint("sync_direction IN ('local_to_remote', 'remote_to_local', 'bidirectional')", name='valid_sync_direction'),
        # Ensure non-negative error count
        CheckConstraint("error_count >= 0", name='non_negative_error_count'),
        # Unique constraint for entity tracking
        Index('idx_unique_entity', 'entity_type', 'entity_id', unique=True),
        # Performance indexes
        Index('idx_sync_status_type', 'sync_status', 'entity_type'),
        Index('idx_sync_batch', 'sync_batch_id'),
        Index('idx_sync_timestamps', 'last_sync_attempt', 'sync_status'),
    )
    
    @validates('entity_type')
    def validate_entity_type(self, key, entity_type):
        """Validate entity type."""
        valid_types = ['sprint', 'issue', 'project', 'board']
        if entity_type and entity_type not in valid_types:
            raise ValueError(f"Invalid entity type. Must be one of: {valid_types}")
        return entity_type
    
    @validates('sync_direction')
    def validate_sync_direction(self, key, sync_direction):
        """Validate sync direction."""
        valid_directions = ['local_to_remote', 'remote_to_local', 'bidirectional']
        if sync_direction and sync_direction not in valid_directions:
            raise ValueError(f"Invalid sync direction. Must be one of: {valid_directions}")
        return sync_direction
    
    def __repr__(self) -> str:
        return f"<SyncMetadata(id={self.id}, entity={self.entity_type}:{self.entity_id}, status={self.sync_status.value})>"


class ConflictResolution(Base):
    """Model for tracking and resolving synchronization conflicts."""
    
    __tablename__ = "conflict_resolutions"
    
    # Reference to sync metadata
    sync_metadata_id = Column(Integer, ForeignKey("sync_metadata.id"), nullable=False, index=True)
    
    # Conflict information
    conflict_type = Column(String(50), nullable=False)  # field_conflict, deletion_conflict, creation_conflict
    field_name = Column(String(100), nullable=True)  # Specific field that has conflict
    
    # Conflict values
    local_value = Column(JSON, nullable=True)  # Local value
    remote_value = Column(JSON, nullable=True)  # Remote value
    
    # Resolution
    resolution_strategy = Column(Enum(ConflictResolutionStrategy), nullable=False, default=ConflictResolutionStrategy.MANUAL)
    resolved_value = Column(JSON, nullable=True)  # Final resolved value
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who resolved conflict
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Relationships
    sync_metadata = relationship("SyncMetadata")
    resolved_by_user = relationship("User")
    
    # Table constraints and indexes
    __table_args__ = (
        # Ensure valid conflict types
        CheckConstraint("conflict_type IN ('field_conflict', 'deletion_conflict', 'creation_conflict')", name='valid_conflict_type'),
        # Performance indexes
        Index('idx_conflict_status', 'is_resolved', 'conflict_type'),
        Index('idx_conflict_sync', 'sync_metadata_id', 'is_resolved'),
        Index('idx_conflict_resolution', 'resolved_at', 'resolution_strategy'),
    )
    
    @validates('conflict_type')
    def validate_conflict_type(self, key, conflict_type):
        """Validate conflict type."""
        valid_types = ['field_conflict', 'deletion_conflict', 'creation_conflict']
        if conflict_type and conflict_type not in valid_types:
            raise ValueError(f"Invalid conflict type. Must be one of: {valid_types}")
        return conflict_type
    
    def __repr__(self) -> str:
        return f"<ConflictResolution(id={self.id}, type={self.conflict_type}, resolved={self.is_resolved})>"


class SyncHistory(Base):
    """Historical record of synchronization operations."""
    
    __tablename__ = "sync_history"
    
    # Operation details
    operation_type = Column(String(50), nullable=False, index=True)  # full_sync, incremental_sync, conflict_resolution
    entity_type = Column(String(50), nullable=False, index=True)
    batch_id = Column(String(100), nullable=True, index=True)
    
    # Results
    entities_processed = Column(Integer, default=0, nullable=False)
    entities_created = Column(Integer, default=0, nullable=False)
    entities_updated = Column(Integer, default=0, nullable=False)
    entities_deleted = Column(Integer, default=0, nullable=False)
    entities_skipped = Column(Integer, default=0, nullable=False)
    conflicts_detected = Column(Integer, default=0, nullable=False)
    conflicts_resolved = Column(Integer, default=0, nullable=False)
    
    # Performance metrics
    duration_seconds = Column(Float, nullable=True)
    api_calls_made = Column(Integer, default=0, nullable=False)
    
    # Status
    status = Column(Enum(SyncStatus), nullable=False, default=SyncStatus.COMPLETED, index=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    sync_details = Column(JSON, nullable=True)  # Additional sync operation details
    initiated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    initiated_by_user = relationship("User")
    
    # Table constraints and indexes
    __table_args__ = (
        # Ensure valid operation types
        CheckConstraint("operation_type IN ('full_sync', 'incremental_sync', 'conflict_resolution', 'webhook_sync')", name='valid_operation_type'),
        # Ensure non-negative counts
        CheckConstraint("entities_processed >= 0", name='non_negative_processed'),
        CheckConstraint("entities_created >= 0", name='non_negative_created'),
        CheckConstraint("entities_updated >= 0", name='non_negative_updated'),
        CheckConstraint("entities_deleted >= 0", name='non_negative_deleted'),
        CheckConstraint("entities_skipped >= 0", name='non_negative_skipped'),
        CheckConstraint("conflicts_detected >= 0", name='non_negative_conflicts'),
        CheckConstraint("api_calls_made >= 0", name='non_negative_api_calls'),
        # Performance indexes
        Index('idx_sync_history_type_status', 'operation_type', 'status'),
        Index('idx_sync_history_batch', 'batch_id'),
        Index('idx_sync_history_created', 'created_at', 'status'),
    )
    
    @validates('operation_type')
    def validate_operation_type(self, key, operation_type):
        """Validate operation type."""
        valid_types = ['full_sync', 'incremental_sync', 'conflict_resolution', 'webhook_sync']
        if operation_type and operation_type not in valid_types:
            raise ValueError(f"Invalid operation type. Must be one of: {valid_types}")
        return operation_type
    
    def __repr__(self) -> str:
        return f"<SyncHistory(id={self.id}, operation={self.operation_type}, status={self.status.value})>"