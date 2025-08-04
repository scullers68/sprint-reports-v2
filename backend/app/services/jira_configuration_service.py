"""
JIRA Configuration Service for managing JIRA connection configurations.

Provides CRUD operations, connection testing, validation, and monitoring
for JIRA configurations with proper encryption and error handling.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import ExternalServiceError, ValidationError, SprintReportsException
from app.core.logging import get_logger
from app.models.jira_configuration import JiraConfiguration
from app.enums import JiraInstanceType, JiraAuthMethod, ConnectionStatus
from app.schemas.jira import (
    JiraConnectionConfig,
    JiraConnectionTest,
    JiraConnectionTestResult
)
from app.services.jira_service import JiraService, JiraAPIClient

logger = get_logger(__name__)


class JiraConfigurationService:
    """
    Service for managing JIRA configurations with CRUD operations,
    connection testing, encryption, and comprehensive error handling.
    
    Follows existing service patterns and architectural guidelines.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize JIRA Configuration Service.
        
        Args:
            db: Async database session
        """
        self.db = db
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    async def create_configuration(
        self,
        config: JiraConnectionConfig,
        name: str,
        description: Optional[str] = None,
        user_id: Optional[int] = None,
        environment: str = "production",
        test_connection: bool = True
    ) -> JiraConfiguration:
        """
        Create a new JIRA configuration with validation and testing.
        
        Args:
            config: JIRA connection configuration
            name: Configuration name
            description: Optional description
            user_id: ID of user creating the configuration
            environment: Environment (dev, staging, production)
            test_connection: Whether to test connection before saving
            
        Returns:
            Created JIRA configuration
            
        Raises:
            ValidationError: If configuration is invalid
            ExternalServiceError: If connection test fails
            SprintReportsException: If database operation fails
        """
        try:
            self.logger.info(f"Creating JIRA configuration '{name}' for environment '{environment}'")
            
            # Test connection first if requested
            if test_connection:
                test_result = await self._test_configuration_connection(config)
                if not test_result.connection_valid:
                    error_msg = f"Connection test failed: {', '.join(test_result.errors)}"
                    self.logger.error(f"Configuration creation failed - {error_msg}")
                    raise ExternalServiceError("JIRA", error_msg)
            
            # Auto-detect instance type if not specified
            instance_type = config.is_cloud
            if instance_type is None:
                instance_type = self._detect_instance_type(config.url)
            
            # Create configuration model
            auth_method_value = config.auth_method.value
            status_value = ConnectionStatus.ACTIVE.value if test_connection else ConnectionStatus.PENDING.value
            instance_type_value = JiraInstanceType.CLOUD.value if instance_type else JiraInstanceType.SERVER.value
            
            jira_config = JiraConfiguration(
                name=name,
                description=description,
                url=config.url,
                instance_type=instance_type_value,
                auth_method=auth_method_value,
                email=config.email,
                username=config.username,
                created_by_user_id=user_id,
                environment=environment,
                status=status_value
            )
            
            # Set encrypted credentials using properties
            if config.api_token:
                jira_config.api_token = config.api_token
            if config.password:
                jira_config.password = config.password
            if config.oauth_config:
                jira_config.oauth_config = config.oauth_config
            
            # Handle default configuration logic
            if await self._should_set_as_default(environment):
                jira_config.is_default = True
                # Unset other defaults for this environment
                await self._unset_other_defaults(environment)
            
            # Save to database
            self.db.add(jira_config)
            await self.db.commit()
            await self.db.refresh(jira_config)
            
            self.logger.info(f"Successfully created JIRA configuration {jira_config.id} '{name}'")
            return jira_config
            
        except ExternalServiceError:
            await self.db.rollback()
            raise
        except IntegrityError as e:
            await self.db.rollback()
            self.logger.error(f"Database integrity error creating configuration: {e}")
            raise ValidationError(f"Configuration with name '{name}' already exists")
        except SQLAlchemyError as e:
            await self.db.rollback()
            self.logger.error(f"Database error creating configuration: {e}")
            raise SprintReportsException("Failed to create JIRA configuration")
        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"Unexpected error creating configuration: {e}", exc_info=True)
            raise SprintReportsException("Unexpected error creating JIRA configuration")
    
    async def get_configuration(self, config_id: int) -> Optional[JiraConfiguration]:
        """
        Get JIRA configuration by ID.
        
        Args:
            config_id: Configuration ID
            
        Returns:
            JIRA configuration or None if not found
            
        Raises:
            SprintReportsException: If database operation fails
        """
        try:
            self.logger.debug(f"Retrieving JIRA configuration {config_id}")
            
            result = await self.db.execute(
                select(JiraConfiguration).where(JiraConfiguration.id == config_id)
            )
            config = result.scalar_one_or_none()
            
            if config:
                self.logger.debug(f"Found JIRA configuration {config_id}")
            else:
                self.logger.debug(f"JIRA configuration {config_id} not found")
            
            return config
            
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving configuration {config_id}: {e}")
            raise SprintReportsException(f"Failed to retrieve JIRA configuration {config_id}")
    
    async def get_configurations(
        self,
        environment: Optional[str] = None,
        status: Optional[ConnectionStatus] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[JiraConfiguration]:
        """
        Get JIRA configurations with filtering.
        
        Args:
            environment: Filter by environment
            status: Filter by connection status
            is_active: Filter by active status
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of JIRA configurations
            
        Raises:
            SprintReportsException: If database operation fails
        """
        try:
            self.logger.debug(
                f"Retrieving JIRA configurations - env: {environment}, "
                f"status: {status}, active: {is_active}, limit: {limit}, offset: {offset}"
            )
            
            query = select(JiraConfiguration)
            
            # Apply filters
            filters = []
            if environment is not None:
                filters.append(JiraConfiguration.environment == environment)
            if status is not None:
                filters.append(JiraConfiguration.status == status)
            if is_active is not None:
                filters.append(JiraConfiguration.is_active == is_active)
            
            if filters:
                query = query.where(and_(*filters))
            
            # Apply ordering, limit, and offset
            query = query.order_by(
                JiraConfiguration.is_default.desc(),
                JiraConfiguration.created_at.desc()
            ).limit(limit).offset(offset)
            
            result = await self.db.execute(query)
            configurations = result.scalars().all()
            
            self.logger.debug(f"Found {len(configurations)} JIRA configurations")
            return list(configurations)
            
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving configurations: {e}")
            raise SprintReportsException("Failed to retrieve JIRA configurations")
    
    async def get_default_configuration(
        self, 
        environment: str = "production"
    ) -> Optional[JiraConfiguration]:
        """
        Get the default JIRA configuration for an environment.
        
        Args:
            environment: Environment to get default for
            
        Returns:
            Default JIRA configuration or None if not found
            
        Raises:
            SprintReportsException: If database operation fails
        """
        try:
            self.logger.debug(f"Retrieving default JIRA configuration for environment '{environment}'")
            
            result = await self.db.execute(
                select(JiraConfiguration).where(
                    and_(
                        JiraConfiguration.is_default == True,
                        JiraConfiguration.environment == environment,
                        JiraConfiguration.is_active == True
                    )
                )
            )
            config = result.scalar_one_or_none()
            
            if config:
                self.logger.debug(f"Found default configuration {config.id} for environment '{environment}'")
            else:
                self.logger.debug(f"No default configuration found for environment '{environment}'")
            
            return config
            
        except SQLAlchemyError as e:
            self.logger.error(f"Database error retrieving default configuration: {e}")
            raise SprintReportsException("Failed to retrieve default JIRA configuration")
    
    async def update_configuration(
        self,
        config_id: int,
        updates: Dict[str, Any],
        test_connection: bool = True
    ) -> Optional[JiraConfiguration]:
        """
        Update JIRA configuration with validation and testing.
        
        Args:
            config_id: Configuration ID to update
            updates: Dictionary of fields to update
            test_connection: Whether to test connection after update
            
        Returns:
            Updated configuration or None if not found
            
        Raises:
            ValidationError: If update data is invalid
            ExternalServiceError: If connection test fails
            SprintReportsException: If database operation fails
        """
        try:
            self.logger.info(f"Updating JIRA configuration {config_id}")
            
            # Get existing configuration
            config = await self.get_configuration(config_id)
            if not config:
                self.logger.warning(f"Configuration {config_id} not found for update")
                return None
            
            # Test connection if credentials or URL changed and testing is enabled
            if test_connection and self._requires_connection_test(updates):
                # Create temporary config for testing
                test_config = self._create_test_config_from_updates(config, updates)
                test_result = await self._test_configuration_connection(test_config)
                
                if not test_result.connection_valid:
                    error_msg = f"Connection test failed: {', '.join(test_result.errors)}"
                    self.logger.error(f"Configuration update failed - {error_msg}")
                    raise ExternalServiceError("JIRA", error_msg)
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                else:
                    self.logger.warning(f"Ignoring unknown field '{key}' in update")
            
            # Handle default configuration changes
            if updates.get('is_default'):
                await self._unset_other_defaults(config.environment, exclude_id=config_id)
            
            # Update timestamp
            config.updated_at = datetime.now(timezone.utc)
            
            await self.db.commit()
            await self.db.refresh(config)
            
            self.logger.info(f"Successfully updated JIRA configuration {config_id}")
            return config
            
        except (ExternalServiceError, ValidationError):
            await self.db.rollback()
            raise
        except SQLAlchemyError as e:
            await self.db.rollback()
            self.logger.error(f"Database error updating configuration {config_id}: {e}")
            raise SprintReportsException(f"Failed to update JIRA configuration {config_id}")
        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"Unexpected error updating configuration {config_id}: {e}", exc_info=True)
            raise SprintReportsException("Unexpected error updating JIRA configuration")
    
    async def delete_configuration(self, config_id: int) -> bool:
        """
        Delete JIRA configuration.
        
        Args:
            config_id: Configuration ID to delete
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            ValidationError: If trying to delete the last active configuration
            SprintReportsException: If database operation fails
        """
        try:
            self.logger.info(f"Deleting JIRA configuration {config_id}")
            
            # Check if configuration exists
            config = await self.get_configuration(config_id)
            if not config:
                self.logger.warning(f"Configuration {config_id} not found for deletion")
                return False
            
            # Check if this is the last active configuration
            active_count = await self._count_active_configurations(config.environment)
            if active_count <= 1 and config.is_active:
                self.logger.error(f"Cannot delete last active configuration {config_id}")
                raise ValidationError("Cannot delete the last active JIRA configuration")
            
            # Perform soft delete by setting inactive
            config.is_active = False
            config.status = ConnectionStatus.INACTIVE
            config.updated_at = datetime.now(timezone.utc)
            
            await self.db.commit()
            
            self.logger.info(f"Successfully deleted (deactivated) JIRA configuration {config_id}")
            return True
            
        except ValidationError:
            await self.db.rollback()
            raise
        except SQLAlchemyError as e:
            await self.db.rollback()
            self.logger.error(f"Database error deleting configuration {config_id}: {e}")
            raise SprintReportsException(f"Failed to delete JIRA configuration {config_id}")
    
    async def test_configuration_connection(
        self, 
        config_id: int,
        update_status: bool = True
    ) -> JiraConnectionTestResult:
        """
        Test connection for existing JIRA configuration.
        
        Args:
            config_id: Configuration ID to test
            update_status: Whether to update configuration status based on test
            
        Returns:
            Connection test result
            
        Raises:
            SprintReportsException: If configuration not found or database error
        """
        try:
            self.logger.info(f"Testing connection for JIRA configuration {config_id}")
            
            config = await self.get_configuration(config_id)
            if not config:
                raise SprintReportsException(f"JIRA configuration {config_id} not found")
            
            # Create connection config for testing
            # Ensure auth_method is properly converted to enum
            if isinstance(config.auth_method, str):
                auth_method = JiraAuthMethod(config.auth_method)
            else:
                auth_method = config.auth_method
            
            connection_config = JiraConnectionConfig(
                url=config.url,
                auth_method=auth_method,
                email=config.email,
                api_token=config.api_token,
                username=config.username,
                password=config.password,
                oauth_config=config.oauth_config,
                is_cloud=config.is_cloud_instance()
            )
            
            # Test connection
            test_result = await self._test_configuration_connection(connection_config)
            
            # Update configuration status if requested
            if update_status:
                if test_result.connection_valid:
                    config.record_successful_test(
                        int(test_result.total_time_ms) if test_result.total_time_ms else None
                    )
                else:
                    error_message = "; ".join(test_result.errors) if test_result.errors else "Unknown error"
                    config.record_failed_test(error_message)
                
                await self.db.commit()
                self.logger.info(f"Updated configuration {config_id} status based on test result")
            
            return test_result
            
        except SQLAlchemyError as e:
            self.logger.error(f"Database error testing configuration {config_id}: {e}")
            raise SprintReportsException(f"Failed to test JIRA configuration {config_id}")
    
    async def monitor_configurations(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        Monitor health and status of JIRA configurations.
        
        Args:
            environment: Optional environment filter
            
        Returns:
            Monitoring summary with health metrics
            
        Raises:
            SprintReportsException: If database operation fails
        """
        try:
            self.logger.debug(f"Monitoring JIRA configurations for environment: {environment}")
            
            # Get configurations to monitor
            configs = await self.get_configurations(
                environment=environment,
                is_active=True
            )
            
            monitoring_data = {
                "total_configurations": len(configs),
                "healthy_count": 0,
                "error_count": 0,
                "inactive_count": 0,
                "configurations": [],
                "environment": environment,
                "timestamp": datetime.now(timezone.utc)
            }
            
            for config in configs:
                config_status = {
                    "id": config.id,
                    "name": config.name,
                    "url": config.url,
                    "status": config.status.value,
                    "is_healthy": config.is_healthy(),
                    "last_tested": config.last_tested_at,
                    "consecutive_errors": config.consecutive_errors,
                    "avg_response_time_ms": config.avg_response_time_ms
                }
                
                monitoring_data["configurations"].append(config_status)
                
                # Update counters
                if config.is_healthy():
                    monitoring_data["healthy_count"] += 1
                elif config.status == ConnectionStatus.ERROR:
                    monitoring_data["error_count"] += 1
                else:
                    monitoring_data["inactive_count"] += 1
            
            # Calculate health percentage
            if monitoring_data["total_configurations"] > 0:
                monitoring_data["health_percentage"] = (
                    monitoring_data["healthy_count"] / monitoring_data["total_configurations"] * 100
                )
            else:
                monitoring_data["health_percentage"] = 0
            
            self.logger.debug(f"Monitoring complete: {monitoring_data['health_percentage']:.1f}% healthy")
            return monitoring_data
            
        except SQLAlchemyError as e:
            self.logger.error(f"Database error monitoring configurations: {e}")
            raise SprintReportsException("Failed to monitor JIRA configurations")
    
    # Private helper methods
    
    def _detect_instance_type(self, url: str) -> bool:
        """Detect if JIRA instance is Cloud (True) or Server (False)."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.hostname and parsed.hostname.endswith('.atlassian.net')
    
    async def _test_configuration_connection(
        self, 
        config: JiraConnectionConfig
    ) -> JiraConnectionTestResult:
        """Test JIRA configuration connection."""
        from app.schemas.jira import JiraConnectionTest
        
        test_request = JiraConnectionTest(
            config=config,
            test_operations=["server_info", "projects"]
        )
        
        # Use JiraService to perform the actual test
        # This reuses existing connection testing logic
        try:
            client = JiraAPIClient(
                url=config.url,
                auth_method=config.auth_method.value,
                email=config.email,
                api_token=config.api_token,
                username=config.username,
                password=config.password,
                oauth_dict=config.oauth_config,
                cloud=config.is_cloud
            )
            
            start_time = datetime.now()
            connection_valid = await client.test_connection()
            end_time = datetime.now()
            
            test_result = JiraConnectionTestResult(
                connection_valid=connection_valid,
                configuration={
                    "url": config.url,
                    "auth_method": config.auth_method.value,
                    "is_cloud": client.is_cloud,
                    "api_version": client.preferred_api_version
                },
                tests={},
                errors=[] if connection_valid else ["Connection test failed"],
                recommendations=[],
                total_time_ms=(end_time - start_time).total_seconds() * 1000
            )
            
            await client.close()
            return test_result
            
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return JiraConnectionTestResult(
                connection_valid=False,
                configuration={
                    "url": config.url,
                    "auth_method": config.auth_method.value,
                    "is_cloud": None,
                    "api_version": None
                },
                tests={},
                errors=[str(e)],
                recommendations=[]
            )
    
    async def _should_set_as_default(self, environment: str) -> bool:
        """Check if this should be set as the default configuration."""
        result = await self.db.execute(
            select(func.count(JiraConfiguration.id)).where(
                and_(
                    JiraConfiguration.environment == environment,
                    JiraConfiguration.is_active == True
                )
            )
        )
        count = result.scalar()
        return count == 0  # Set as default if it's the first active config
    
    async def _unset_other_defaults(self, environment: str, exclude_id: Optional[int] = None) -> None:
        """Unset default flag for other configurations in the same environment."""
        query = update(JiraConfiguration).where(
            and_(
                JiraConfiguration.environment == environment,
                JiraConfiguration.is_default == True
            )
        ).values(is_default=False)
        
        if exclude_id:
            query = query.where(JiraConfiguration.id != exclude_id)
        
        await self.db.execute(query)
    
    def _requires_connection_test(self, updates: Dict[str, Any]) -> bool:
        """Check if updates require a connection test."""
        test_required_fields = [
            'url', 'auth_method', 'email', 'api_token', 
            'username', 'password', 'oauth_config'
        ]
        return any(field in updates for field in test_required_fields)
    
    def _create_test_config_from_updates(
        self, 
        config: JiraConfiguration, 
        updates: Dict[str, Any]
    ) -> JiraConnectionConfig:
        """Create a test configuration from existing config plus updates."""
        # Get auth method value, handling both string and enum cases
        auth_method_value = updates.get('auth_method', config.auth_method)
        if isinstance(auth_method_value, str):
            auth_method = JiraAuthMethod(auth_method_value)
        else:
            auth_method = auth_method_value
        
        return JiraConnectionConfig(
            url=updates.get('url', config.url),
            auth_method=auth_method,
            email=updates.get('email', config.email),
            api_token=updates.get('api_token', config.api_token),
            username=updates.get('username', config.username),
            password=updates.get('password', config.password),
            oauth_config=updates.get('oauth_config', config.oauth_config),
            is_cloud=config.is_cloud_instance()
        )
    
    async def _count_active_configurations(self, environment: str) -> int:
        """Count active configurations in environment."""
        result = await self.db.execute(
            select(func.count(JiraConfiguration.id)).where(
                and_(
                    JiraConfiguration.environment == environment,
                    JiraConfiguration.is_active == True
                )
            )
        )
        return result.scalar()