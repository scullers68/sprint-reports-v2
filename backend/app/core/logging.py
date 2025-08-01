"""
Structured logging configuration for the application.

Provides centralized logging setup with structured JSON logging,
correlation tracking, performance monitoring, and security audit logging.
"""

import logging
import logging.config
import re
from typing import Dict, Any, Optional, Union
import structlog
from datetime import datetime, timezone
from app.core.config import settings


# Patterns for sensitive data that should be masked in logs
SENSITIVE_PATTERNS = [
    (re.compile(r'("password"\s*:\s*")[^"]*(")', re.IGNORECASE), r'\1***\2'),
    (re.compile(r'("token"\s*:\s*")[^"]*(")', re.IGNORECASE), r'\1***\2'),
    (re.compile(r'("api_key"\s*:\s*")[^"]*(")', re.IGNORECASE), r'\1***\2'),
    (re.compile(r'("secret"\s*:\s*")[^"]*(")', re.IGNORECASE), r'\1***\2'),
    (re.compile(r'("authorization"\s*:\s*")[^"]*(")', re.IGNORECASE), r'\1***\2'),
    (re.compile(r'("email"\s*:\s*")[^"]*@[^"]*(")', re.IGNORECASE), r'\1***@***.***\2'),
    (re.compile(r'("phone"\s*:\s*")[^"]*(")', re.IGNORECASE), r'\1***-***-****\2'),
    (re.compile(r'("ssn"\s*:\s*")[^"]*(")', re.IGNORECASE), r'\1***-**-****\2'),
    (re.compile(r'("credit_card"\s*:\s*")[^"]*(")', re.IGNORECASE), r'\1****-****-****-****\2'),
    # Bearer token pattern
    (re.compile(r'(Bearer\s+)[A-Za-z0-9\-_\.]+', re.IGNORECASE), r'\1***'),
    # API key patterns
    (re.compile(r'([Aa]pi[_-]?[Kk]ey["\s]*[:=]["\s]*)[A-Za-z0-9]+', re.IGNORECASE), r'\1***'),
]


def mask_sensitive_data(data: Union[str, Dict, Any]) -> Union[str, Dict, Any]:
    """
    Mask sensitive data in logs to prevent exposure of secrets.
    
    Args:
        data: Data to be logged (string, dict, or other)
        
    Returns:
        Data with sensitive information masked
    """
    if isinstance(data, str):
        # Apply all patterns to mask sensitive data
        masked_data = data
        for pattern, replacement in SENSITIVE_PATTERNS:
            masked_data = pattern.sub(replacement, masked_data)
        return masked_data
    
    elif isinstance(data, dict):
        # Recursively mask dictionary values
        masked_dict = {}
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if key name indicates sensitive data
            if any(sensitive in key_lower for sensitive in ['password', 'token', 'secret', 'key', 'auth']):
                masked_dict[key] = '***'
            else:
                masked_dict[key] = mask_sensitive_data(value)
        return masked_dict
    
    elif isinstance(data, (list, tuple)):
        # Recursively mask list/tuple items
        return type(data)(mask_sensitive_data(item) for item in data)
    
    else:
        # Return non-string/dict data as-is
        return data


class SensitiveDataMaskingProcessor:
    """
    Structlog processor to mask sensitive data in log records.
    """
    
    def __call__(self, logger, method_name, event_dict):
        """
        Process log event to mask sensitive data.
        
        Args:
            logger: Logger instance
            method_name: Log method name
            event_dict: Event dictionary to process
            
        Returns:
            dict: Processed event dictionary with masked sensitive data
        """
        # Mask sensitive data in all event dict values
        masked_event = {}
        for key, value in event_dict.items():
            masked_event[key] = mask_sensitive_data(value)
        
        return masked_event


