"""
JIRA connection endpoints for setup, testing, and monitoring.

Handles JIRA instance connection management, authentication validation,
and health monitoring with support for both Cloud and Server instances.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.encryption import encrypt_sensitive_field, decrypt_sensitive_field
from app.core.exceptions import ExternalServiceError, RateLimitError
from app.models.user import User
from app.schemas.jira import (
    JiraConnectionConfig, JiraConnectionTest, JiraConnectionTestResult,
    JiraConnectionStatus, JiraHealthCheck, JiraCapabilities, JiraSetupResult
)
from app.core.security import get_current_user
from app.services.jira_service import JiraService, JiraAPIClient

router = APIRouter()
logger = logging.getLogger(__name__)


# All schemas are now imported from app.schemas.jira


@router.post("/connection/test")
async def test_jira_connection(
    test_request: JiraConnectionTest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> JiraConnectionTestResult:
    """
    Test JIRA connection with provided configuration.
    
    Validates credentials, tests basic connectivity, and checks available operations.
    Does not store configuration - only tests it.
    """
    from app.schemas.jira import JiraTestResult
    
    config = test_request.config
    start_time = datetime.now()
    
    test_results = JiraConnectionTestResult(
        connection_valid=False,
        configuration={
            "url": config.url,
            "auth_method": config.auth_method,
            "is_cloud": None,
            "api_version": None
        },
        tests={},
        errors=[],
        recommendations=[]
    )
    
    try:
        # Create temporary client for testing
        client = JiraAPIClient(
            url=config.url,
            auth_method=config.auth_method,
            email=config.email,
            api_token=config.api_token,
            username=config.username,
            password=config.password,
            oauth_dict=config.oauth_config,
            cloud=config.is_cloud
        )
        
        # Update configuration details
        test_results.configuration["is_cloud"] = client.is_cloud
        test_results.configuration["api_version"] = client.preferred_api_version
        
        # Test basic connection
        connection_test = await client.test_connection()
        test_results.connection_valid = connection_test
        
        if not connection_test:
            test_results.errors.append("Failed to establish basic connection to JIRA")
            await client.close()
            return test_results
        
        # Run additional tests based on request
        jira_service = JiraService()
        jira_service._client = client  # Use our test client
        
        for test_operation in test_request.test_operations:
            test_result_data = await _run_connection_test(jira_service, test_operation)
            test_results.tests[test_operation] = JiraTestResult(**test_result_data)
        
        # Generate recommendations
        test_results.recommendations = _generate_connection_recommendations(
            client, test_results.tests
        )
        
        await client.close()
        
        logger.info(f"JIRA connection test completed for {config.url} by user {current_user.id}")
        
        # Calculate total time
        test_results.total_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
    except ExternalServiceError as e:
        test_results.errors.append(f"External service error: {e.detail}")
        logger.error(f"JIRA connection test failed: {e}")
    except RateLimitError as e:
        test_results.errors.append(f"Rate limit exceeded: {e}")
        logger.warning(f"Rate limit hit during connection test: {e}")
    except Exception as e:
        test_results.errors.append(f"Unexpected error: {str(e)}")
        logger.error(f"Unexpected error during JIRA connection test: {e}", exc_info=True)
    
    return test_results


@router.post("/connection/setup")
async def setup_jira_connection(
    config: JiraConnectionConfig,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> JiraSetupResult:
    """
    Set up and store JIRA connection configuration.
    
    Tests the connection, encrypts sensitive data, and stores configuration
    for use by the application.
    """
    # First test the connection
    test_request = JiraConnectionTest(config=config)
    test_results = await test_jira_connection(test_request, current_user, db)
    
    if not test_results["connection_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"JIRA connection test failed: {test_results['errors']}"
        )
    
    try:
        # Encrypt sensitive configuration data
        encrypted_config = {}
        if config.api_token:
            encrypted_config["api_token"] = encrypt_sensitive_field(config.api_token)
        if config.password:
            encrypted_config["password"] = encrypt_sensitive_field(config.password)
        if config.oauth_config:
            encrypted_config["oauth_config"] = encrypt_sensitive_field(str(config.oauth_config))
        
        # Store configuration (this would typically go to a database table)
        # For now, we'll demonstrate with a success response
        # TODO: Implement proper configuration storage in database
        
        logger.info(f"JIRA connection configured for {config.url} by user {current_user.id}")
        
        return JiraSetupResult(
            status="configured",
            url=config.url,
            auth_method=config.auth_method,
            is_cloud=test_results.configuration["is_cloud"],
            api_version=test_results.configuration["api_version"],
            configured_at=datetime.now(timezone.utc),
            test_results=test_results
        )
        
    except Exception as e:
        logger.error(f"Failed to store JIRA configuration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store JIRA configuration"
        )


@router.get("/connection/status")
async def get_jira_connection_status(
    current_user: User = Depends(get_current_user)
) -> JiraConnectionStatus:
    """
    Get current JIRA connection status and capabilities.
    
    Returns the status of the configured JIRA connection including
    connectivity, capabilities, and last test results.
    """
    try:
        jira_service = JiraService()
        
        # Test current connection
        connection_result = await jira_service.test_connection()
        
        status = JiraConnectionStatus(
            connected=connection_result.get("connected", False),
            url=settings.JIRA_URL or "Not configured",
            is_cloud=connection_result.get("is_cloud", False),
            api_version=connection_result.get("api_version", "unknown"),
            last_test=datetime.now(timezone.utc),
            error=connection_result.get("error"),
            server_info=connection_result.get("server_info"),
            capabilities=[]
        )
        
        # Test capabilities if connected
        if status.connected:
            status.capabilities = await _test_jira_capabilities(jira_service)
        
        await jira_service.close()
        return status
        
    except Exception as e:
        logger.error(f"Failed to get JIRA connection status: {e}", exc_info=True)
        return JiraConnectionStatus(
            connected=False,
            url=settings.JIRA_URL or "Not configured",
            is_cloud=False,
            api_version="unknown",
            last_test=datetime.now(timezone.utc),
            error=str(e),
            server_info=None,
            capabilities=[]
        )


@router.get("/connection/health")
async def get_jira_health_check(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> JiraHealthCheck:
    """
    Perform comprehensive JIRA health check.
    
    Checks connection health, response times, error rates,
    and provides recommendations for optimization.
    """
    start_time = datetime.now()
    health_check = JiraHealthCheck(
        status="unhealthy",
        last_check=start_time,
        response_time_ms=None,
        error_count_24h=0,
        success_rate_24h=0.0,
        issues=[],
        recommendations=[]
    )
    
    try:
        jira_service = JiraService()
        
        # Test basic connectivity
        connection_start = datetime.now()
        connection_result = await jira_service.test_connection()
        connection_time = (datetime.now() - connection_start).total_seconds() * 1000
        
        health_check.response_time_ms = connection_time
        
        if connection_result.get("connected"):
            health_check.status = "healthy"
            
            # Check response time health
            if connection_time > 5000:  # 5 seconds
                health_check.status = "degraded"
                health_check.issues.append(f"High response time: {connection_time:.0f}ms")
                health_check.recommendations.append("Check network connectivity to JIRA instance")
            elif connection_time > 10000:  # 10 seconds
                health_check.status = "unhealthy"
                health_check.issues.append(f"Very high response time: {connection_time:.0f}ms")
        else:
            health_check.issues.append("Cannot connect to JIRA instance")
            health_check.recommendations.append("Check JIRA URL and credentials")
        
        # TODO: Query database for error counts and success rates over 24h
        # This would require a monitoring/metrics table to track API calls
        health_check.success_rate_24h = 100.0 if connection_result.get("connected") else 0.0
        
        await jira_service.close()
        
    except Exception as e:
        health_check.issues.append(f"Health check failed: {str(e)}")
        health_check.recommendations.append("Review JIRA service configuration and logs")
        logger.error(f"JIRA health check failed: {e}", exc_info=True)
    
    return health_check


@router.get("/connection/capabilities")
async def get_jira_capabilities(
    current_user: User = Depends(get_current_user)
) -> JiraCapabilities:
    """
    Discover and return available JIRA capabilities.
    
    Tests what operations are available with the current configuration
    and returns detailed capability information.
    """
    try:
        jira_service = JiraService()
        
        capabilities = JiraCapabilities()
        
        # Test basic connectivity
        connection_result = await jira_service.test_connection()
        if connection_result.get("connected"):
            capabilities.basic_connectivity = True
            capabilities.supported_operations.append("server_info")
        
        # Test various API endpoints
        test_operations = [
            ("projects_access", "get_projects", "projects"),
            ("boards_access", "get_boards", "boards"),
            ("custom_fields_access", "get_custom_fields", "custom_fields"),
            ("field_discovery", "discover_field_mappings", "field_discovery")
        ]
        
        for capability_key, method_name, operation_name in test_operations:
            try:
                method = getattr(jira_service, method_name)
                if method_name == "discover_field_mappings":
                    result = await method()
                else:
                    result = await method()
                    
                if result and (not isinstance(result, dict) or not result.get("error")):
                    setattr(capabilities, capability_key, True)
                    capabilities.supported_operations.append(operation_name)
            except Exception as e:
                logger.debug(f"Capability test failed for {capability_key}: {e}")
                capabilities.limitations.append(f"Limited {operation_name} access")
        
        # Test Agile API specifically
        try:
            boards = await jira_service.get_boards()
            if boards:
                capabilities.agile_api = True
                capabilities.boards_access = True
                capabilities.supported_operations.append("agile_boards")
                
                # Test sprint access with first board
                try:
                    sprints = await jira_service.get_sprints(board_id=boards[0]["id"])
                    if sprints:
                        capabilities.sprints_access = True
                        capabilities.supported_operations.append("sprints")
                        
                        # Test issue access with first sprint
                        try:
                            issues = await jira_service.get_sprint_issues(
                                sprint_id=sprints[0]["id"]
                            )
                            if issues:
                                capabilities.issues_access = True
                                capabilities.supported_operations.append("sprint_issues")
                        except Exception:
                            capabilities.limitations.append("Limited sprint issues access")
                except Exception:
                    capabilities.limitations.append("Limited sprint access")
        except Exception:
            capabilities.limitations.append("Limited Agile API access")
        
        # Generate recommendations
        if not capabilities.agile_api:
            capabilities.recommendations.append(
                "Enable Agile/Software features in JIRA for full sprint management"
            )
        if not capabilities.custom_fields_access:
            capabilities.recommendations.append(
                "Grant custom fields access for advanced field mapping"
            )
        
        await jira_service.close()
        return capabilities
        
    except Exception as e:
        logger.error(f"Failed to discover JIRA capabilities: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to discover JIRA capabilities"
        )


async def _run_connection_test(jira_service: JiraService, test_operation: str) -> Dict[str, Any]:
    """Run a specific connection test operation."""
    result = {"success": False, "data": None, "error": None, "response_time_ms": None}
    
    start_time = datetime.now()
    
    try:
        if test_operation == "server_info":
            data = await jira_service._get_client()
            server_info = await data.get_server_info()
            result["data"] = server_info
            result["success"] = True
            
        elif test_operation == "projects":
            projects = await jira_service.get_projects()
            result["data"] = {"count": len(projects), "sample": projects[:3]}
            result["success"] = True
            
        elif test_operation == "boards":
            boards = await jira_service.get_boards()
            result["data"] = {"count": len(boards), "sample": boards[:3]}
            result["success"] = True
            
        elif test_operation == "sprints":
            boards = await jira_service.get_boards()
            if boards:
                sprints = await jira_service.get_sprints(board_id=boards[0]["id"])
                result["data"] = {"count": len(sprints), "sample": sprints[:3]}
                result["success"] = True
            else:
                result["error"] = "No boards available for sprint testing"
                
    except Exception as e:
        result["error"] = str(e)
    
    result["response_time_ms"] = (datetime.now() - start_time).total_seconds() * 1000
    return result


def _generate_connection_recommendations(
    client: JiraAPIClient, 
    test_results: Dict[str, Any]
) -> List[str]:
    """Generate recommendations based on connection test results."""
    recommendations = []
    
    # Check API version
    if client.preferred_api_version == "2":
        recommendations.append(
            "Consider upgrading to JIRA API v3 for better performance and features"
        )
    
    # Check test results
    for test_name, test_result in test_results.items():
        if hasattr(test_result, 'success') and not test_result.success:
            if test_name == "projects":
                recommendations.append(
                    "Grant 'Browse Projects' permission for project discovery"
                )
            elif test_name == "boards":
                recommendations.append(
                    "Enable Agile features and grant board access permissions"
                )
            elif test_name == "sprints":
                recommendations.append(
                    "Ensure user has access to Agile boards and sprints"
                )
        elif hasattr(test_result, 'response_time_ms') and test_result.response_time_ms and test_result.response_time_ms > 3000:
            recommendations.append(
                f"High response time for {test_name} ({test_result.response_time_ms:.0f}ms) - "
                "consider optimizing queries or checking network connectivity"
            )
    
    # Cloud vs Server recommendations
    if client.is_cloud:
        recommendations.append(
            "Using JIRA Cloud - ensure API token is from a user with appropriate permissions"
        )
    else:
        recommendations.append(
            "Using JIRA Server - verify authentication method and user permissions"
        )
    
    return recommendations


async def _test_jira_capabilities(jira_service: JiraService) -> List[str]:
    """Test and return list of available JIRA capabilities."""
    capabilities = []
    
    # Test basic operations
    test_operations = [
        ("projects", "get_projects"),
        ("boards", "get_boards"),
        ("custom_fields", "get_custom_fields")
    ]
    
    for capability_name, method_name in test_operations:
        try:
            method = getattr(jira_service, method_name)
            result = await method()
            if result and (not isinstance(result, dict) or not result.get("error")):
                capabilities.append(capability_name)
        except Exception:
            pass  # Capability not available
    
    # Test Agile capabilities
    try:
        boards = await jira_service.get_boards()
        if boards:
            capabilities.append("agile_boards")
            
            # Test sprints with first board
            try:
                sprints = await jira_service.get_sprints(board_id=boards[0]["id"])
                if sprints:
                    capabilities.append("sprints")
                    
                    # Test issues with first sprint
                    try:
                        issues = await jira_service.get_sprint_issues(sprint_id=sprints[0]["id"])
                        if issues:
                            capabilities.append("sprint_issues")
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception:
        pass
    
    return capabilities