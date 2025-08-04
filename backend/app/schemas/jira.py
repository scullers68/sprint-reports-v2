"""
Pydantic schemas for JIRA integration.

Defines request/response models for JIRA connection management,
configuration, and validation endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator

from app.enums import JiraInstanceType, JiraAuthMethod


class JiraConnectionConfigBase(BaseModel):
    """Base JIRA connection configuration."""
    url: str = Field(..., description="JIRA instance URL")
    auth_method: JiraAuthMethod = Field(JiraAuthMethod.TOKEN, description="Authentication method")
    is_cloud: Optional[bool] = Field(None, description="True for Cloud, False for Server, None for auto-detect")
    
    @validator('url')
    def validate_url(cls, v):
        """Validate JIRA URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v.rstrip('/')


class JiraConnectionConfig(JiraConnectionConfigBase):
    """JIRA connection configuration with credentials."""
    email: Optional[str] = Field(None, description="Email for Cloud token authentication")
    api_token: Optional[str] = Field(None, description="API token for authentication")
    username: Optional[str] = Field(None, description="Username for basic authentication")
    password: Optional[str] = Field(None, description="Password for basic authentication")
    oauth_config: Optional[Dict[str, str]] = Field(None, description="OAuth configuration")
    custom_fields: Optional[Dict[str, str]] = Field(None, description="Custom field mappings")
    
    @validator('email')
    def validate_email_for_cloud(cls, v, values):
        """Validate email is provided for Cloud token authentication."""
        auth_method = values.get('auth_method')
        is_cloud = values.get('is_cloud')
        
        if auth_method == JiraAuthMethod.TOKEN and is_cloud and not v:
            raise ValueError('Email is required for JIRA Cloud token authentication')
        return v
    
    @validator('api_token')
    def validate_token_auth(cls, v, values):
        """Validate token is provided for token authentication."""
        auth_method = values.get('auth_method')
        
        if auth_method == JiraAuthMethod.TOKEN and not v:
            raise ValueError('API token is required for token authentication')
        return v
    
    @validator('username')
    def validate_basic_auth_username(cls, v, values):
        """Validate username is provided for basic authentication."""
        auth_method = values.get('auth_method')
        
        if auth_method == JiraAuthMethod.BASIC and not v:
            raise ValueError('Username is required for basic authentication')
        return v
    
    @validator('password')
    def validate_basic_auth_password(cls, v, values):
        """Validate password is provided for basic authentication."""
        auth_method = values.get('auth_method')
        
        if auth_method == JiraAuthMethod.BASIC and not v:
            raise ValueError('Password is required for basic authentication')
        return v


class JiraConnectionTest(BaseModel):
    """JIRA connection test request."""
    config: JiraConnectionConfig
    test_operations: List[str] = Field(
        default=["server_info", "projects", "boards"], 
        description="Operations to test: server_info, projects, boards, sprints, custom_fields"
    )
    timeout_seconds: int = Field(30, description="Test timeout in seconds")


class JiraTestResult(BaseModel):
    """Individual test result."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    response_time_ms: Optional[float] = None


class JiraConnectionTestResult(BaseModel):
    """JIRA connection test result."""
    connection_valid: bool
    configuration: Dict[str, Any]
    tests: Dict[str, JiraTestResult]
    errors: List[str]
    recommendations: List[str]
    total_time_ms: Optional[float] = None


class JiraConnectionStatus(BaseModel):
    """JIRA connection status response."""
    connected: bool
    url: str
    is_cloud: bool
    api_version: str
    last_test: Optional[datetime]
    error: Optional[str]
    server_info: Optional[Dict[str, Any]]
    capabilities: List[str]


class JiraHealthStatus(str, Enum):
    """JIRA health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class JiraHealthCheck(BaseModel):
    """JIRA health check response."""
    status: JiraHealthStatus
    last_check: datetime
    response_time_ms: Optional[float]
    error_count_24h: int = 0
    success_rate_24h: float = 0.0
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class JiraCapabilities(BaseModel):
    """JIRA capabilities response."""
    basic_connectivity: bool = False
    agile_api: bool = False
    projects_access: bool = False
    boards_access: bool = False
    sprints_access: bool = False
    issues_access: bool = False
    custom_fields_access: bool = False
    webhooks_supported: bool = False
    field_discovery: bool = False
    supported_operations: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class JiraSetupResult(BaseModel):
    """JIRA connection setup result."""
    status: str
    url: str
    auth_method: str
    is_cloud: bool
    api_version: str
    configured_at: datetime
    test_results: Optional[JiraConnectionTestResult] = None


