"""
Tests for JIRA API client and service.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import httpx
import os

# Mock settings before importing
os.environ.update({
    'SECRET_KEY': 'test-secret-key-for-testing-only',
    'ENCRYPTION_KEY': 'test-encryption-key-for-testing-only-32-bytes',
    'POSTGRES_SERVER': 'localhost',
    'POSTGRES_USER': 'test',
    'POSTGRES_PASSWORD': 'test',
    'POSTGRES_DB': 'test',
    'JIRA_URL': 'https://kineo.atlassian.net',
    'JIRA_EMAIL': 'russell.grocott@kineo.com.au',
    'JIRA_API_TOKEN': 'test-token',
    'CONFLUENCE_URL': 'https://kineo.atlassian.net/wiki',
    'JIRA_WEBHOOK_SECRET': 'test-webhook-secret'
})

from app.services.jira_service import JiraAPIClient, JiraService
from app.core.exceptions import ExternalServiceError, RateLimitError


class TestJiraAPIClient:
    """Test cases for JiraAPIClient."""
    
    def test_detect_cloud_instance(self):
        """Test cloud instance detection."""
        # Cloud instance
        client = JiraAPIClient("https://company.atlassian.net")
        assert client.is_cloud is True
        
        # Server instance
        client = JiraAPIClient("https://jira.company.com")
        assert client.is_cloud is False
    
    def test_init_with_token_auth_cloud(self):
        """Test initialization with token authentication for cloud."""
        client = JiraAPIClient(
            "https://company.atlassian.net",
            auth_method="token",
            email="test@example.com",
            api_token="token123"
        )
        
        assert client.is_cloud is True
        assert client.auth_method == "token"
        assert client.email == "test@example.com"
        assert client.api_token == "token123"
        assert client.preferred_api_version == "3"
    
    def test_init_with_basic_auth_server(self):
        """Test initialization with basic authentication for server."""
        client = JiraAPIClient(
            "https://jira.company.com",
            auth_method="basic",
            username="testuser",
            password="testpass"
        )
        
        assert client.is_cloud is False
        assert client.auth_method == "basic"
        assert client.username == "testuser"
        assert client.password == "testpass"
        assert client.preferred_api_version == "2"
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        client = JiraAPIClient("https://jira.example.com")
        client._rate_limit_max_calls = 2
        client._rate_limit_window = 1
        
        # First two calls should pass
        await client._check_rate_limit()
        await client._check_rate_limit()
        
        # Third call should trigger rate limiting (but we won't wait)
        start_time = client._rate_limit_window_start
        client._rate_limit_calls = client._rate_limit_max_calls
        
        # Mock time to avoid actual waiting
        with patch('asyncio.sleep'):
            await client._check_rate_limit()
    
    @pytest.mark.asyncio
    async def test_make_request_with_retry_success(self):
        """Test successful request with retry logic."""
        client = JiraAPIClient("https://jira.example.com")
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        
        client.client = AsyncMock()
        client.client.request = AsyncMock(return_value=mock_response)
        
        response = await client._make_request_with_retry("GET", "/test")
        
        assert response.status_code == 200
        client.client.request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_make_request_with_retry_rate_limit(self):
        """Test request retry on rate limit."""
        client = JiraAPIClient("https://jira.example.com")
        
        # Mock rate limit response then success
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"Retry-After": "1"}
        
        success_response = Mock()
        success_response.status_code = 200
        
        client.client = AsyncMock()
        client.client.request = AsyncMock(side_effect=[rate_limit_response, success_response])
        
        with patch('asyncio.sleep'):
            response = await client._make_request_with_retry("GET", "/test")
        
        assert response.status_code == 200
        assert client.client.request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_make_request_with_retry_auth_failure(self):
        """Test authentication failure handling."""
        client = JiraAPIClient("https://jira.example.com")
        
        # Mock authentication failure
        auth_failure_response = Mock()
        auth_failure_response.status_code = 401
        
        client.client = AsyncMock()
        client.client.request = AsyncMock(return_value=auth_failure_response)
        
        with pytest.raises(ExternalServiceError) as exc_info:
            await client._make_request_with_retry("GET", "/test")
        
        assert "Authentication failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test."""
        client = JiraAPIClient("https://jira.example.com")
        client.get = AsyncMock(return_value={"version": "8.0.0"})
        
        result = await client.test_connection()
        
        assert result is True
        client.get.assert_called_once_with("/rest/api/2/serverInfo")
    
    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test failed connection test."""
        client = JiraAPIClient("https://jira.example.com")
        client.get = AsyncMock(side_effect=Exception("Connection failed"))
        
        result = await client.test_connection()
        
        assert result is False


class TestJiraService:
    """Test cases for JiraService."""
    
    @pytest.mark.asyncio
    async def test_get_client_creates_client(self):
        """Test that _get_client creates and tests client."""
        service = JiraService()
        
        with patch('app.services.jira_service.JiraAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.test_connection = AsyncMock(return_value=True)
            mock_client_class.return_value = mock_client
            
            client = await service._get_client()
            
            assert client == mock_client
            mock_client.test_connection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_client_connection_failure(self):
        """Test client creation with connection failure."""
        service = JiraService()
        
        with patch('app.services.jira_service.JiraAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.test_connection = AsyncMock(return_value=False)
            mock_client_class.return_value = mock_client
            
            with pytest.raises(ExternalServiceError):
                await service._get_client()
    
    @pytest.mark.asyncio
    async def test_get_sprints_success(self):
        """Test successful sprint retrieval."""
        service = JiraService()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value={
            "values": [
                {"id": 1, "name": "Sprint 1", "state": "ACTIVE"}
            ]
        })
        
        service._client = mock_client
        
        sprints = await service.get_sprints(board_id=123)
        
        assert len(sprints) == 1
        assert sprints[0]["name"] == "Sprint 1"
        mock_client.get.assert_called_once_with(
            "/rest/agile/1.0/board/123/sprint",
            params={"maxResults": 100}
        )
    
    @pytest.mark.asyncio
    async def test_get_sprints_fallback_on_error(self):
        """Test sprint retrieval fallback on error."""
        service = JiraService()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("API Error"))
        
        service._client = mock_client
        
        sprints = await service.get_sprints()
        
        # Should return placeholder data
        assert len(sprints) == 1
        assert sprints[0]["name"] == "Sample Sprint"
    
    @pytest.mark.asyncio
    async def test_get_sprint_issues_success(self):
        """Test successful sprint issues retrieval."""
        service = JiraService()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value={
            "issues": [
                {
                    "key": "TEST-123",
                    "fields": {
                        "issuetype": {"subtask": False},
                        "summary": "Test issue"
                    }
                }
            ]
        })
        
        service._client = mock_client
        
        issues = await service.get_sprint_issues(sprint_id=456)
        
        assert len(issues) == 1
        assert issues[0]["key"] == "TEST-123"
        mock_client.get.assert_called_once_with(
            "/rest/agile/1.0/sprint/456/issue",
            params={"maxResults": 1000}
        )
    
    @pytest.mark.asyncio
    async def test_get_sprint_issues_exclude_subtasks(self):
        """Test sprint issues retrieval excluding subtasks."""
        service = JiraService()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value={
            "issues": [
                {
                    "key": "TEST-123",
                    "fields": {"issuetype": {"subtask": False}}
                },
                {
                    "key": "TEST-124",
                    "fields": {"issuetype": {"subtask": True}}
                }
            ]
        })
        
        service._client = mock_client
        
        issues = await service.get_sprint_issues(sprint_id=456, exclude_subtasks=True)
        
        assert len(issues) == 1
        assert issues[0]["key"] == "TEST-123"
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test."""
        service = JiraService()
        
        mock_client = AsyncMock()
        mock_client.get_server_info = AsyncMock(return_value={"version": "8.0.0"})
        mock_client.is_cloud = False
        mock_client.preferred_api_version = "2"
        
        service._client = mock_client
        
        result = await service.test_connection()
        
        assert result["connected"] is True
        assert result["server_info"]["version"] == "8.0.0"
        assert result["is_cloud"] is False
        assert result["api_version"] == "2"
    
    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test failed connection test."""
        service = JiraService()
        
        mock_client = AsyncMock()
        mock_client.get_server_info = AsyncMock(side_effect=Exception("Connection failed"))
        
        service._client = mock_client
        
        result = await service.test_connection()
        
        assert result["connected"] is False
        assert "Connection failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test client connection closing."""
        service = JiraService()
        
        mock_client = AsyncMock()
        service._client = mock_client
        
        await service.close()
        
        mock_client.close.assert_called_once()
        assert service._client is None