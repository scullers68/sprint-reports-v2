"""
Pydantic schemas for JIRA integration.

Defines request/response models for JIRA connection management,
configuration, and validation endpoints.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, validator


class JiraInstanceType(str, Enum):
    """JIRA instance type enumeration."""
    CLOUD = "cloud"
    SERVER = "server"
    DATA_CENTER = "datacenter"


class JiraAuthMethod(str, Enum):
    """JIRA authentication method enumeration."""
    TOKEN = "token"
    BASIC = "basic"
    OAUTH = "oauth"


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