class JiraServerInfo(BaseModel):
    """JIRA server information."""
    base_url: str
    version: str
    version_numbers: List[int]
    deployment_type: str
    build_number: int
    build_date: datetime
    server_time: datetime
    scm_info: Optional[str] = None
    server_title: str


class JiraProject(BaseModel):
    """JIRA project information."""
    id: str
    key: str
    name: str
    project_type_key: str
    simplified: bool = False
    style: str = "classic"
    is_private: bool = False
    
    
class JiraBoard(BaseModel):
    """JIRA board information."""
    id: int
    name: str
    type: str
    project_key: Optional[str] = None
    location: Optional[Dict[str, Any]] = None


class JiraSprint(BaseModel):
    """JIRA sprint information."""
    id: int
    name: str
    state: str
    board_id: int
    goal: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    complete_date: Optional[datetime] = None


class JiraCustomField(BaseModel):
    """JIRA custom field information."""
    id: str
    name: str
    description: Optional[str] = None
    field_type: str
    searchable: bool = False
    orderable: bool = False
    navigable: bool = False
    field_schema: Optional[Dict[str, Any]] = None


class JiraFieldMapping(BaseModel):
    """JIRA field mapping configuration."""
    jira_field_id: str
    jira_field_name: str
    sprint_reports_field: str
    field_type: str
    transformation: Optional[str] = None
    default_value: Optional[Any] = None
    is_required: bool = False


class JiraFieldDiscovery(BaseModel):
    """JIRA field discovery result."""
    total_custom_fields: int
    used_fields: int
    field_analysis: Dict[str, Any]
    mapping_suggestions: List[Dict[str, Any]]
    confidence_threshold: float = 0.7


class JiraConnectionMonitoring(BaseModel):
    """JIRA connection monitoring data."""
    uptime_percentage: float
    average_response_time_ms: float
    error_rate_percentage: float
    last_successful_call: Optional[datetime] = None
    last_failed_call: Optional[datetime] = None
    total_calls_24h: int = 0
    successful_calls_24h: int = 0
    failed_calls_24h: int = 0


class JiraConnectionAlert(BaseModel):
    """JIRA connection alert."""
    alert_type: str  # "error", "warning", "info"
    message: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class JiraConnectionDashboard(BaseModel):
    """JIRA connection dashboard data."""
    status: JiraConnectionStatus
    health: JiraHealthCheck
    monitoring: JiraConnectionMonitoring
    recent_alerts: List[JiraConnectionAlert]
    capabilities: JiraCapabilities


# JIRA Configuration Management Schemas

