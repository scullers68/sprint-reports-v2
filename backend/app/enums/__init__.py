"""
Shared enumerations for the Sprint Reports application.

Provides common enum definitions used across models, schemas, and services
to ensure consistency and prevent duplication.
"""

from app.enums.jira import (
    JiraInstanceType,
    JiraAuthMethod,
    ConnectionStatus
)

__all__ = [
    "JiraInstanceType",
    "JiraAuthMethod", 
    "ConnectionStatus"
]