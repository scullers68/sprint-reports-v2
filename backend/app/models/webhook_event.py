"""
JIRA webhook event model for real-time event processing.

Stores and processes JIRA webhook events according to architectural specification.
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, JSON

from app.models.base import Base


class WebhookEvent(Base):
    """Store and process JIRA webhook events."""
    __tablename__ = "webhook_events"
    
    # Event identification
    event_id = Column(String(100), unique=True, nullable=False, index=True)  # Webhook event ID
    event_type = Column(String(100), nullable=False, index=True)  # jira:issue_updated, etc.
    
    # Event data
    payload = Column(JSON, nullable=False)  # Full webhook payload
    processed_data = Column(JSON, nullable=True)  # Extracted and processed data
    processed_at = Column(DateTime(timezone=True))
    processing_status = Column(String(20), default='pending', nullable=False, index=True)  # pending, processing, completed, failed
    
    # Processing metadata
    retry_count = Column(Integer, default=0, nullable=False)
    processing_attempts = Column(Integer, default=0, nullable=False)
    last_processed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    processing_duration_ms = Column(Integer)

    def __repr__(self) -> str:
        return f"<WebhookEvent(id={self.id}, event_id='{self.event_id}', type='{self.event_type}', status='{self.processing_status}')>"