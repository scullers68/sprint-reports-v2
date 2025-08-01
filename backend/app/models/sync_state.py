"""
Sync State model for tracking synchronization state and conflicts.

Implements the architectural specification for sync state management.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, Integer, JSON, Index, CheckConstraint, Text
from sqlalchemy.orm import validates

from app.models.base import Base


class SyncState(Base):
    """Track synchronization state and conflicts."""
    
    __tablename__ = "sync_metadata"
    
    # Entity identification (mapped to sync_metadata schema)
    entity_type = Column(String(50), nullable=False, index=True)  # sprint, issue, project, board
    entity_id = Column(String(100), nullable=False, index=True)  # Internal ID
    jira_id = Column(String(100), nullable=True, index=True)  # JIRA ID
    
    # Sync status and timing
    sync_status = Column(String(20), nullable=False, index=True)  # pending, in_progress, completed, failed, skipped  
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
    
    # Architectural specification additions
    conflicts = Column(JSON, nullable=True)  # Store conflict details
    resolution_strategy = Column(String(50), nullable=True)  # auto, manual, jira_wins, local_wins
    
    # Performance tracking
    sync_duration_ms = Column(Integer, nullable=True)
    api_calls_count = Column(Integer, default=0, nullable=False)
    
    # Table constraints and indexes (aligned with sync_metadata table)
    __table_args__ = (
        # Ensure valid entity types
        CheckConstraint("entity_type IN ('sprint', 'issue', 'project', 'board')", name='valid_entity_type'),
        # Ensure valid sync status
        CheckConstraint("sync_status IN ('pending', 'in_progress', 'completed', 'failed', 'skipped')", name='valid_sync_status'),  
        # Ensure valid sync directions
        CheckConstraint("sync_direction IN ('local_to_remote', 'remote_to_local', 'bidirectional')", name='valid_sync_direction'),
        # Ensure valid resolution strategies
        CheckConstraint("resolution_strategy IS NULL OR resolution_strategy IN ('auto', 'manual', 'jira_wins', 'local_wins')", name='valid_resolution_strategy'),
        # Ensure non-negative values
        CheckConstraint("sync_duration_ms IS NULL OR sync_duration_ms >= 0", name='non_negative_duration'),
        CheckConstraint("api_calls_count >= 0", name='non_negative_api_calls'),
        CheckConstraint("error_count >= 0", name='non_negative_error_count'),
        # Unique constraint for entity tracking
        Index('idx_unique_entity', 'entity_type', 'entity_id', unique=True),
        # Performance indexes
        Index('idx_sync_status_type', 'sync_status', 'entity_type'),
        Index('idx_sync_batch', 'sync_batch_id'),
        Index('idx_sync_timestamps', 'last_sync_attempt', 'sync_status'),
        Index('idx_sync_performance', 'sync_duration_ms', 'api_calls_count'),
        # Allow extending existing table definition
        {'extend_existing': True}
    )
    
    @validates('entity_type')
    def validate_entity_type(self, key, entity_type):
        """Validate entity type."""
        valid_types = ['sprint', 'issue', 'project', 'board']
        if entity_type and entity_type not in valid_types:
            raise ValueError(f"Invalid entity type. Must be one of: {valid_types}")
        return entity_type
    
    @validates('sync_status')
    def validate_sync_status(self, key, sync_status):
        """Validate sync status."""
        valid_statuses = ['pending', 'in_progress', 'completed', 'failed', 'skipped']
        if sync_status and sync_status not in valid_statuses:
            raise ValueError(f"Invalid sync status. Must be one of: {valid_statuses}")
        return sync_status
    
    @validates('sync_direction')
    def validate_sync_direction(self, key, sync_direction):
        """Validate sync direction."""
        if sync_direction is None:
            return sync_direction
        valid_directions = ['local_to_remote', 'remote_to_local', 'bidirectional']
        if sync_direction not in valid_directions:
            raise ValueError(f"Invalid sync direction. Must be one of: {valid_directions}")
        return sync_direction
    
    @validates('resolution_strategy')
    def validate_resolution_strategy(self, key, resolution_strategy):
        """Validate resolution strategy."""
        if resolution_strategy is None:
            return resolution_strategy
        valid_strategies = ['auto', 'manual', 'jira_wins', 'local_wins']
        if resolution_strategy not in valid_strategies:
            raise ValueError(f"Invalid resolution strategy. Must be one of: {valid_strategies}")
        return resolution_strategy
    
    @validates('sync_duration_ms', 'api_calls_count', 'error_count')
    def validate_non_negative(self, key, value):
        """Validate non-negative numeric values."""
        if value is not None and value < 0:
            raise ValueError(f"{key} cannot be negative")
        return value
    
    def __repr__(self) -> str:
        return f"<SyncState(id={self.id}, entity={self.entity_type}:{self.entity_id}, status={self.sync_status})>"