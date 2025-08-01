"""
Field mapping Pydantic schemas for API request/response models.

Extends existing schema patterns for field mapping operations.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field, validator

from app.models.field_mapping import FieldType, MappingType


# Field Mapping schemas
class FieldMappingBase(BaseModel):
    """Base field mapping schema with common fields."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    jira_field_id: str = Field(..., min_length=1, max_length=100)
    jira_field_name: Optional[str] = Field(None, max_length=200)
    target_field: str = Field(..., min_length=1, max_length=100)
    field_type: FieldType = Field(default=FieldType.STRING)
    mapping_type: MappingType = Field(default=MappingType.DIRECT)
    default_value: Optional[str] = Field(None, max_length=500)
    is_required: bool = Field(default=False)
    is_active: bool = Field(default=True)
    version: str = Field(default="1.0", max_length=20)


class FieldMappingCreate(FieldMappingBase):
    """Schema for creating a new field mapping."""
    transformation_config: Optional[Dict[str, Any]] = None
    validation_rules: Optional[Dict[str, Any]] = None
    template_id: Optional[int] = None
    
    @validator('transformation_config')
    def validate_transformation_config(cls, v):
        """Validate transformation configuration."""
        if v and not isinstance(v, dict):
            raise ValueError('transformation_config must be a dictionary')
        return v
    
    @validator('validation_rules')
    def validate_validation_rules(cls, v):
        """Validate validation rules."""
        if v and not isinstance(v, dict):
            raise ValueError('validation_rules must be a dictionary')
        return v


class FieldMappingUpdate(BaseModel):
    """Schema for updating an existing field mapping."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    jira_field_name: Optional[str] = Field(None, max_length=200)
    target_field: Optional[str] = Field(None, min_length=1, max_length=100)
    field_type: Optional[FieldType] = None
    mapping_type: Optional[MappingType] = None
    transformation_config: Optional[Dict[str, Any]] = None
    validation_rules: Optional[Dict[str, Any]] = None
    default_value: Optional[str] = Field(None, max_length=500)
    is_required: Optional[bool] = None
    is_active: Optional[bool] = None


class FieldMappingRead(FieldMappingBase):
    """Schema for reading field mapping data."""
    id: int
    transformation_config: Optional[Dict[str, Any]] = None
    validation_rules: Optional[Dict[str, Any]] = None
    template_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Field Mapping Template schemas
class FieldMappingTemplateBase(BaseModel):
    """Base field mapping template schema."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    jira_project_type: Optional[str] = Field(None, max_length=100)
    organization: Optional[str] = Field(None, max_length=200)
    is_default: bool = Field(default=False)
    is_active: bool = Field(default=True)
    version: str = Field(default="1.0", max_length=20)


class FieldMappingTemplateCreate(FieldMappingTemplateBase):
    """Schema for creating a new field mapping template."""
    template_config: Optional[Dict[str, Any]] = None
    parent_template_id: Optional[int] = None
    mappings: Optional[List[FieldMappingCreate]] = None
    
    @validator('template_config')
    def validate_template_config(cls, v):
        """Validate template configuration."""
        if v and not isinstance(v, dict):
            raise ValueError('template_config must be a dictionary')
        return v


class FieldMappingTemplateUpdate(BaseModel):
    """Schema for updating an existing field mapping template."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    jira_project_type: Optional[str] = Field(None, max_length=100)
    organization: Optional[str] = Field(None, max_length=200)
    template_config: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class FieldMappingTemplateRead(FieldMappingTemplateBase):
    """Schema for reading field mapping template data."""
    id: int
    template_config: Optional[Dict[str, Any]] = None
    parent_template_id: Optional[int] = None
    mappings: Optional[List[FieldMappingRead]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Field Mapping Version schemas
class FieldMappingVersionBase(BaseModel):
    """Base field mapping version schema."""
    version_number: str = Field(..., min_length=1, max_length=20)
    change_type: str = Field(..., min_length=1, max_length=50)
    change_description: Optional[str] = None
    migration_required: bool = Field(default=False)


class FieldMappingVersionCreate(FieldMappingVersionBase):
    """Schema for creating a field mapping version."""
    mapping_id: int = Field(..., gt=0)
    previous_config: Optional[Dict[str, Any]] = None
    new_config: Optional[Dict[str, Any]] = None
    migration_script: Optional[str] = None


class FieldMappingVersionRead(FieldMappingVersionBase):
    """Schema for reading field mapping version data."""
    id: int
    mapping_id: int
    previous_config: Optional[Dict[str, Any]] = None
    new_config: Optional[Dict[str, Any]] = None
    migration_script: Optional[str] = None
    applied_at: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Field transformation schemas
class FieldTransformationRequest(BaseModel):
    """Schema for field transformation requests."""
    source_value: Any
    transformation_type: str = Field(..., min_length=1)
    transformation_config: Optional[Dict[str, Any]] = None
    field_type: FieldType


class FieldTransformationResponse(BaseModel):
    """Schema for field transformation responses."""
    transformed_value: Any
    success: bool
    error_message: Optional[str] = None
    warnings: Optional[List[str]] = None


class FieldValidationRequest(BaseModel):
    """Schema for field validation requests."""
    field_value: Any
    validation_rules: Dict[str, Any]
    field_type: FieldType
    is_required: bool = False


class FieldValidationResponse(BaseModel):
    """Schema for field validation responses."""
    is_valid: bool
    error_messages: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    normalized_value: Optional[Any] = None


# Bulk operations schemas
class BulkFieldMappingCreate(BaseModel):
    """Schema for bulk field mapping creation."""
    template_id: Optional[int] = None
    mappings: List[FieldMappingCreate]
    apply_to_existing: bool = Field(default=False)


class BulkFieldMappingResponse(BaseModel):
    """Schema for bulk field mapping operation response."""
    created_count: int
    updated_count: int
    failed_count: int
    created_mappings: List[FieldMappingRead]
    errors: Optional[List[str]] = None


# Migration schemas
class FieldMappingMigration(BaseModel):
    """Schema for field mapping migration."""
    from_version: str
    to_version: str
    migration_steps: List[Dict[str, Any]]
    rollback_steps: Optional[List[Dict[str, Any]]] = None
    backup_required: bool = Field(default=True)


class FieldMappingMigrationResult(BaseModel):
    """Schema for field mapping migration result."""
    success: bool
    executed_steps: List[str]
    failed_step: Optional[str] = None
    error_message: Optional[str] = None
    rollback_available: bool = False