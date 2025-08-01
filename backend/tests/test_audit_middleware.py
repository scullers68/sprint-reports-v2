"""
Tests for audit middleware functionality.

Tests for SecurityAuditMiddleware including security event capture,
suspicious activity detection, and request auditing.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request, Response, HTTPException
from starlette.datastructures import Headers

from app.core.middleware import SecurityAuditMiddleware, get_user_context
from app.models.security import SecurityEventTypes, SecurityEventCategories


class TestSecurityAuditMiddleware:
    """Test suite for SecurityAuditMiddleware."""
    
    @pytest.fixture
    def mock_app(self):
        """Mock FastAPI application."""
        return Mock()
    
    @pytest.fixture
    def audit_middleware(self, mock_app):
        """SecurityAuditMiddleware instance."""
        return SecurityAuditMiddleware(mock_app)
    
    @pytest.fixture
    def mock_request(self):
        """Mock HTTP request."""
        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/v1/auth/login"
        request.query_params = {}
        request.headers = Headers({"user-agent": "Mozilla/5.0", "host": "localhost"})
        request.client.host = "192.168.1.1"
        request.state = Mock()
        return request
    
    @pytest.fixture
    def mock_response(self):
        """Mock HTTP response."""
        response = Mock(spec=Response)
        response.status_code = 200
        response.headers = {}
        return response
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Mock audit logger."""
        with patch('app.core.middleware.get_audit_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            yield mock_logger
    
    @pytest.mark.asyncio
    async def test_dispatch_security_relevant_request(self, audit_middleware, mock_request, mock_response, mock_audit_logger):
        """Test dispatch for security-relevant request."""
        # Arrange
        mock_call_next = AsyncMock(return_value=mock_response)
        mock_request.state.correlation_id = "test-correlation-id"
        
        # Act
        response = await audit_middleware.dispatch(mock_request, mock_call_next)
        
        # Assert
        assert response == mock_response
        assert mock_audit_logger.log_security_event.call_count == 2  # start and completed
        
        # Check request start log
        start_call = mock_audit_logger.log_security_event.call_args_list[0]
        assert start_call[1]["event_type"] == "request_start"
        assert start_call[1]["event_category"] == SecurityEventCategories.SYSTEM_SECURITY
        
        # Check request completed log
        completed_call = mock_audit_logger.log_security_event.call_args_list[1]
        assert completed_call[1]["event_type"] == "request_completed"
        assert completed_call[1]["success"] is True
    
    @pytest.mark.asyncio
    async def test_dispatch_authentication_event(self, audit_middleware, mock_request, mock_response, mock_audit_logger):
        """Test dispatch for authentication endpoint."""
        # Arrange
        mock_call_next = AsyncMock(return_value=mock_response)
        mock_request.url.path = "/api/v1/auth/login"
        mock_request.state.correlation_id = "test-correlation-id"
        
        # Act
        await audit_middleware.dispatch(mock_request, mock_call_next)
        
        # Assert
        mock_audit_logger.log_authentication_event.assert_called_once()
        auth_call = mock_audit_logger.log_authentication_event.call_args[1]
        assert auth_call["event_type"] == SecurityEventTypes.LOGIN_SUCCESS
        assert auth_call["success"] is True
    
    @pytest.mark.asyncio
    async def test_dispatch_failed_authentication(self, audit_middleware, mock_request, mock_response, mock_audit_logger):
        """Test dispatch for failed authentication."""
        # Arrange
        mock_call_next = AsyncMock(return_value=mock_response)
        mock_request.url.path = "/api/v1/auth/login"
        mock_response.status_code = 401
        mock_request.state.correlation_id = "test-correlation-id"
        
        # Act
        await audit_middleware.dispatch(mock_request, mock_call_next)
        
        # Assert
        mock_audit_logger.log_authentication_event.assert_called_once()
        auth_call = mock_audit_logger.log_authentication_event.call_args[1]
        assert auth_call["event_type"] == SecurityEventTypes.LOGIN_FAILURE
        assert auth_call["success"] is False
    
    @pytest.mark.asyncio
    async def test_dispatch_authorization_event(self, audit_middleware, mock_request, mock_response, mock_audit_logger):
        """Test dispatch for protected resource access."""
        # Arrange
        mock_call_next = AsyncMock(return_value=mock_response)
        mock_request.url.path = "/api/v1/sprints/123"
        mock_request.method = "GET"
        mock_request.state.correlation_id = "test-correlation-id"
        mock_request.state.user_id = 1
        mock_request.state.user_email = "test@example.com"
        
        # Act
        await audit_middleware.dispatch(mock_request, mock_call_next)
        
        # Assert
        mock_audit_logger.log_authorization_event.assert_called_once()
        auth_call = mock_audit_logger.log_authorization_event.call_args[1]
        assert auth_call["event_type"] == SecurityEventTypes.ACCESS_GRANTED
        assert auth_call["resource_type"] == "sprints"
        assert auth_call["resource_id"] == "123"
    
    @pytest.mark.asyncio
    async def test_dispatch_http_exception(self, audit_middleware, mock_request, mock_audit_logger):
        """Test dispatch with HTTP exception."""
        # Arrange
        http_exception = HTTPException(status_code=403, detail="Access denied")
        mock_call_next = AsyncMock(side_effect=http_exception)
        mock_request.state.correlation_id = "test-correlation-id"
        
        # Act & Assert
        with pytest.raises(HTTPException):
            await audit_middleware.dispatch(mock_request, mock_call_next)
        
        # Verify security event was logged
        assert mock_audit_logger.log_security_event.call_count >= 2  # start + failed
        failed_calls = [call for call in mock_audit_logger.log_security_event.call_args_list 
                       if call[1].get("event_type") == "request_failed"]
        assert len(failed_calls) == 1
        assert failed_calls[0][1]["success"] is False
    
    @pytest.mark.asyncio
    async def test_dispatch_unhandled_exception(self, audit_middleware, mock_request, mock_audit_logger):
        """Test dispatch with unhandled exception."""
        # Arrange
        exception = Exception("Something went wrong")
        mock_call_next = AsyncMock(side_effect=exception)
        mock_request.state.correlation_id = "test-correlation-id"
        
        # Act & Assert
        with pytest.raises(Exception):
            await audit_middleware.dispatch(mock_request, mock_call_next)
        
        # Verify security event was logged
        error_calls = [call for call in mock_audit_logger.log_security_event.call_args_list 
                      if call[1].get("event_type") == "request_error"]
        assert len(error_calls) == 1
        assert error_calls[0][1]["severity"] == "ERROR"
    
    @pytest.mark.asyncio
    async def test_detect_rate_limiting(self, audit_middleware, mock_request, mock_response, mock_audit_logger):
        """Test detection of rate limiting violations."""
        # Arrange
        mock_call_next = AsyncMock(return_value=mock_response)
        mock_response.status_code = 429
        mock_request.state.correlation_id = "test-correlation-id"
        
        # Act
        await audit_middleware.dispatch(mock_request, mock_call_next)
        
        # Assert
        mock_audit_logger.log_security_violation.assert_called_once()
        violation_call = mock_audit_logger.log_security_violation.call_args[1]
        assert violation_call["event_type"] == SecurityEventTypes.RATE_LIMIT_EXCEEDED
    
    @pytest.mark.asyncio
    async def test_detect_brute_force_attempt(self, audit_middleware, mock_request, mock_response, mock_audit_logger):
        """Test detection of brute force attempts."""
        # Arrange
        mock_call_next = AsyncMock(return_value=mock_response)
        mock_request.url.path = "/api/v1/auth/login"
        mock_response.status_code = 401
        mock_request.client.host = "192.168.1.100"
        mock_request.state.correlation_id = "test-correlation-id"
        
        # Act
        await audit_middleware.dispatch(mock_request, mock_call_next)
        
        # Assert
        brute_force_calls = [call for call in mock_audit_logger.log_security_violation.call_args_list 
                           if call[1].get("event_type") == SecurityEventTypes.BRUTE_FORCE_ATTEMPT]
        assert len(brute_force_calls) == 1
    
    @pytest.mark.asyncio
    async def test_detect_suspicious_user_agent(self, audit_middleware, mock_request, mock_response, mock_audit_logger):
        """Test detection of suspicious user agents."""
        # Arrange
        mock_call_next = AsyncMock(return_value=mock_response)
        mock_request.headers = Headers({"user-agent": "curl/7.68.0"})
        mock_request.state.correlation_id = "test-correlation-id"
        
        # Act
        await audit_middleware.dispatch(mock_request, mock_call_next)
        
        # Assert
        suspicious_calls = [call for call in mock_audit_logger.log_security_violation.call_args_list 
                          if call[1].get("event_type") == SecurityEventTypes.SUSPICIOUS_ACTIVITY]
        assert len(suspicious_calls) == 1
    
    def test_is_security_relevant_auth_endpoint(self, audit_middleware, mock_request):
        """Test security relevance check for auth endpoints."""
        # Arrange
        mock_request.url.path = "/api/v1/auth/login"
        
        # Act
        result = audit_middleware._is_security_relevant(mock_request)
        
        # Assert
        assert result is True
    
    def test_is_security_relevant_protected_endpoint(self, audit_middleware, mock_request):
        """Test security relevance check for protected endpoints."""
        # Arrange
        mock_request.url.path = "/api/v1/sprints/123"
        
        # Act
        result = audit_middleware._is_security_relevant(mock_request)
        
        # Assert
        assert result is True
    
    def test_is_security_relevant_write_operation(self, audit_middleware, mock_request):
        """Test security relevance check for write operations."""
        # Arrange
        mock_request.method = "POST"
        mock_request.url.path = "/api/v1/public/data"
        
        # Act
        result = audit_middleware._is_security_relevant(mock_request)
        
        # Assert
        assert result is True
    
    def test_is_security_relevant_read_operation(self, audit_middleware, mock_request):
        """Test security relevance check for read operations."""
        # Arrange
        mock_request.method = "GET"
        mock_request.url.path = "/api/v1/public/health"
        
        # Act
        result = audit_middleware._is_security_relevant(mock_request)
        
        # Assert
        assert result is False
    
    def test_extract_resource_info_valid_path(self, audit_middleware):
        """Test resource information extraction from valid API path."""
        # Act
        resource_type, resource_id = audit_middleware._extract_resource_info("/api/v1/sprints/123")
        
        # Assert
        assert resource_type == "sprints"
        assert resource_id == "123"
    
    def test_extract_resource_info_no_id(self, audit_middleware):
        """Test resource information extraction from path without ID."""
        # Act
        resource_type, resource_id = audit_middleware._extract_resource_info("/api/v1/sprints")
        
        # Assert
        assert resource_type == "sprints"
        assert resource_id is None
    
    def test_extract_resource_info_invalid_path(self, audit_middleware):
        """Test resource information extraction from invalid path."""
        # Act
        resource_type, resource_id = audit_middleware._extract_resource_info("/invalid/path")
        
        # Assert
        assert resource_type == "unknown"
        assert resource_id is None
    
    def test_is_suspicious_user_agent_curl(self, audit_middleware):
        """Test suspicious user agent detection for curl."""
        # Act
        result = audit_middleware._is_suspicious_user_agent("curl/7.68.0")
        
        # Assert
        assert result is True
    
    def test_is_suspicious_user_agent_bot(self, audit_middleware):
        """Test suspicious user agent detection for bot."""
        # Act
        result = audit_middleware._is_suspicious_user_agent("GoogleBot/2.1")
        
        # Assert
        assert result is True
    
    def test_is_suspicious_user_agent_normal_browser(self, audit_middleware):
        """Test suspicious user agent detection for normal browser."""
        # Act
        result = audit_middleware._is_suspicious_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        
        # Assert
        assert result is False


class TestGetUserContext:
    """Test suite for get_user_context function."""
    
    @pytest.fixture
    def mock_request(self):
        """Mock HTTP request."""
        request = Mock(spec=Request)
        request.headers = Headers({"user-agent": "Mozilla/5.0"})
        request.client.host = "192.168.1.1"
        request.state = Mock()
        request.state.user_id = 1
        request.state.user_email = "test@example.com"
        return request
    
    def test_get_user_context_complete(self, mock_request):
        """Test getting user context with all information available."""
        # Act
        context = get_user_context(mock_request)
        
        # Assert
        assert context["user_id"] == 1
        assert context["user_email"] == "test@example.com"
        assert context["user_ip"] == "192.168.1.1"
        assert context["user_agent"] == "Mozilla/5.0"
    
    def test_get_user_context_missing_user_info(self, mock_request):
        """Test getting user context without user information."""
        # Arrange
        mock_request.state.user_id = None
        mock_request.state.user_email = None
        
        # Act
        context = get_user_context(mock_request)
        
        # Assert
        assert context["user_id"] is None
        assert context["user_email"] is None
        assert context["user_ip"] == "192.168.1.1"
        assert context["user_agent"] == "Mozilla/5.0"
    
    def test_get_user_context_no_client(self, mock_request):
        """Test getting user context without client information."""
        # Arrange
        mock_request.client = None
        
        # Act
        context = get_user_context(mock_request)
        
        # Assert
        assert context["user_ip"] is None


if __name__ == "__main__":
    pytest.main([__file__])