def configure_logging() -> None:
    """
    Configure structured logging for the application.
    
    Sets up JSON-based structured logging with appropriate log levels,
    formatters, and handlers for different environments.
    """
    
    # Logging configuration
    log_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
        },
        "handlers": {
            "default": {
                "level": settings.LOG_LEVEL,
                "formatter": "standard",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {  # root logger
                "handlers": ["default"],
                "level": settings.LOG_LEVEL,
                "propagate": False
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["default"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO", 
                "handlers": ["default"],
                "propagate": False
            },
            "sqlalchemy.engine": {
                "level": "INFO" if settings.LOG_LEVEL == "DEBUG" else "WARNING",
                "handlers": ["default"],
                "propagate": False
            },
            "alembic": {
                "level": "INFO",
                "handlers": ["default"],
                "propagate": False
            }
        }
    }
    
    # Apply logging configuration
    logging.config.dictConfig(log_config)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            SensitiveDataMaskingProcessor(),  # Add sensitive data masking
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Get a configured structured logger.
    
    Args:
        name: Optional logger name, defaults to caller's module
        
    Returns:
        structlog.BoundLogger: Configured structured logger
    """
    return structlog.get_logger(name)


class LoggerMixin:
    """
    Mixin class to add logging capabilities to any class.
    
    Provides a logger property that returns a bound logger
    with the class name as the logger name.
    """
    
    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger bound to this class."""
        return get_logger(self.__class__.__name__)


def log_performance(func):
    """
    Decorator to log function performance metrics.
    
    Args:
        func: Function to wrap with performance logging
        
    Returns:
        Wrapped function with performance logging
    """
    import time
    import functools
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = get_logger(f"{func.__module__}.{func.__name__}")
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(
                "Function executed successfully",
                function=func.__name__,
                duration_seconds=round(duration, 4),
                args_count=len(args),
                kwargs_count=len(kwargs)
            )
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Function execution failed",
                function=func.__name__,
                error_type=type(e).__name__,
                error_message=str(e),
                duration_seconds=round(duration, 4)
            )
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = get_logger(f"{func.__module__}.{func.__name__}")
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(
                "Function executed successfully",
                function=func.__name__,
                duration_seconds=round(duration, 4),
                args_count=len(args),
                kwargs_count=len(kwargs)
            )
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Function execution failed",
                function=func.__name__,
                error_type=type(e).__name__,
                error_message=str(e),
                duration_seconds=round(duration, 4)
            )
            raise
    
    # Return appropriate wrapper based on function type
    if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
        return async_wrapper
    else:
        return sync_wrapper


