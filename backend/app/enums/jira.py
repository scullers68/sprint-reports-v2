"""
Shared JIRA enumerations for use across models, schemas, and services.

Defines common enum values for JIRA configuration and connection management
to ensure consistency across the application.
"""

from enum import Enum as PyEnum


class JiraInstanceType(str, PyEnum):
    """JIRA instance type enumeration."""
    CLOUD = "cloud"
    SERVER = "server"
    DATA_CENTER = "datacenter"


class JiraAuthMethod(str, PyEnum):
    """JIRA authentication method enumeration."""
    TOKEN = "token"
    BASIC = "basic"
    OAUTH = "oauth"


class ConnectionStatus(str, PyEnum):
    """Connection status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    TESTING = "testing"
    PENDING = "pending"