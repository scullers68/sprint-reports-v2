"""
Custom exception classes and error handling for Sprint Reports API.

Provides standardized error responses and exception handling patterns.
"""

from typing import Any, Dict, Optional, List
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

logger = logging.getLogger(__name__)


class SprintReportsException(Exception):
    """Base exception class for Sprint Reports application."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(SprintReportsException):
    """Exception for validation errors."""
    
    def __init__(self, message: str, field_errors: Optional[List[Dict[str, str]]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details={"field_errors": field_errors or []}
        )


class NotFoundError(SprintReportsException):
    """Exception for resource not found errors."""
    
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} not found",
            error_code="RESOURCE_NOT_FOUND",
            details={"resource": resource, "identifier": str(identifier)}
        )


class DuplicateResourceError(SprintReportsException):
    """Exception for duplicate resource creation attempts."""
    
    def __init__(self, resource: str, field: str, value: Any):
        super().__init__(
            message=f"{resource} with {field} '{value}' already exists",
            error_code="DUPLICATE_RESOURCE",
            details={"resource": resource, "field": field, "value": str(value)}
        )


class ExternalServiceError(SprintReportsException):
    """Exception for external service integration errors."""
    
    def __init__(self, service: str, message: str, status_code: Optional[int] = None):
        super().__init__(
            message=f"{service} error: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service, "status_code": status_code}
        )


class AuthenticationError(SprintReportsException):
    """Exception for authentication errors."""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(SprintReportsException):
    """Exception for authorization errors."""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR"
        )


class RateLimitError(SprintReportsException):
    """Exception for rate limiting errors."""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED"
        )


def create_error_response(
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create standardized error response."""
    return {
        "error": {
            "code": error_code,
            "message": message,
            "details": details or {},
            "request_id": request_id
        }
    }


async def sprint_reports_exception_handler(
    request: Request, 
    exc: SprintReportsException
) -> JSONResponse:
    """Handle Sprint Reports custom exceptions."""
    request_id = getattr(request.state, "request_id", None)
    
    # Determine HTTP status code based on exception type
    status_code_map = {
        "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
        "RESOURCE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "DUPLICATE_RESOURCE": status.HTTP_409_CONFLICT,
        "EXTERNAL_SERVICE_ERROR": status.HTTP_502_BAD_GATEWAY,
        "AUTHENTICATION_ERROR": status.HTTP_401_UNAUTHORIZED,
        "AUTHORIZATION_ERROR": status.HTTP_403_FORBIDDEN,
        "RATE_LIMIT_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
    }
    
    status_code = status_code_map.get(exc.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Log error for monitoring
    logger.error(
        "API error occurred",
        extra={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    response_data = create_error_response(
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status_code,
        content=response_data
    )


async def http_exception_handler(
    request: Request, 
    exc: HTTPException
) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    request_id = getattr(request.state, "request_id", None)
    
    logger.warning(
        "HTTP exception occurred",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    response_data = create_error_response(
        error_code="HTTP_ERROR",
        message=str(exc.detail),
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


async def validation_exception_handler(
    request: Request, 
    exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    request_id = getattr(request.state, "request_id", None)
    
    # Format validation errors
    field_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        field_errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        "Validation error occurred",
        extra={
            "field_errors": field_errors,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    response_data = create_error_response(
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        details={"field_errors": field_errors},
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response_data
    )


async def generic_exception_handler(
    request: Request, 
    exc: Exception
) -> JSONResponse:
    """Handle unexpected exceptions."""
    request_id = getattr(request.state, "request_id", None)
    
    logger.error(
        "Unexpected error occurred",
        extra={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        },
        exc_info=True
    )
    
    response_data = create_error_response(
        error_code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_data
    )