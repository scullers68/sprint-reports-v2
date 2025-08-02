"""
Custom middleware for error handling, logging, request processing, and security audit.

Provides centralized error handling, structured logging, request tracking,
and comprehensive security auditing for the FastAPI application.
"""

import time
import uuid
from typing import Callable, Any, Dict, Optional
import traceback
import logging

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from app.core.logging import get_audit_logger
from app.models.security import SecurityEventTypes, SecurityEventCategories

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
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

logger = structlog.get_logger()


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware for consistent error responses.
    
    Catches unhandled exceptions and converts them to proper HTTP responses
    with appropriate status codes and error messages.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through error handling.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/endpoint in the chain
            
        Returns:
            Response: HTTP response with error handling applied
        """
        try:
            response = await call_next(request)
            return response
        except HTTPException:
            # Re-raise HTTP exceptions to be handled by FastAPI
            raise
        except SQLAlchemyError as e:
            logger.error(
                "Database error occurred",
                error_type="SQLAlchemyError",
                error_message=str(e),
                request_path=request.url.path,
                request_method=request.method
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Database error",
                    "message": "A database error occurred while processing your request",
                    "type": "database_error"
                }
            )
        except ValueError as e:
            logger.warning(
                "Validation error occurred",
                error_type="ValueError",
                error_message=str(e),
                request_path=request.url.path,
                request_method=request.method
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Validation error",
                    "message": str(e),
                    "type": "validation_error"
                }
            )
        except Exception as e:
            logger.error(
                "Unhandled exception occurred",
                error_type=type(e).__name__,
                error_message=str(e),
                traceback=traceback.format_exc(),
                request_path=request.url.path,
                request_method=request.method
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred while processing your request",
                    "type": "internal_error"
                }
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Request logging middleware for structured request/response logging.
    
    Logs all incoming requests with timing information, response status,
    and request correlation IDs for tracing.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with logging.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/endpoint in the chain
            
        Returns:
            Response: HTTP response with logging applied
        """
        # Generate correlation ID for request tracing
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        start_time = time.time()
        
        # Log incoming request
        logger.info(
            "Incoming request",
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            user_agent=request.headers.get("user-agent"),
            client_ip=request.client.host if request.client else None
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            "Request processed",
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time_seconds=round(process_time, 4)
        )
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Process-Time"] = str(round(process_time, 4))
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware for adding security-related HTTP headers.
    
    Adds common security headers to all responses to improve application security.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with security headers.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/endpoint in the chain
            
        Returns:
            Response: HTTP response with security headers added
        """
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        # Add HSTS header for TLS enforcement
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Add additional security headers
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        
        return response


def get_correlation_id(request: Request) -> str:
    """
    Get correlation ID from request state.
    
    Args:
        request: The HTTP request object
        
    Returns:
        str: Correlation ID for the request
    """
    return getattr(request.state, "correlation_id", "unknown")


def get_user_context(request: Request) -> Dict[str, Any]:
    """
    Extract user context from request for audit logging.
    
    Args:
        request: The HTTP request object
        
    Returns:
        Dict containing user context information
    """
    # Extract user information from request state or JWT token
    # This will be populated by authentication middleware
    user_context = {
        "user_id": getattr(request.state, "user_id", None),
        "user_email": getattr(request.state, "user_email", None),
        "user_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }
    
    return user_context


class SecurityAuditMiddleware(BaseHTTPMiddleware):
    """
    Security audit middleware for comprehensive security event logging.
    
    Extends existing logging patterns to capture security-relevant events
    including authentication attempts, authorization checks, and suspicious activity.
    """

    def __init__(self, app):
        super().__init__(app)
        self.audit_logger = get_audit_logger()
        self.sensitive_paths = {
            "/api/v1/auth/login",
            "/api/v1/auth/logout", 
            "/api/v1/auth/refresh",
            "/api/v1/auth/reset-password",
        }
        self.protected_paths = {
            "/api/v1/sprints",
            "/api/v1/reports",
            "/api/v1/capacity",
            "/api/v1/admin",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with security audit logging.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/endpoint in the chain
            
        Returns:
            Response: HTTP response with security audit applied
        """
        start_time = time.time()
        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id
        
        # Extract user context
        user_context = get_user_context(request)
        
        # Log security-relevant request start
        if self._is_security_relevant(request):
            self.audit_logger.log_security_event(
                event_type="request_start",
                event_category=SecurityEventCategories.SYSTEM_SECURITY,
                description=f"Security-relevant request started: {request.method} {request.url.path}",
                user_id=user_context.get("user_id"),
                user_email=user_context.get("user_email"),
                user_ip=user_context.get("user_ip"),
                correlation_id=correlation_id,
                user_agent=user_context.get("user_agent"),
                request_method=request.method,
                request_path=request.url.path,
                metadata={
                    "query_params": dict(request.query_params),
                    "headers": dict(request.headers),
                }
            )
        
        # Process request and capture security events
        try:
            response = await call_next(request)
            
            # Log successful completion for security-relevant requests
            if self._is_security_relevant(request):
                process_time = time.time() - start_time
                
                self.audit_logger.log_security_event(
                    event_type="request_completed",
                    event_category=SecurityEventCategories.SYSTEM_SECURITY,
                    description=f"Security-relevant request completed: {request.method} {request.url.path}",
                    user_id=user_context.get("user_id"),
                    user_email=user_context.get("user_email"),
                    user_ip=user_context.get("user_ip"),
                    success=True,
                    correlation_id=correlation_id,
                    user_agent=user_context.get("user_agent"),
                    request_method=request.method,
                    request_path=request.url.path,
                    metadata={
                        "status_code": response.status_code,
                        "process_time_seconds": round(process_time, 4),
                    }
                )
                
                # Log authentication events
                if request.url.path in self.sensitive_paths:
                    self._log_authentication_event(request, response, user_context, correlation_id)
                
                # Log authorization events for protected resources
                elif request.url.path.startswith(tuple(self.protected_paths)):
                    self._log_authorization_event(request, response, user_context, correlation_id)
            
            # Detect and log suspicious activity
            self._detect_suspicious_activity(request, response, user_context, correlation_id)
            
            return response
            
        except HTTPException as e:
            # Log HTTP exceptions as security events
            process_time = time.time() - start_time
            
            if self._is_security_relevant(request) or e.status_code in [401, 403, 429]:
                self.audit_logger.log_security_event(
                    event_type="request_failed",
                    event_category=SecurityEventCategories.SECURITY_VIOLATION,
                    description=f"HTTP exception: {e.status_code} - {e.detail}",
                    user_id=user_context.get("user_id"),
                    user_email=user_context.get("user_email"),
                    user_ip=user_context.get("user_ip"),
                    success=False,
                    severity="WARNING" if e.status_code in [401, 403] else "ERROR",
                    correlation_id=correlation_id,
                    user_agent=user_context.get("user_agent"),
                    request_method=request.method,
                    request_path=request.url.path,
                    failure_reason=str(e.detail),
                    metadata={
                        "status_code": e.status_code,
                        "process_time_seconds": round(process_time, 4),
                    }
                )
            
            raise
            
        except Exception as e:
            # Log unhandled exceptions as security events
            process_time = time.time() - start_time
            
            self.audit_logger.log_security_event(
                event_type="request_error",
                event_category=SecurityEventCategories.SYSTEM_SECURITY,
                description=f"Unhandled exception: {type(e).__name__}",
                user_id=user_context.get("user_id"),
                user_email=user_context.get("user_email"),
                user_ip=user_context.get("user_ip"),
                success=False,
                severity="ERROR",
                correlation_id=correlation_id,
                user_agent=user_context.get("user_agent"),
                request_method=request.method,
                request_path=request.url.path,
                failure_reason=str(e),
                metadata={
                    "error_type": type(e).__name__,
                    "process_time_seconds": round(process_time, 4),
                    "traceback": traceback.format_exc(),
                }
            )
            
            raise

    def _is_security_relevant(self, request: Request) -> bool:
        """
        Determine if a request is security-relevant for audit logging.
        
        Args:
            request: The HTTP request
            
        Returns:
            bool: True if request should be audited
        """
        path = request.url.path
        
        # Always audit authentication endpoints
        if path in self.sensitive_paths:
            return True
        
        # Always audit protected resource access
        if path.startswith(tuple(self.protected_paths)):
            return True
        
        # Audit admin endpoints
        if "/admin" in path:
            return True
            
        # Audit any write operations (POST, PUT, DELETE, PATCH)
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            return True
        
        return False

    def _log_authentication_event(
        self, 
        request: Request, 
        response: Response, 
        user_context: Dict[str, Any], 
        correlation_id: str
    ) -> None:
        """Log authentication-specific events."""
        path = request.url.path
        success = response.status_code < 400
        
        if "/login" in path:
            event_type = SecurityEventTypes.LOGIN_SUCCESS if success else SecurityEventTypes.LOGIN_FAILURE
        elif "/logout" in path:
            event_type = SecurityEventTypes.LOGOUT
        elif "/refresh" in path:
            event_type = SecurityEventTypes.TOKEN_REFRESH
        else:
            event_type = "authentication_event"
        
        # Extract email from request body for failed logins (if available)
        user_email = user_context.get("user_email", "unknown")
        
        self.audit_logger.log_authentication_event(
            event_type=event_type,
            user_email=user_email,
            success=success,
            user_ip=user_context.get("user_ip"),
            correlation_id=correlation_id,
            failure_reason=f"HTTP {response.status_code}" if not success else None,
            metadata={
                "request_path": path,
                "status_code": response.status_code,
            }
        )

    def _log_authorization_event(
        self, 
        request: Request, 
        response: Response, 
        user_context: Dict[str, Any], 
        correlation_id: str
    ) -> None:
        """Log authorization-specific events."""
        success = response.status_code < 400
        
        event_type = SecurityEventTypes.ACCESS_GRANTED if success else SecurityEventTypes.ACCESS_DENIED
        
        # Extract resource information from path
        resource_type, resource_id = self._extract_resource_info(request.url.path)
        
        if user_context.get("user_id") and user_context.get("user_email"):
            self.audit_logger.log_authorization_event(
                event_type=event_type,
                user_id=user_context["user_id"],
                user_email=user_context["user_email"],
                resource_type=resource_type,
                resource_id=resource_id or "unknown",
                success=success,
                user_ip=user_context.get("user_ip"),
                correlation_id=correlation_id,
                failure_reason=f"HTTP {response.status_code}" if not success else None,
                metadata={
                    "request_method": request.method,
                    "request_path": request.url.path,
                    "status_code": response.status_code,
                }
            )

    def _detect_suspicious_activity(
        self, 
        request: Request, 
        response: Response, 
        user_context: Dict[str, Any], 
        correlation_id: str
    ) -> None:
        """Detect and log suspicious activity patterns."""
        
        # Rate limiting violations (429 status)
        if response.status_code == 429:
            self.audit_logger.log_security_violation(
                event_type=SecurityEventTypes.RATE_LIMIT_EXCEEDED,
                description=f"Rate limit exceeded for {request.url.path}",
                user_id=user_context.get("user_id"),
                user_email=user_context.get("user_email"),
                user_ip=user_context.get("user_ip"),
                severity="WARNING",
                correlation_id=correlation_id,
                metadata={
                    "request_path": request.url.path,
                    "request_method": request.method,
                }
            )
        
        # Multiple authentication failures could indicate brute force
        if (request.url.path in self.sensitive_paths and 
            response.status_code == 401 and 
            user_context.get("user_ip")):
            
            self.audit_logger.log_security_violation(
                event_type=SecurityEventTypes.BRUTE_FORCE_ATTEMPT,
                description=f"Authentication failure from {user_context['user_ip']}",
                user_ip=user_context["user_ip"],
                severity="WARNING",
                correlation_id=correlation_id,
                metadata={
                    "request_path": request.url.path,
                    "user_agent": user_context.get("user_agent"),
                }
            )
        
        # Suspicious user agent patterns
        user_agent = user_context.get("user_agent", "")
        if user_agent and self._is_suspicious_user_agent(user_agent):
            self.audit_logger.log_security_violation(
                event_type=SecurityEventTypes.SUSPICIOUS_ACTIVITY,
                description=f"Suspicious user agent detected: {user_agent[:100]}",
                user_id=user_context.get("user_id"),
                user_ip=user_context.get("user_ip"),
                severity="INFO",
                correlation_id=correlation_id,
                metadata={
                    "user_agent": user_agent,
                    "request_path": request.url.path,
                }
            )

    def _extract_resource_info(self, path: str) -> tuple[str, Optional[str]]:
        """
        Extract resource type and ID from request path.
        
        Args:
            path: Request path
            
        Returns:
            Tuple of (resource_type, resource_id)
        """
        parts = path.strip("/").split("/")
        
        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "v1":
            resource_type = parts[2]
            resource_id = parts[3] if len(parts) > 3 else None
            return resource_type, resource_id
        
        return "unknown", None

    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """
        Check if user agent appears suspicious.
        
        Args:
            user_agent: User agent string
            
        Returns:
            bool: True if user agent appears suspicious
        """
        suspicious_patterns = [
            "curl", "wget", "python-requests", "bot", "crawler", 
            "scanner", "scraper", "automated", "test"
        ]
        
        user_agent_lower = user_agent.lower()
        return any(pattern in user_agent_lower for pattern in suspicious_patterns)


