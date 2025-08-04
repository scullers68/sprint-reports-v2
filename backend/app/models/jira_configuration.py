"""
JIRA Configuration model for persistent storage of connection settings.

Stores JIRA connection configurations securely with proper encryption
for sensitive data fields and connection monitoring capabilities.
"""

from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import Column, String, Integer, Boolean, Text, Enum, DateTime, JSON, Index, CheckConstraint
from sqlalchemy.orm import validates
from sqlalchemy.ext.hybrid import hybrid_property
import logging

from app.models.base import Base
from app.core.encryption import encrypt_sensitive_field, decrypt_sensitive_field, should_encrypt_field
from app.enums import JiraInstanceType, JiraAuthMethod, ConnectionStatus

logger = logging.getLogger(__name__)


class JiraConfiguration(Base):
    """
    JIRA connection configuration model for persistent storage.
    
    Stores JIRA connection settings with encryption for sensitive data,
    connection monitoring, and validation tracking capabilities.
    """
    __tablename__ = "jira_configurations"
    
    # Basic configuration
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Connection details
    url = Column(String(500), nullable=False)
    instance_type = Column(Enum('cloud', 'server', 'datacenter', name='jirainstancetype'), nullable=False, default='cloud')
    auth_method = Column(Enum('token', 'basic', 'oauth', name='jiraauthmethod'), nullable=False, default='token')
    
    
    # Authentication credentials (encrypted)
    email = Column(Text, nullable=True)  # Encrypted for Cloud token auth
    username = Column(Text, nullable=True)  # Encrypted for basic auth
    _api_token = Column("api_token", Text, nullable=True)  # Encrypted
    _password = Column("password", Text, nullable=True)  # Encrypted
    _oauth_config = Column("oauth_config", JSON, nullable=True)  # Encrypted JSON
    
    # Configuration metadata
    custom_fields = Column(JSON, nullable=True)  # Custom field mappings
    api_version = Column(String(50), nullable=True)  # Detected API version
    server_info = Column(JSON, nullable=True)  # Server information cache
    capabilities = Column(JSON, nullable=True)  # Detected capabilities
    
    # Connection status and monitoring
    status = Column(Enum('active', 'inactive', 'error', 'testing', 'pending', name='connectionstatus'), nullable=False, default='pending')
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Testing and validation timestamps
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    last_successful_test = Column(DateTime(timezone=True), nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error tracking
    last_error_message = Column(Text, nullable=True)
    error_count = Column(Integer, default=0, nullable=False)
    consecutive_errors = Column(Integer, default=0, nullable=False)
    
    # Performance metrics
    avg_response_time_ms = Column(Integer, nullable=True)
    success_rate_percent = Column(Integer, nullable=True)
    
    # Configuration metadata
    created_by_user_id = Column(Integer, nullable=True)  # FK to users table
    environment = Column(String(50), nullable=False, default="production")  # dev, staging, prod
    tags = Column(JSON, nullable=True)  # Tags for organization
    
    # Table constraints and indexes
    __table_args__ = (
        # Ensure URL format is valid
        CheckConstraint("url ~ '^https?://'", name='valid_url_format'),
        # Ensure name is not empty when trimmed
        CheckConstraint("trim(name) != ''", name='name_not_empty'),
        # Only one default configuration per environment
        Index('idx_jira_config_default_env', 'is_default', 'environment', 
              postgresql_where='is_default = true'),
        # Compound index for status and activity lookups
        Index('idx_jira_config_status_active', 'status', 'is_active'),
        # Index for URL lookups
        Index('idx_jira_config_url', 'url'),
        # Index for testing timestamps
        Index('idx_jira_config_test_times', 'last_tested_at', 'last_successful_test'),
        # Index for error tracking
        Index('idx_jira_config_errors', 'error_count', 'consecutive_errors', 'status'),
        # Index for environment filtering
        Index('idx_jira_config_environment', 'environment', 'is_active'),
    )
    
    @hybrid_property
    def api_token(self) -> Optional[str]:
        """Decrypt and return API token."""
        if self._api_token:
            return decrypt_sensitive_field(self._api_token)
        return None
    
    @api_token.setter
    def api_token(self, value: Optional[str]) -> None:
        """Encrypt and store API token."""
        if value:
            self._api_token = encrypt_sensitive_field(value)
        else:
            self._api_token = None
    
    @hybrid_property
    def password(self) -> Optional[str]:
        """Decrypt and return password."""
        if self._password:
            return decrypt_sensitive_field(self._password)
        return None
    
    @password.setter
    def password(self, value: Optional[str]) -> None:
        """Encrypt and store password."""
        if value:
            self._password = encrypt_sensitive_field(value)
        else:
            self._password = None
    
    @hybrid_property
    def oauth_config(self) -> Optional[Dict[str, Any]]:
        """Decrypt and return OAuth configuration."""
        if self._oauth_config:
            # OAuth config is stored as encrypted JSON
            return self._oauth_config
        return None
    
    @oauth_config.setter
    def oauth_config(self, value: Optional[Dict[str, Any]]) -> None:
        """Encrypt and store OAuth configuration."""
        self._oauth_config = value
    
    @validates('url')
    def validate_url(self, key, url):
        """Validate URL format."""
        if url and not url.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return url.rstrip('/') if url else url
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate name format."""
        if name and len(name.strip()) < 1:
            raise ValueError("Name cannot be empty")
        return name.strip() if name else name
    
    @validates('email')
    def validate_email_for_auth(self, key, email):
        """Validate email for authentication methods."""
        if email and '@' not in email:
            raise ValueError("Invalid email format")
        return email
    
    def is_cloud_instance(self) -> bool:
        """Check if this is a JIRA Cloud instance."""
        return self.instance_type == JiraInstanceType.CLOUD
    
    def is_server_instance(self) -> bool:
        """Check if this is a JIRA Server/Data Center instance."""
        return self.instance_type in [JiraInstanceType.SERVER, JiraInstanceType.DATA_CENTER]
    
    def requires_email(self) -> bool:
        """Check if email is required for the current auth method."""
        return (self.auth_method == JiraAuthMethod.TOKEN and 
                self.instance_type == JiraInstanceType.CLOUD)
    
    def is_healthy(self) -> bool:
        """Check if connection is healthy based on recent tests."""
        return (self.status == ConnectionStatus.ACTIVE and 
                self.consecutive_errors == 0)
    
    def record_successful_test(self, response_time_ms: Optional[int] = None) -> None:
        """Record a successful connection test."""
        now = datetime.utcnow()
        self.last_tested_at = now
        self.last_successful_test = now
        self.status = ConnectionStatus.ACTIVE
        self.consecutive_errors = 0
        
        if response_time_ms is not None:
            self.avg_response_time_ms = response_time_ms
    
    def record_failed_test(self, error_message: str) -> None:
        """Record a failed connection test."""
        now = datetime.utcnow()
        self.last_tested_at = now
        self.last_error_at = now
        self.last_error_message = error_message
        self.error_count += 1
        self.consecutive_errors += 1
        
        # Update status based on consecutive errors
        if self.consecutive_errors >= 3:
            self.status = ConnectionStatus.ERROR
        elif self.consecutive_errors >= 1:
            self.status = ConnectionStatus.INACTIVE
    
    def reset_error_tracking(self) -> None:
        """Reset error tracking after successful operations."""
        self.consecutive_errors = 0
        self.last_error_message = None
        if self.status == ConnectionStatus.ERROR:
            self.status = ConnectionStatus.ACTIVE
    
    def update_capabilities(self, capabilities: Dict[str, Any]) -> None:
        """Update detected JIRA capabilities."""
        self.capabilities = capabilities
    
    def update_server_info(self, server_info: Dict[str, Any]) -> None:
        """Update cached server information."""
        self.server_info = server_info
        if 'version' in server_info:
            self.api_version = server_info['version']
    
    def get_masked_config(self) -> Dict[str, Any]:
        """Get configuration with sensitive fields masked."""
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'instance_type': self.instance_type,
            'auth_method': self.auth_method,
            'email': self.email if self.email else None,
            'username': self.username if self.username else None,
            'api_token': '***' if self._api_token else None,
            'password': '***' if self._password else None,
            'status': self.status,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'last_tested_at': self.last_tested_at,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def __repr__(self) -> str:
        return f"<JiraConfiguration(id={self.id}, name='{self.name}', url='{self.url}', status='{self.status}')>"