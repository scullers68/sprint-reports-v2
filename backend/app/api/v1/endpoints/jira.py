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
from app.core.exceptions import ExternalServiceError, RateLimitError, ValidationError, SprintReportsException
from app.models.user import User
from app.schemas.jira import (
    JiraConnectionConfig, JiraConnectionTest, JiraConnectionTestResult,
    JiraConnectionStatus, JiraHealthCheck, JiraCapabilities, JiraSetupResult,
    JiraConfigurationCreate, JiraConfigurationUpdate, JiraConfigurationResponse,
    JiraConfigurationList, JiraConfigurationTestRequest, JiraConfigurationStatusFilter,
    JiraConfigurationMonitoringResponse
)
from app.core.security import get_current_user
from app.services.jira_service import JiraService, JiraAPIClient
from app.services.jira_configuration_service import JiraConfigurationService

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


@router.get("/projects")
async def discover_projects(
    search: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Discover and list all accessible JIRA projects with filtering and permissions.
    
    Args:
        search: Optional search term to filter projects by name or key
        limit: Maximum number of projects to return (default 50)
    
    Returns:
        List of JIRA projects with metadata and permission information
    """
    try:
        # For now, we'll need to get the connection details from somewhere
        # This is a temporary fix - in production, you'd store the config in DB
        # and retrieve it here based on the current user
        
        # Check if we have connection details in the request headers or session
        # For testing, we'll use environment variables as fallback
        from app.core.config import settings
        
        if not settings.JIRA_URL or not settings.JIRA_API_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JIRA connection not configured. Please set JIRA_URL and JIRA_API_TOKEN environment variables."
            )
        
        # Create JIRA service with connection details
        from app.services.jira_service import JiraService
        
        jira_service = JiraService(db)
        
        # Get all projects from JIRA
        all_projects = await jira_service.get_projects()
        
        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            all_projects = [
                project for project in all_projects
                if (search_lower in project.get("name", "").lower() or 
                    search_lower in project.get("key", "").lower())
            ]
        
        # Apply limit
        projects = all_projects[:limit]
        
        # Enhance project data with additional metadata
        enhanced_projects = []
        for project in projects:
            enhanced_project = {
                "id": project.get("id"),
                "key": project.get("key"),
                "name": project.get("name"),
                "projectTypeKey": project.get("projectTypeKey", "unknown"),
                "simplified": project.get("simplified", False),
                "style": project.get("style", "classic"),
                "isPrivate": project.get("isPrivate", False),
                "description": project.get("description"),
                "lead": project.get("lead"),
                "url": project.get("self"),
                "avatarUrls": project.get("avatarUrls"),
                "permissions": {
                    "browse": True,  # If we can see it, we can browse it
                    "administrate": False,  # Would need additional check
                    "create_issues": False  # Would need additional check
                },
                "board_count": 0  # Will be populated below
            }
            
            # Try to get board count for this project
            try:
                project_boards = await jira_service.get_boards(project_key=project.get("key"))
                enhanced_project["board_count"] = len(project_boards) if project_boards else 0
            except Exception as e:
                logger.debug(f"Could not get boards for project {project.get('key')}: {e}")
            
            enhanced_projects.append(enhanced_project)
        
        await jira_service.close()
        
        logger.info(f"Found {len(enhanced_projects)} projects for user {current_user.id}")
        return enhanced_projects
        
    except Exception as e:
        logger.error(f"Failed to discover JIRA projects: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover JIRA projects: {str(e)}"
        )


@router.get("/projects/{project_key}/boards")
async def discover_project_boards(
    project_key: str,
    board_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Discover and list all boards within a specific JIRA project.
    
    Args:
        project_key: JIRA project key
        board_type: Optional filter by board type (scrum, kanban)
    
    Returns:
        List of JIRA boards with configuration and sprint settings
    """
    try:
        jira_service = JiraService()
        
        # Get boards for the specific project
        boards = await jira_service.get_boards(project_key=project_key)
        
        # Apply board type filter if provided
        if board_type:
            boards = [
                board for board in boards
                if board.get("type", "").lower() == board_type.lower()
            ]
        
        # Enhance board data with additional metadata
        enhanced_boards = []
        for board in boards:
            enhanced_board = {
                "id": board.get("id"),
                "name": board.get("name"),
                "type": board.get("type"),
                "project_key": project_key,
                "self": board.get("self"),
                "location": board.get("location"),
                "configuration": {
                    "type": board.get("type", "unknown").lower(),
                    "is_scrum": board.get("type", "").lower() == "scrum",
                    "is_kanban": board.get("type", "").lower() == "kanban",
                    "supports_sprints": board.get("type", "").lower() == "scrum"
                },
                "permissions": {
                    "view": True,  # If we can see it, we can view it
                    "edit": False,  # Would need additional check
                    "admin": False  # Would need additional check
                },
                "sprint_count": 0,
                "active_sprint": None
            }
            
            # For Scrum boards, try to get sprint information
            if enhanced_board["configuration"]["is_scrum"]:
                try:
                    sprints = await jira_service.get_sprints(board_id=board.get("id"))
                    enhanced_board["sprint_count"] = len(sprints) if sprints else 0
                    
                    # Find active sprint
                    if sprints:
                        active_sprints = [s for s in sprints if s.get("state") == "ACTIVE"]
                        if active_sprints:
                            active_sprint = active_sprints[0]
                            enhanced_board["active_sprint"] = {
                                "id": active_sprint.get("id"),
                                "name": active_sprint.get("name"),
                                "goal": active_sprint.get("goal"),
                                "startDate": active_sprint.get("startDate"),
                                "endDate": active_sprint.get("endDate")
                            }
                
                except Exception as e:
                    logger.debug(f"Could not get sprints for board {board.get('id')}: {e}")
            
            enhanced_boards.append(enhanced_board)
        
        await jira_service.close()
        
        logger.info(f"Found {len(enhanced_boards)} boards for project {project_key} for user {current_user.id}")
        return enhanced_boards
        
    except Exception as e:
        logger.error(f"Failed to discover boards for project {project_key}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover boards for project {project_key}: {str(e)}"
        )


@router.get("/boards/{board_id}/configuration")
async def get_board_configuration(
    board_id: int,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get detailed configuration information for a specific JIRA board.
    
    Args:
        board_id: JIRA board ID
    
    Returns:
        Detailed board configuration including sprint settings and permissions
    """
    try:
        jira_service = JiraService()
        client = await jira_service._get_client()
        
        # Get board details
        board_endpoint = f"/rest/agile/1.0/board/{board_id}"
        board_info = await client.get(board_endpoint)
        
        configuration = {
            "id": board_info.get("id"),
            "name": board_info.get("name"),
            "type": board_info.get("type"),
            "location": board_info.get("location"),
            "self": board_info.get("self"),
            "supports_sprints": board_info.get("type", "").lower() == "scrum",
            "permissions": {
                "view_board": True,
                "view_sprints": board_info.get("type", "").lower() == "scrum",
                "create_sprints": False,  # Would need additional permission check
                "edit_board": False       # Would need additional permission check
            },
            "sprint_settings": {},
            "columns": [],
            "quick_filters": [],
            "estimation": {}
        }
        
        # Get board configuration details if available
        try:
            config_endpoint = f"/rest/agile/1.0/board/{board_id}/configuration"
            board_config = await client.get(config_endpoint)
            
            configuration["columns"] = board_config.get("columnConfig", {}).get("columns", [])
            configuration["quick_filters"] = board_config.get("filter", {}).get("quickFilters", [])
            configuration["estimation"] = board_config.get("estimation", {})
            
            # Extract sprint settings for Scrum boards
            if configuration["supports_sprints"]:
                configuration["sprint_settings"] = {
                    "default_duration": board_config.get("sprintConfig", {}).get("duration", "2 weeks"),
                    "start_day": board_config.get("sprintConfig", {}).get("startDay", "Monday"),
                    "working_days": board_config.get("sprintConfig", {}).get("workingDays", [])
                }
        
        except Exception as e:
            logger.debug(f"Could not get detailed board configuration for {board_id}: {e}")
        
        # Get recent sprints for Scrum boards
        if configuration["supports_sprints"]:
            try:
                sprints = await jira_service.get_sprints(board_id=board_id)
                configuration["recent_sprints"] = [
                    {
                        "id": sprint.get("id"),
                        "name": sprint.get("name"),
                        "state": sprint.get("state"),
                        "startDate": sprint.get("startDate"),
                        "endDate": sprint.get("endDate"),
                        "goal": sprint.get("goal")
                    }
                    for sprint in (sprints[:5] if sprints else [])  # Last 5 sprints
                ]
            except Exception as e:
                logger.debug(f"Could not get sprints for board {board_id}: {e}")
                configuration["recent_sprints"] = []
        
        await jira_service.close()
        
        logger.info(f"Retrieved board configuration for board {board_id} for user {current_user.id}")
        return configuration
        
    except Exception as e:
        logger.error(f"Failed to get board configuration for {board_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get board configuration: {str(e)}"
        )


@router.post("/projects/{project_key}/select")
async def select_project_for_sprint_import(
    project_key: str,
    board_ids: List[int],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Select a JIRA project and boards for sprint data import and persist the selection.
    
    Args:
        project_key: JIRA project key
        board_ids: List of board IDs to use for sprint import
    
    Returns:
        Selection confirmation with project and board details
    """
    try:
        jira_service = JiraService(db)
        
        # Validate project exists and is accessible
        projects = await jira_service.get_projects()
        selected_project = next(
            (p for p in projects if p.get("key") == project_key), 
            None
        )
        
        if not selected_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_key} not found or not accessible"
            )
        
        # Validate boards exist and belong to project
        validated_boards = []
        for board_id in board_ids:
            try:
                # Get board details and verify it belongs to this project
                client = await jira_service._get_client()
                board_endpoint = f"/rest/agile/1.0/board/{board_id}"
                board_info = await client.get(board_endpoint)
                
                # Check if board is associated with the project
                board_project_key = None
                if board_info.get("location", {}).get("projectKey"):
                    board_project_key = board_info["location"]["projectKey"]
                
                if board_project_key != project_key:
                    logger.warning(f"Board {board_id} does not belong to project {project_key}")
                    continue
                
                validated_boards.append({
                    "id": board_info.get("id"),
                    "name": board_info.get("name"),
                    "type": board_info.get("type"),
                    "supports_sprints": board_info.get("type", "").lower() == "scrum"
                })
                
            except Exception as e:
                logger.warning(f"Could not validate board {board_id}: {e}")
                continue
        
        if not validated_boards:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid boards found for the specified project"
            )
        
        # TODO: Store project selection in database
        # This would typically create a user preference record or project configuration
        
        selection_result = {
            "project": {
                "key": selected_project.get("key"),
                "name": selected_project.get("name"),
                "id": selected_project.get("id")
            },
            "boards": validated_boards,
            "selected_at": datetime.now(timezone.utc).isoformat(),
            "selected_by": current_user.id,
            "status": "selected",
            "next_steps": [
                "Project and boards have been selected for sprint import",
                "Use the sprint discovery endpoint to find available sprints",
                "Configure field mappings if needed",
                "Begin sprint data import process"
            ]
        }
        
        await jira_service.close()
        
        logger.info(f"User {current_user.id} selected project {project_key} with {len(validated_boards)} boards")
        return selection_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to select project {project_key}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to select project: {str(e)}"
        )


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