class JiraConfigurationCreate(BaseModel):
    """Schema for creating a new JIRA configuration."""
    name: str = Field(..., min_length=1, max_length=200, description="Configuration name")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description")
    config: JiraConnectionConfig = Field(..., description="JIRA connection configuration")
    environment: str = Field("production", description="Environment (dev, staging, production)")
    is_default: bool = Field(False, description="Set as default configuration for environment")
    test_connection: bool = Field(True, description="Test connection before saving")
    tags: Optional[List[str]] = Field(None, description="Optional tags for organization")

    @validator('name')
    def validate_name(cls, v):
        """Validate configuration name."""
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()

    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment value."""
        valid_environments = ['dev', 'development', 'staging', 'uat', 'production', 'prod']
        if v.lower() not in valid_environments:
            raise ValueError(f'Environment must be one of: {", ".join(valid_environments)}')
        return v.lower()


class JiraConfigurationUpdate(BaseModel):
    """Schema for updating an existing JIRA configuration."""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Configuration name")
    description: Optional[str] = Field(None, max_length=1000, description="Configuration description")
    config: Optional[JiraConnectionConfig] = Field(None, description="JIRA connection configuration")
    is_active: Optional[bool] = Field(None, description="Configuration active status")
    is_default: Optional[bool] = Field(None, description="Set as default configuration")
    test_connection: bool = Field(True, description="Test connection if config updated")
    tags: Optional[List[str]] = Field(None, description="Tags for organization")

    @validator('name')
    def validate_name(cls, v):
        """Validate configuration name."""
        if v is not None and not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip() if v else v


class JiraConfigurationResponse(BaseModel):
    """Schema for JIRA configuration response."""
    id: int
    name: str
    description: Optional[str]
    url: str
    instance_type: str
    auth_method: str
    email: Optional[str]
    username: Optional[str]
    # Sensitive fields are masked by default
    has_api_token: bool = Field(False, description="Whether API token is configured")
    has_password: bool = Field(False, description="Whether password is configured")
    has_oauth_config: bool = Field(False, description="Whether OAuth config is configured")
    # Optionally included sensitive fields for editing
    api_token: Optional[str] = Field(None, description="API token (only when include_sensitive=true)")
    password: Optional[str] = Field(None, description="Password (only when include_sensitive=true)")
    custom_fields: Optional[Dict[str, Any]]
    api_version: Optional[str]
    server_info: Optional[Dict[str, Any]]
    capabilities: Optional[Dict[str, Any]]
    status: str
    is_active: bool
    is_default: bool
    last_tested_at: Optional[datetime]
    last_successful_test: Optional[datetime]
    last_error_at: Optional[datetime]
    last_error_message: Optional[str]
    error_count: int
    consecutive_errors: int
    avg_response_time_ms: Optional[int]
    success_rate_percent: Optional[int]
    environment: str
    tags: Optional[List[str]]
    created_at: datetime
    updated_at: datetime
    created_by_user_id: Optional[int]

    @classmethod
    def from_orm_with_security(cls, config):
        """Create response from ORM object with security considerations."""
        return cls(
            id=config.id,
            name=config.name,
            description=config.description,
            url=config.url,
            instance_type=config.instance_type,
            auth_method=config.auth_method,
            email=config.email,
            username=config.username,
            has_api_token=bool(config._api_token),
            has_password=bool(config._password),
            has_oauth_config=bool(config._oauth_config),
            custom_fields=config.custom_fields,
            api_version=config.api_version,
            server_info=config.server_info,
            capabilities=config.capabilities,
            status=config.status,
            is_active=config.is_active,
            is_default=config.is_default,
            last_tested_at=config.last_tested_at,
            last_successful_test=config.last_successful_test,
            last_error_at=config.last_error_at,
            last_error_message=config.last_error_message,
            error_count=config.error_count,
            consecutive_errors=config.consecutive_errors,
            avg_response_time_ms=config.avg_response_time_ms,
            success_rate_percent=config.success_rate_percent,
            environment=config.environment,
            tags=config.tags,
            created_at=config.created_at,
            updated_at=config.updated_at,
            created_by_user_id=config.created_by_user_id
        )


class JiraConfigurationList(BaseModel):
    """Schema for listing JIRA configurations."""
    configurations: List[JiraConfigurationResponse]
    total: int
    page: int = 1
    page_size: int = 100
    has_next: bool = False
    has_previous: bool = False


class JiraConfigurationTestRequest(BaseModel):
    """Schema for testing a specific configuration."""
    config_id: int = Field(..., description="Configuration ID to test")
    update_status: bool = Field(True, description="Update configuration status based on test result")


class JiraConfigurationStatusFilter(BaseModel):
    """Schema for filtering configurations by status."""
    environment: Optional[str] = Field(None, description="Filter by environment")
    status: Optional[str] = Field(None, description="Filter by connection status")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_default: Optional[bool] = Field(None, description="Filter by default status")
    limit: int = Field(100, ge=1, le=1000, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Number of results to skip")


class JiraConfigurationMonitoringResponse(BaseModel):
    """Schema for configuration monitoring response."""
    total_configurations: int
    healthy_count: int
    error_count: int
    inactive_count: int
    health_percentage: float
    environment: Optional[str]
    timestamp: datetime
    configurations: List[Dict[str, Any]]