class AuthorizationMiddleware(BaseHTTPMiddleware):
    """
    Authorization middleware for role-based access control.
    
    Checks user permissions for protected endpoints based on their roles
    and the required permissions for each endpoint.
    """
    
    def __init__(self, app, exempt_paths: list = None):
        """
        Initialize authorization middleware.
        
        Args:
            app: FastAPI application instance
            exempt_paths: List of paths exempt from authorization checks
        """
        super().__init__(app)
        self.exempt_paths = exempt_paths or [
            "/docs", "/redoc", "/openapi.json", "/health", 
            "/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/refresh"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with authorization checks.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/endpoint in the chain
            
        Returns:
            Response: HTTP response with authorization applied
        """
        path = request.url.path
        
        # Skip authorization for exempt paths
        if any(path.startswith(exempt_path) for exempt_path in self.exempt_paths):
            return await call_next(request)
        
        # Skip authorization for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Get user from request state (set by authentication middleware)
        user = getattr(request.state, "user", None)
        
        if not user:
            logger.warning(
                "Authorization failed - no authenticated user",
                path=path,
                method=request.method,
                correlation_id=get_correlation_id(request)
            )
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Authentication required",
                    "message": "You must be authenticated to access this resource",
                    "type": "authentication_error"
                }
            )
        
        # Check if user account is active
        if not user.is_active:
            logger.warning(
                "Authorization failed - inactive user account",
                user_id=user.id,
                path=path,
                method=request.method,
                correlation_id=get_correlation_id(request)
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Account inactive",
                    "message": "Your account is not active",
                    "type": "authorization_error"
                }
            )
        
        # Get required permission for this endpoint
        required_permission = self._get_required_permission(path, request.method)
        
        if required_permission:
            # Check if user has the required permission
            if not user.has_permission(required_permission):
                logger.warning(
                    "Authorization failed - insufficient permissions",
                    user_id=user.id,
                    required_permission=required_permission,
                    user_permissions=user.get_permissions(),
                    path=path,
                    method=request.method,
                    correlation_id=get_correlation_id(request)
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Insufficient permissions",
                        "message": f"You don't have permission to {required_permission}",
                        "type": "authorization_error",
                        "required_permission": required_permission
                    }
                )
        
        # Store permission context in request for potential use by endpoints
        request.state.required_permission = required_permission
        
        # Log successful authorization
        logger.debug(
            "Authorization successful",
            user_id=user.id,
            required_permission=required_permission,
            path=path,
            method=request.method,
            correlation_id=get_correlation_id(request)
        )
        
        return await call_next(request)
    
    def _get_required_permission(self, path: str, method: str) -> str:
        """
        Determine required permission based on path and HTTP method.
        
        Args:
            path: Request path
            method: HTTP method
            
        Returns:
            str: Required permission string or None if no permission required
        """
        # API path to permission mapping
        permission_map = {
            # Sprint endpoints
            "/api/v1/sprints": {
                "GET": "sprint.read",
                "POST": "sprint.write"
            },
            "/api/v1/sprints/{id}": {
                "GET": "sprint.read",
                "PUT": "sprint.write",
                "DELETE": "sprint.delete"
            },
            
            # Queue endpoints
            "/api/v1/queues": {
                "GET": "queue.read",
                "POST": "queue.generate"
            },
            "/api/v1/queues/{id}": {
                "GET": "queue.read",
                "PUT": "queue.write",
                "DELETE": "queue.delete"
            },
            
            # Report endpoints
            "/api/v1/reports": {
                "GET": "report.read",
                "POST": "report.create"
            },
            "/api/v1/reports/{id}": {
                "GET": "report.read",
                "PUT": "report.write",
                "DELETE": "report.delete"
            },
            
            # Capacity endpoints
            "/api/v1/capacity": {
                "GET": "capacity.read",
                "POST": "capacity.write",
                "PUT": "capacity.write"
            },
            
            # User management endpoints
            "/api/v1/users": {
                "GET": "user.read",
                "POST": "admin.users"
            },
            "/api/v1/users/{id}": {
                "GET": "user.read",
                "PUT": "user.write",
                "DELETE": "admin.users"
            },
            "/api/v1/users/{id}/roles": {
                "GET": "user.roles",
                "PUT": "user.roles",
                "POST": "user.roles",
                "DELETE": "user.roles"
            },
            
            # Admin endpoints
            "/api/v1/admin/roles": {
                "GET": "admin.roles",
                "POST": "admin.roles"
            },
            "/api/v1/admin/roles/{id}": {
                "GET": "admin.roles",
                "PUT": "admin.roles",
                "DELETE": "admin.roles"
            },
            "/api/v1/admin/permissions": {
                "GET": "admin.roles",
                "POST": "admin.roles"
            }
        }
        
        # Handle parameterized paths by removing {id} patterns
        normalized_path = path
        import re
        normalized_path = re.sub(r'/\d+', '/{id}', normalized_path)
        
        # Look up permission
        if normalized_path in permission_map:
            method_permissions = permission_map[normalized_path]
            return method_permissions.get(method.upper())
        
        # Default permissions for unknown paths
        if path.startswith("/api/v1/admin/"):
            return "admin.system"
        
        return None


def require_permission(permission: str):
    """
    Decorator to require specific permission for endpoint access.
    
    Args:
        permission: Required permission string
        
    Returns:
        Decorator function
    """
    def decorator(func):
        func._required_permission = permission
        return func
    return decorator


def get_current_user_permissions(request: Request) -> list[str]:
    """
    Get current user's permissions from request state.
    
    Args:
        request: HTTP request object
        
    Returns:
        List of permission strings
    """
    user = getattr(request.state, "user", None)
    if user:
        return user.get_permissions()
    return []


class JWTAuthenticationMiddleware(BaseHTTPMiddleware):
    """
    JWT authentication middleware for handling Bearer token validation.
    
    Handles JWT tokens from Authorization headers and sets user context.
    """

    def __init__(self, app, exempt_paths: list = None):
        """
        Initialize JWT authentication middleware.
        
        Args:
            app: FastAPI application instance
            exempt_paths: List of paths exempt from authentication checks
        """
        super().__init__(app)
        self.exempt_paths = exempt_paths or [
            "/docs", "/redoc", "/openapi.json", "/health",
            "/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/refresh",
            "/api/v1/auth/password/reset-request", "/api/v1/auth/password/reset-confirm",
            "/api/v1/auth/sso"
            # Note: /api/v1/auth/logout is NOT exempt because it requires authentication
        ]
        # Add exact match for root path
        self.exempt_exact_paths = ["/"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with JWT authentication.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/endpoint in the chain
            
        Returns:
            Response: HTTP response with authentication applied
        """
        path = request.url.path
        correlation_id = get_correlation_id(request)
        
        logger.debug(
            "JWT middleware processing request",
            path=path,
            method=request.method,
            correlation_id=correlation_id
        )
        
        # Skip authentication for exempt paths
        matching_exempt_path = None
        
        # Check exact matches first
        if path in self.exempt_exact_paths:
            matching_exempt_path = path
        else:
            # Check prefix matches
            for exempt_path in self.exempt_paths:
                if path.startswith(exempt_path):
                    matching_exempt_path = exempt_path
                    break
        
        if matching_exempt_path:
            logger.debug(
                "JWT middleware skipping exempt path",
                path=path,
                matched_exempt_path=matching_exempt_path,
                correlation_id=correlation_id
            )
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Extract JWT token from Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            # No token provided, let authorization middleware handle this
            return await call_next(request)
        
        token = authorization.split(" ")[1]
        
        # Validate JWT token and set user context
        try:
            from app.core.security import verify_token, get_user_by_id
            from app.core.database import async_session
            
            # Verify the JWT token
            token_data = verify_token(token, "access")
            
            if not token_data or not token_data.user_id:
                logger.debug(
                    "JWT token verification failed",
                    path=path,
                    correlation_id=correlation_id
                )
                return await call_next(request)
            
            # Get user from database
            async with async_session() as db:
                user = await get_user_by_id(db, token_data.user_id)
                if user and user.is_active:
                    # Set user in request state for authorization middleware
                    request.state.user = user
                    logger.debug(
                        "JWT authentication successful",
                        user_id=user.id,
                        path=path,
                        correlation_id=correlation_id
                    )
                    
        except Exception as e:
            # Log authentication error but don't block request
            # Let authorization middleware handle the missing user
            logger.warning(
                "JWT authentication failed",
                error=str(e),
                error_type=type(e).__name__,
                path=path,
                correlation_id=correlation_id
            )
        
        return await call_next(request)


class SSOAuthenticationMiddleware(BaseHTTPMiddleware):
    """
    SSO authentication middleware for handling SSO token validation.
    
    Handles authentication tokens from SSO providers and sets user context.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with SSO authentication.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/endpoint in the chain
            
        Returns:
            Response: HTTP response with SSO authentication applied
        """
        # Skip authentication for public endpoints
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)
        
        # Check for SSO authentication headers
        sso_token = request.headers.get("X-SSO-Token")
        sso_provider = request.headers.get("X-SSO-Provider")
        
        if sso_token and sso_provider:
            try:
                # Validate SSO token (implementation would depend on provider)
                user_info = await self._validate_sso_token(sso_token, sso_provider)
                if user_info:
                    request.state.sso_user = user_info
                    request.state.auth_method = "sso"
                    logger.info(
                        "SSO authentication successful",
                        provider=sso_provider,
                        user_id=user_info.get("user_id"),
                        correlation_id=get_correlation_id(request)
                    )
            except Exception as e:
                logger.warning(
                    "SSO token validation failed",
                    provider=sso_provider,
                    error=str(e),
                    correlation_id=get_correlation_id(request)
                )
        
        response = await call_next(request)
        return response
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public and doesn't require authentication."""
        public_paths = [
            "/",
            "/health",
            "/health/ready",
            "/health/live",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/sso/saml/initiate",
            "/api/v1/auth/sso/saml/acs",
            "/api/v1/auth/sso/oauth/initiate",
            "/api/v1/auth/sso/oauth/callback",
        ]
        return path in public_paths or path.startswith("/static/")
    
    async def _validate_sso_token(self, token: str, provider: str) -> Optional[Dict[str, Any]]:
        """
        Validate SSO token with provider.
        
        Args:
            token: SSO token to validate
            provider: SSO provider name
            
        Returns:
            User information if token is valid, None otherwise
        """
        # This would implement actual token validation logic
        # For now, return None to indicate validation failed
        # In a real implementation, this would:
        # 1. Validate token signature/format
        # 2. Check token expiration
        # 3. Extract user information
        # 4. Return structured user data
        return None


def add_custom_middleware(app):
    """
    Add custom middleware to FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Add custom middleware in reverse order (last added = first executed)
    app.add_middleware(SSOAuthenticationMiddleware)
    app.add_middleware(SecurityAuditMiddleware)
    app.add_middleware(AuthorizationMiddleware)
    app.add_middleware(JWTAuthenticationMiddleware)  # Add JWT auth before authorization
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)