# JIRA Configuration Management Endpoints

@router.post("/configurations", response_model=JiraConfigurationResponse, status_code=status.HTTP_201_CREATED)
async def create_jira_configuration(
    config_data: JiraConfigurationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> JiraConfigurationResponse:
    """
    Create a new JIRA configuration with validation and testing.
    
    Creates a JIRA configuration entry, optionally tests the connection,
    and stores it securely with encrypted sensitive fields.
    """
    try:
        logger.info(f"Creating JIRA configuration '{config_data.name}' for user {current_user.id}")
        
        # Initialize configuration service
        config_service = JiraConfigurationService(db)
        
        # Create configuration with automatic testing if requested
        jira_config = await config_service.create_configuration(
            config=config_data.config,
            name=config_data.name,
            description=config_data.description,
            user_id=current_user.id,
            environment=config_data.environment,
            test_connection=config_data.test_connection
        )
        
        logger.info(f"Successfully created JIRA configuration {jira_config.id}")
        
        # Return response with masked sensitive fields
        return JiraConfigurationResponse.from_orm_with_security(jira_config)
        
    except ValidationError as e:
        logger.warning(f"Validation error creating JIRA configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except ExternalServiceError as e:
        logger.error(f"JIRA connection test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"JIRA connection test failed: {e.detail}"
        )
    except SprintReportsException as e:
        logger.error(f"Database error creating configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create JIRA configuration"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating JIRA configuration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error creating JIRA configuration"
        )


@router.get("/configurations", response_model=JiraConfigurationList)
async def list_jira_configurations(
    environment: Optional[str] = None,
    status_filter: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> JiraConfigurationList:
    """
    List JIRA configurations with filtering and pagination.
    
    Returns a paginated list of JIRA configurations with optional
    filtering by environment, status, and active state.
    """
    try:
        logger.debug(f"Listing JIRA configurations for user {current_user.id}")
        
        # Initialize configuration service
        config_service = JiraConfigurationService(db)
        
        # Parse status filter
        status_enum = None
        if status_filter:
            try:
                from app.enums import ConnectionStatus
                status_enum = ConnectionStatus(status_filter.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status filter: {status_filter}"
                )
        
        # Get configurations with filtering
        configurations = await config_service.get_configurations(
            environment=environment,
            status=status_enum,
            is_active=is_active,
            limit=limit,
            offset=offset
        )
        
        # Convert to response models
        config_responses = [
            JiraConfigurationResponse.from_orm_with_security(config)
            for config in configurations
        ]
        
        # Calculate pagination info
        total = len(config_responses)  # Note: This is simplified, in production you'd get total separately
        page = (offset // limit) + 1 if limit > 0 else 1
        has_next = len(configurations) == limit  # Simplified check
        has_previous = offset > 0
        
        logger.debug(f"Found {len(configurations)} JIRA configurations")
        
        return JiraConfigurationList(
            configurations=config_responses,
            total=total,
            page=page,
            page_size=limit,
            has_next=has_next,
            has_previous=has_previous
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing JIRA configurations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list JIRA configurations"
        )


@router.get("/configurations/{config_id}", response_model=JiraConfigurationResponse)
async def get_jira_configuration(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> JiraConfigurationResponse:
    """
    Get a specific JIRA configuration by ID.
    
    Returns detailed information about a JIRA configuration
    with sensitive fields masked for security.
    """
    try:
        logger.debug(f"Getting JIRA configuration {config_id} for user {current_user.id}")
        
        # Initialize configuration service
        config_service = JiraConfigurationService(db)
        
        # Get configuration
        jira_config = await config_service.get_configuration(config_id)
        
        if not jira_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"JIRA configuration {config_id} not found"
            )
        
        logger.debug(f"Found JIRA configuration {config_id}")
        
        # Return response with masked sensitive fields
        return JiraConfigurationResponse.from_orm_with_security(jira_config)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting JIRA configuration {config_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get JIRA configuration {config_id}"
        )


@router.put("/configurations/{config_id}", response_model=JiraConfigurationResponse)
async def update_jira_configuration(
    config_id: int,
    update_data: JiraConfigurationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> JiraConfigurationResponse:
    """
    Update an existing JIRA configuration.
    
    Updates configuration fields and optionally tests the connection
    if authentication or connection details are modified.
    """
    try:
        logger.info(f"Updating JIRA configuration {config_id} for user {current_user.id}")
        
        # Initialize configuration service
        config_service = JiraConfigurationService(db)
        
        # Prepare update dictionary excluding None values
        updates = {}
        update_dict = update_data.dict(exclude_unset=True, exclude={'config', 'test_connection'})
        
        # Handle individual field updates
        for key, value in update_dict.items():
            if value is not None:
                updates[key] = value
        
        # Handle config updates separately to properly handle nested fields
        if update_data.config:
            config_dict = update_data.config.dict(exclude_unset=True)
            for key, value in config_dict.items():
                if value is not None:
                    updates[key] = value
        
        # Update configuration
        updated_config = await config_service.update_configuration(
            config_id=config_id,
            updates=updates,
            test_connection=update_data.test_connection
        )
        
        if not updated_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"JIRA configuration {config_id} not found"
            )
        
        logger.info(f"Successfully updated JIRA configuration {config_id}")
        
        # Return response with masked sensitive fields
        return JiraConfigurationResponse.from_orm_with_security(updated_config)
        
    except HTTPException:
        raise
    except ValidationError as e:
        logger.warning(f"Validation error updating JIRA configuration {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except ExternalServiceError as e:
        logger.error(f"JIRA connection test failed for configuration {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"JIRA connection test failed: {e.detail}"
        )
    except Exception as e:
        logger.error(f"Error updating JIRA configuration {config_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update JIRA configuration {config_id}"
        )


@router.delete("/configurations/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_jira_configuration(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete (deactivate) a JIRA configuration.
    
    Performs soft delete by setting the configuration as inactive.
    Prevents deletion of the last active configuration in an environment.
    """
    try:
        logger.info(f"Deleting JIRA configuration {config_id} for user {current_user.id}")
        
        # Initialize configuration service
        config_service = JiraConfigurationService(db)
        
        # Delete configuration
        deleted = await config_service.delete_configuration(config_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"JIRA configuration {config_id} not found"
            )
        
        logger.info(f"Successfully deleted JIRA configuration {config_id}")
        
    except HTTPException:
        raise
    except ValidationError as e:
        logger.warning(f"Validation error deleting JIRA configuration {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting JIRA configuration {config_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete JIRA configuration {config_id}"
        )


@router.post("/configurations/{config_id}/test", response_model=JiraConnectionTestResult)
async def test_jira_configuration(
    config_id: int,
    update_status: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> JiraConnectionTestResult:
    """
    Test connection for a specific JIRA configuration.
    
    Tests the connection using stored configuration and optionally
    updates the configuration status based on test results.
    """
    try:
        logger.info(f"Testing JIRA configuration {config_id} for user {current_user.id}")
        
        # Initialize configuration service
        config_service = JiraConfigurationService(db)
        
        # Test configuration connection
        test_result = await config_service.test_configuration_connection(
            config_id=config_id,
            update_status=update_status
        )
        
        logger.info(f"JIRA configuration {config_id} test completed: {test_result.connection_valid}")
        
        return test_result
        
    except SprintReportsException as e:
        logger.error(f"Database error testing JIRA configuration {config_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"JIRA configuration {config_id} not found"
        )
    except Exception as e:
        logger.error(f"Error testing JIRA configuration {config_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test JIRA configuration {config_id}"
        )


@router.get("/configurations/default", response_model=JiraConfigurationResponse)
async def get_default_jira_configuration(
    environment: str = "production",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> JiraConfigurationResponse:
    """
    Get the default JIRA configuration for an environment.
    
    Returns the default JIRA configuration for the specified environment.
    """
    try:
        logger.debug(f"Getting default JIRA configuration for environment '{environment}' for user {current_user.id}")
        
        # Initialize configuration service
        config_service = JiraConfigurationService(db)
        
        # Get default configuration
        default_config = await config_service.get_default_configuration(environment)
        
        if not default_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No default JIRA configuration found for environment '{environment}'"
            )
        
        logger.debug(f"Found default JIRA configuration {default_config.id} for environment '{environment}'")
        
        # Return response with masked sensitive fields
        return JiraConfigurationResponse.from_orm_with_security(default_config)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting default JIRA configuration for environment '{environment}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get default JIRA configuration for environment '{environment}'"
        )


@router.get("/configurations/monitor", response_model=JiraConfigurationMonitoringResponse)
async def monitor_jira_configurations(
    environment: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> JiraConfigurationMonitoringResponse:
    """
    Monitor health and status of JIRA configurations.
    
    Returns comprehensive monitoring data including health metrics,
    error counts, and status summaries for JIRA configurations.
    """
    try:
        logger.debug(f"Monitoring JIRA configurations for environment '{environment}' for user {current_user.id}")
        
        # Initialize configuration service
        config_service = JiraConfigurationService(db)
        
        # Get monitoring data
        monitoring_data = await config_service.monitor_configurations(environment)
        
        logger.debug(f"Configuration monitoring complete: {monitoring_data['health_percentage']:.1f}% healthy")
        
        # Convert to response model
        return JiraConfigurationMonitoringResponse(**monitoring_data)
        
    except Exception as e:
        logger.error(f"Error monitoring JIRA configurations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to monitor JIRA configurations"
        )