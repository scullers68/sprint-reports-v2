"""
Request/response validation framework.

Provides utilities for validating API requests, responses, and data models
with comprehensive error handling and validation reporting.
"""

from typing import Any, Dict, List, Optional, Type, Union
from datetime import datetime
import re

from pydantic import BaseModel, ValidationError, validator
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)


class ValidationResult:
    """
    Result object for validation operations.
    
    Contains validation status, errors, and validated data.
    """
    
    def __init__(self, is_valid: bool, data: Any = None, errors: List[str] = None):
        self.is_valid = is_valid
        self.data = data
        self.errors = errors or []
    
    def add_error(self, error: str) -> None:
        """Add an error to the validation result."""
        self.errors.append(error)
        self.is_valid = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary."""
        return {
            "is_valid": self.is_valid,
            "data": self.data,
            "errors": self.errors
        }


class BaseValidator:
    """
    Base class for custom validators.
    
    Provides common validation utilities and error handling.
    """
    
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.logger = get_logger(self.__class__.__name__)
    
    def validate_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def validate_date_range(self, start_date: datetime, end_date: datetime) -> bool:
        """Validate that start_date is before end_date."""
        return start_date < end_date
    
    def validate_positive_integer(self, value: int) -> bool:
        """Validate that integer is positive."""
        return isinstance(value, int) and value > 0
    
    def validate_non_empty_string(self, value: str) -> bool:
        """Validate that string is not empty or whitespace only."""
        return isinstance(value, str) and value.strip() != ""


class RequestValidator(BaseValidator):
    """
    Validator for API request data.
    
    Provides validation for common request patterns and business rules.
    """
    
    async def validate_model(self, model_class: Type[BaseModel], data: Dict[str, Any]) -> ValidationResult:
        """
        Validate data against a Pydantic model.
        
        Args:
            model_class: Pydantic model class to validate against
            data: Data dictionary to validate
            
        Returns:
            ValidationResult: Validation result with errors or validated data
        """
        try:
            validated_data = model_class(**data)
            self.logger.info(
                "Model validation successful",
                model_class=model_class.__name__,
                data_keys=list(data.keys())
            )
            return ValidationResult(is_valid=True, data=validated_data)
        except ValidationError as e:
            errors = []
            for error in e.errors():
                field = " -> ".join(str(loc) for loc in error["loc"])
                message = error["msg"]
                errors.append(f"{field}: {message}")
            
            self.logger.warning(
                "Model validation failed",
                model_class=model_class.__name__,
                errors=errors,
                data_keys=list(data.keys())
            )
            return ValidationResult(is_valid=False, errors=errors)
    
    async def validate_unique_field(self, model_class: Any, field_name: str, 
                                  value: Any, exclude_id: Optional[int] = None) -> ValidationResult:
        """
        Validate that a field value is unique in the database.
        
        Args:
            model_class: SQLAlchemy model class
            field_name: Field name to check for uniqueness
            value: Value to check
            exclude_id: Optional ID to exclude from uniqueness check (for updates)
            
        Returns:
            ValidationResult: Validation result
        """
        if not self.db:
            return ValidationResult(is_valid=False, errors=["Database session not available"])
        
        try:
            from sqlalchemy import select
            
            query = select(model_class).where(getattr(model_class, field_name) == value)
            if exclude_id:
                query = query.where(model_class.id != exclude_id)
            
            result = await self.db.execute(query)
            existing = result.scalar_one_or_none()
            
            if existing:
                error = f"{field_name} '{value}' already exists"
                self.logger.warning(
                    "Uniqueness validation failed",
                    model_class=model_class.__name__,
                    field_name=field_name,
                    value=value
                )
                return ValidationResult(is_valid=False, errors=[error])
            
            return ValidationResult(is_valid=True)
        except Exception as e:
            self.logger.error(
                "Error during uniqueness validation",
                model_class=model_class.__name__,
                field_name=field_name,
                error=str(e)
            )
            return ValidationResult(is_valid=False, errors=[f"Validation error: {str(e)}"])


class ResponseValidator(BaseValidator):
    """
    Validator for API response data.
    
    Ensures response data meets expected formats and business rules.
    """
    
    def validate_response_model(self, model_class: Type[BaseModel], data: Any) -> ValidationResult:
        """
        Validate response data against a Pydantic model.
        
        Args:
            model_class: Pydantic model class to validate against
            data: Data to validate
            
        Returns:
            ValidationResult: Validation result
        """
        try:
            # Handle list responses
            if isinstance(data, list):
                validated_items = []
                for item in data:
                    if isinstance(item, dict):
                        validated_items.append(model_class(**item))
                    else:
                        validated_items.append(item)
                return ValidationResult(is_valid=True, data=validated_items)
            
            # Handle single item responses
            if isinstance(data, dict):
                validated_data = model_class(**data)
                return ValidationResult(is_valid=True, data=validated_data)
            
            # Data is already a model instance
            return ValidationResult(is_valid=True, data=data)
            
        except ValidationError as e:
            errors = []
            for error in e.errors():
                field = " -> ".join(str(loc) for loc in error["loc"])
                message = error["msg"]
                errors.append(f"{field}: {message}")
            
            self.logger.error(
                "Response validation failed",
                model_class=model_class.__name__,
                errors=errors
            )
            return ValidationResult(is_valid=False, errors=errors)


def validate_request_data(data: Dict[str, Any], model_class: Type[BaseModel]) -> BaseModel:
    """
    Validate request data and raise HTTPException if invalid.
    
    Args:
        data: Request data to validate
        model_class: Pydantic model to validate against
        
    Returns:
        BaseModel: Validated model instance
        
    Raises:
        HTTPException: If validation fails
    """
    try:
        return model_class(**data)
    except ValidationError as e:
        errors = []
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            errors.append(f"{field}: {message}")
        
        logger.warning(
            "Request validation failed",
            model_class=model_class.__name__,
            errors=errors
        )
        
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Validation failed",
                "errors": errors,
                "type": "validation_error"
            }
        )


def validate_pagination_params(skip: int = 0, limit: int = 100, max_limit: int = 1000) -> None:
    """
    Validate pagination parameters.
    
    Args:
        skip: Number of items to skip
        limit: Number of items to return
        max_limit: Maximum allowed limit
        
    Raises:
        HTTPException: If parameters are invalid
    """
    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skip parameter must be non-negative"
        )
    
    if limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit parameter must be positive"
        )
    
    if limit > max_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limit parameter cannot exceed {max_limit}"
        )


class ValidationError(Exception):
    """Custom validation error for business logic validation."""
    
    def __init__(self, message: str, field: Optional[str] = None, code: Optional[str] = None):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(message)