"""
Security audit models for tracking security events and audit trails.

Extends existing Base model patterns for security event logging,
tamper detection, and compliance reporting.
"""

import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import (
    Boolean, Column, String, Text, Integer, JSON, 
    ForeignKey, Index, CheckConstraint, DateTime
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from app.models.base import Base


class SecurityEvent(Base):
    """
    Security event audit log extending Base model patterns.
    
    Tracks all security-related events including authentication,
    authorization, data access, and security violations.
    """
    
    __tablename__ = "security_events"
    __allow_unmapped__ = True
    
    # User context (optional - for system events)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user_email = Column(String(255), nullable=True)  # Denormalized for audit trail
    user_ip = Column(String(45), nullable=True)  # IPv4/IPv6 support
    
    # Event classification
    event_type = Column(String(50), nullable=False, index=True)
    event_category = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="INFO")
    
    # Resource context
    resource_type = Column(String(50), nullable=True, index=True)
    resource_id = Column(String(100), nullable=True)  # String to support various ID types
    resource_name = Column(String(255), nullable=True)
    
    # Event details
    success = Column(Boolean, nullable=False, default=True)
    failure_reason = Column(Text, nullable=True)
    description = Column(Text, nullable=False)
    
    # Request context
    correlation_id = Column(String(36), nullable=True, index=True)  # UUID format
    user_agent = Column(Text, nullable=True)
    request_method = Column(String(10), nullable=True)
    request_path = Column(String(500), nullable=True)
    
    # Additional event metadata
    event_metadata = Column(JSON, nullable=True)
    
    # Tamper detection
    checksum = Column(String(64), nullable=True)  # SHA-256 hash
    previous_checksum = Column(String(64), nullable=True)  # Chain integrity
    
    # Compliance and retention
    retention_date = Column(DateTime(timezone=True), nullable=True)
    compliance_tags = Column(JSON, nullable=True)  # ["GDPR", "SOC2", etc.]
    
    # User relationship
    user = relationship("User", backref="security_events")
    
    # Table constraints and indexes
    __table_args__ = (
        # Ensure event type is not empty
        CheckConstraint("trim(event_type) != ''", name='event_type_not_empty'),
        # Ensure severity is valid
        CheckConstraint(
            "severity IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')", 
            name='valid_severity'
        ),
        # Performance indexes
        Index('idx_security_events_timestamp', 'created_at'),
        Index('idx_security_events_user_time', 'user_id', 'created_at'),
        Index('idx_security_events_type_time', 'event_type', 'created_at'),
        Index('idx_security_events_category_severity', 'event_category', 'severity'),
        Index('idx_security_events_resource', 'resource_type', 'resource_id'),
        Index('idx_security_events_correlation', 'correlation_id'),
        # Compliance and retention indexes
        Index('idx_security_events_retention', 'retention_date'),
        Index('idx_security_events_compliance', 'compliance_tags'),
    )
    
    @validates('event_type', 'event_category')
    def validate_required_fields(self, key, value):
        """Validate required string fields are not empty."""
        if value and not value.strip():
            raise ValueError(f"{key} cannot be empty")
        return value.strip() if value else value
    
    @validates('severity')
    def validate_severity(self, key, severity):
        """Validate severity level."""
        valid_severities = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if severity and severity not in valid_severities:
            raise ValueError(f"Invalid severity: {severity}")
        return severity
    
    def calculate_checksum(self) -> str:
        """
        Calculate SHA-256 checksum for tamper detection.
        
        Returns:
            str: SHA-256 hash of event data
        """
        # Create deterministic representation of event data
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'user_email': self.user_email,
            'event_type': self.event_type,
            'event_category': self.event_category,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'success': self.success,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'event_metadata': self.event_metadata
        }
        
        # Create JSON string with sorted keys for consistency
        json_data = json.dumps(data, sort_keys=True, default=str)
        
        # Calculate SHA-256 hash
        return hashlib.sha256(json_data.encode('utf-8')).hexdigest()
    
    def verify_integrity(self) -> bool:
        """
        Verify event integrity using stored checksum.
        
        Returns:
            bool: True if event has not been tampered with
        """
        if not self.checksum:
            return False
        
        current_checksum = self.calculate_checksum()
        return current_checksum == self.checksum
    
    def set_retention_policy(self, days: int, compliance_tags: Optional[list] = None):
        """
        Set retention policy for the audit event.
        
        Args:
            days: Number of days to retain the event
            compliance_tags: Optional compliance tags (GDPR, SOC2, etc.)
        """
        if days > 0:
            self.retention_date = func.now() + func.make_interval(days=days)
        
        if compliance_tags:
            self.compliance_tags = compliance_tags
    
    def to_audit_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format suitable for external audit systems.
        
        Returns:
            Dict: Audit trail dictionary
        """
        return {
            'id': self.id,
            'timestamp': self.created_at.isoformat() if self.created_at else None,
            'user_id': self.user_id,
            'user_email': self.user_email,
            'user_ip': self.user_ip,
            'event_type': self.event_type,
            'event_category': self.event_category,
            'severity': self.severity,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'resource_name': self.resource_name,
            'success': self.success,
            'failure_reason': self.failure_reason,
            'description': self.description,
            'correlation_id': self.correlation_id,
            'user_agent': self.user_agent,
            'request_method': self.request_method,
            'request_path': self.request_path,
            'event_metadata': self.event_metadata,
            'checksum': self.checksum,
            'compliance_tags': self.compliance_tags
        }
    
    def __repr__(self) -> str:
        return (
            f"<SecurityEvent(id={self.id}, type='{self.event_type}', "
            f"user_id={self.user_id}, success={self.success})>"
        )


class AuditLog(Base):
    """
    High-level audit log for compliance reporting.
    
    Aggregates security events for compliance and reporting purposes.
    """
    
    __tablename__ = "audit_logs"
    __allow_unmapped__ = True
    
    # Log event metadata
    log_type = Column(String(50), nullable=False, index=True)
    log_level = Column(String(20), nullable=False, default="INFO")
    
    # Aggregation context
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    event_count = Column(Integer, nullable=False, default=0)
    
    # Compliance context
    compliance_period = Column(String(50), nullable=True)  # "2024-Q1", "2024-01", etc.
    compliance_framework = Column(String(50), nullable=True)  # "GDPR", "SOC2", etc.
    
    # Summary data
    summary = Column(JSON, nullable=True)
    statistics = Column(JSON, nullable=True)
    
    # Integrity
    log_checksum = Column(String(64), nullable=True)
    
    # Table constraints and indexes
    __table_args__ = (
        CheckConstraint("start_time <= end_time", name='valid_time_range'),
        CheckConstraint("event_count >= 0", name='non_negative_event_count'),
        Index('idx_audit_logs_time_range', 'start_time', 'end_time'),
        Index('idx_audit_logs_compliance', 'compliance_framework', 'compliance_period'),
        Index('idx_audit_logs_type_level', 'log_type', 'log_level'),
    )
    
    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, type='{self.log_type}', "
            f"events={self.event_count})>"
        )


# Event type constants for consistency
class SecurityEventTypes:
    """Security event type constants."""
    
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_REVOCATION = "token_revocation"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    MFA_SUCCESS = "mfa_success"
    MFA_FAILURE = "mfa_failure"
    
    # Authorization events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_ESCALATION = "permission_escalation"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"
    
    # Data access events
    DATA_READ = "data_read"
    DATA_CREATE = "data_create"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    
    # Security violations
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SECURITY_POLICY_VIOLATION = "security_policy_violation"
    BRUTE_FORCE_ATTEMPT = "brute_force_attempt"
    
    # System events
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_UPDATE = "security_update"
    BACKUP_CREATED = "backup_created"
    BACKUP_RESTORED = "backup_restored"


# Event category constants
class SecurityEventCategories:
    """Security event category constants."""
    
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    SECURITY_VIOLATION = "security_violation"
    SYSTEM_SECURITY = "system_security"
    COMPLIANCE = "compliance"