class AuditLogger:
    """
    Security audit logger extending existing structured logging patterns.
    
    Provides specialized logging for security events, compliance,
    and audit trail generation.
    """
    
    def __init__(self, name: str = "audit"):
        """Initialize audit logger."""
        self.logger = get_logger(name)
        self.enabled = settings.ENABLE_AUDIT_LOGGING
    
    def log_security_event(
        self,
        event_type: str,
        event_category: str,
        description: str,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
        user_ip: Optional[str] = None,
        success: bool = True,
        severity: str = "INFO",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        correlation_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        failure_reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        compliance_tags: Optional[list] = None
    ) -> None:
        """
        Log a security audit event.
        
        Args:
            event_type: Type of security event (login, access_denied, etc.)
            event_category: Category (authentication, authorization, etc.)
            description: Human-readable description
            user_id: Optional user ID
            user_email: Optional user email for audit trail
            user_ip: Optional user IP address
            success: Whether the event was successful
            severity: Log severity level
            resource_type: Type of resource accessed
            resource_id: ID of resource accessed
            resource_name: Name of resource accessed
            correlation_id: Request correlation ID
            user_agent: User agent string
            request_method: HTTP method
            request_path: Request path
            failure_reason: Reason for failure (if applicable)
            metadata: Additional event metadata
            compliance_tags: Compliance framework tags
        """
        if not self.enabled:
            return
        
        # Build audit event data
        audit_data = {
            "event_type": event_type,
            "event_category": event_category,
            "description": description,
            "success": success,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Add user context if available
        if user_id is not None:
            audit_data["user_id"] = user_id
        if user_email:
            audit_data["user_email"] = user_email
        if user_ip:
            audit_data["user_ip"] = user_ip
        
        # Add resource context if available
        if resource_type:
            audit_data["resource_type"] = resource_type
        if resource_id:
            audit_data["resource_id"] = resource_id
        if resource_name:
            audit_data["resource_name"] = resource_name
        
        # Add request context if available
        if correlation_id:
            audit_data["correlation_id"] = correlation_id
        if user_agent:
            audit_data["user_agent"] = user_agent
        if request_method:
            audit_data["request_method"] = request_method
        if request_path:
            audit_data["request_path"] = request_path
        
        # Add failure context if applicable
        if not success and failure_reason:
            audit_data["failure_reason"] = failure_reason
        
        # Add metadata if available
        if metadata:
            audit_data["metadata"] = metadata
        
        # Add compliance tags if available
        if compliance_tags:
            audit_data["compliance_tags"] = compliance_tags
        
        # Log the audit event
        log_method = getattr(self.logger, severity.lower(), self.logger.info)
        log_method("Security audit event", **audit_data)
    
    def log_authentication_event(
        self,
        event_type: str,
        user_email: str,
        success: bool,
        user_ip: Optional[str] = None,
        correlation_id: Optional[str] = None,
        failure_reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log authentication-related security event.
        
        Args:
            event_type: Authentication event type
            user_email: User email address
            success: Whether authentication was successful
            user_ip: User IP address
            correlation_id: Request correlation ID
            failure_reason: Failure reason if unsuccessful
            metadata: Additional metadata
        """
        self.log_security_event(
            event_type=event_type,
            event_category="authentication",
            description=f"Authentication event: {event_type}",
            user_email=user_email,
            user_ip=user_ip,
            success=success,
            severity="WARNING" if not success else "INFO",
            correlation_id=correlation_id,
            failure_reason=failure_reason,
            metadata=metadata,
            compliance_tags=["GDPR", "SOC2"]
        )
    
    def log_authorization_event(
        self,
        event_type: str,
        user_id: int,
        user_email: str,
        resource_type: str,
        resource_id: str,
        success: bool,
        user_ip: Optional[str] = None,
        correlation_id: Optional[str] = None,
        failure_reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log authorization-related security event.
        
        Args:
            event_type: Authorization event type
            user_id: User ID
            user_email: User email address
            resource_type: Type of resource accessed
            resource_id: ID of resource accessed
            success: Whether authorization was successful
            user_ip: User IP address
            correlation_id: Request correlation ID
            failure_reason: Failure reason if unsuccessful
            metadata: Additional metadata
        """
        self.log_security_event(
            event_type=event_type,
            event_category="authorization",
            description=f"Authorization event: {event_type} for {resource_type}",
            user_id=user_id,
            user_email=user_email,
            user_ip=user_ip,
            success=success,
            severity="WARNING" if not success else "INFO",
            resource_type=resource_type,
            resource_id=resource_id,
            correlation_id=correlation_id,
            failure_reason=failure_reason,
            metadata=metadata,
            compliance_tags=["GDPR", "SOC2"]
        )
    
    def log_data_access_event(
        self,
        event_type: str,
        user_id: int,
        user_email: str,
        resource_type: str,
        resource_id: str,
        resource_name: Optional[str] = None,
        user_ip: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log data access security event.
        
        Args:
            event_type: Data access event type
            user_id: User ID
            user_email: User email address
            resource_type: Type of resource accessed
            resource_id: ID of resource accessed
            resource_name: Name of resource accessed
            user_ip: User IP address
            correlation_id: Request correlation ID
            metadata: Additional metadata
        """
        self.log_security_event(
            event_type=event_type,
            event_category="data_access",
            description=f"Data access: {event_type} on {resource_type}",
            user_id=user_id,
            user_email=user_email,
            user_ip=user_ip,
            success=True,
            severity="INFO",
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            correlation_id=correlation_id,
            metadata=metadata,
            compliance_tags=["GDPR", "SOC2"]
        )
    
    def log_security_violation(
        self,
        event_type: str,
        description: str,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
        user_ip: Optional[str] = None,
        severity: str = "WARNING",
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log security violation event.
        
        Args:
            event_type: Security violation type
            description: Description of the violation
            user_id: Optional user ID
            user_email: Optional user email
            user_ip: Optional user IP address
            severity: Severity level (WARNING, ERROR, CRITICAL)
            correlation_id: Request correlation ID
            metadata: Additional metadata
        """
        self.log_security_event(
            event_type=event_type,
            event_category="security_violation",
            description=description,
            user_id=user_id,
            user_email=user_email,
            user_ip=user_ip,
            success=False,
            severity=severity,
            correlation_id=correlation_id,
            metadata=metadata,
            compliance_tags=["SOC2"]
        )


# Global audit logger instance
audit_logger = AuditLogger()


def get_audit_logger() -> AuditLogger:
    """
    Get the global audit logger instance.
    
    Returns:
        AuditLogger: Global audit logger
    """
    return audit_logger