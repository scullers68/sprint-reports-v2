"""
Field mapping management endpoints.

Handles CRUD operations for field mappings, templates, and JIRA field discovery.
"""

from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.field_mapping import (
    FieldMappingCreate, FieldMappingRead, FieldMappingUpdate,
    FieldMappingTemplateCreate, FieldMappingTemplateRead, FieldMappingTemplateUpdate,
    FieldTransformationRequest, FieldTransformationResponse,
    FieldValidationRequest, FieldValidationResponse,
    BulkFieldMappingCreate, BulkFieldMappingResponse
)
from app.services.field_mapping_service import FieldMappingService
from app.services.jira_service import JiraService

router = APIRouter()

# Field Mapping CRUD Operations
@router.get("/", response_model=List[FieldMappingRead])
async def list_field_mappings(
    *,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    template_id: Optional[int] = Query(None, description="Filter by template ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status")
):
    """List all field mappings with optional filtering."""
    service = FieldMappingService(db)
    return await service.get_field_mappings(
        skip=skip,
        limit=limit,
        template_id=template_id,
        is_active=is_active
    )


@router.get("/{mapping_id}", response_model=FieldMappingRead)
async def get_field_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific field mapping by ID."""
    service = FieldMappingService(db)
    mapping = await service.get_field_mapping(mapping_id)
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Field mapping with ID {mapping_id} not found"
        )
    
    return mapping


@router.post("/", response_model=FieldMappingRead, status_code=status.HTTP_201_CREATED)
async def create_field_mapping(
    *,
    db: AsyncSession = Depends(get_db),
    mapping_data: FieldMappingCreate
):
    """Create a new field mapping."""
    service = FieldMappingService(db)
    
    try:
        return await service.create_field_mapping(mapping_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{mapping_id}", response_model=FieldMappingRead)
async def update_field_mapping(
    mapping_id: int,
    mapping_data: FieldMappingUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing field mapping."""
    service = FieldMappingService(db)
    mapping = await service.update_field_mapping(mapping_id, mapping_data)
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Field mapping with ID {mapping_id} not found"
        )
    
    return mapping


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a field mapping (soft delete)."""
    service = FieldMappingService(db)
    success = await service.delete_field_mapping(mapping_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Field mapping with ID {mapping_id} not found"
        )


# Field Mapping Template Operations
@router.get("/templates/", response_model=List[FieldMappingTemplateRead])
async def list_field_mapping_templates(
    *,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None, description="Filter by active status")
):
    """List all field mapping templates."""
    service = FieldMappingService(db)
    return await service.get_field_mapping_templates(
        skip=skip,
        limit=limit,
        is_active=is_active
    )


@router.get("/templates/{template_id}", response_model=FieldMappingTemplateRead)
async def get_field_mapping_template(
    template_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific field mapping template by ID."""
    service = FieldMappingService(db)
    template = await service.get_field_mapping_template(template_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Field mapping template with ID {template_id} not found"
        )
    
    return template


@router.post("/templates/", response_model=FieldMappingTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_field_mapping_template(
    *,
    db: AsyncSession = Depends(get_db),
    template_data: FieldMappingTemplateCreate
):
    """Create a new field mapping template."""
    service = FieldMappingService(db)
    
    try:
        return await service.create_field_mapping_template(template_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Field Transformation and Validation Operations
@router.post("/transform", response_model=FieldTransformationResponse)
async def transform_field_value(
    transformation_request: FieldTransformationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Transform a field value using specified transformation rules."""
    service = FieldMappingService(db)
    return await service.transform_field_value(transformation_request)


@router.post("/validate", response_model=FieldValidationResponse)
async def validate_field_value(
    validation_request: FieldValidationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Validate a field value against validation rules."""
    service = FieldMappingService(db)
    return await service.validate_field_value(validation_request)


# JIRA Integration Operations
@router.get("/jira/custom-fields")
async def get_jira_custom_fields(
    db: AsyncSession = Depends(get_db)
):
    """Get all custom fields from JIRA instance."""
    jira_service = JiraService(db=db)
    
    try:
        return await jira_service.get_custom_fields()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve JIRA custom fields: {str(e)}"
        )


@router.post("/jira/discover")
async def discover_field_mappings(
    *,
    db: AsyncSession = Depends(get_db),
    project_key: Optional[str] = Query(None, description="JIRA project key for analysis"),
    sample_issues: Optional[List[Dict[str, Any]]] = None
):
    """Discover potential field mappings by analyzing JIRA data."""
    jira_service = JiraService(db=db)
    
    try:
        return await jira_service.discover_field_mappings(
            sample_issues=sample_issues,
            project_key=project_key
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover field mappings: {str(e)}"
        )


@router.post("/bulk", response_model=BulkFieldMappingResponse)
async def bulk_create_field_mappings(
    *,
    db: AsyncSession = Depends(get_db),
    bulk_request: BulkFieldMappingCreate
):
    """Create multiple field mappings in bulk."""
    service = FieldMappingService(db)
    
    created_mappings = []
    errors = []
    created_count = 0
    failed_count = 0
    
    for mapping_data in bulk_request.mappings:
        try:
            mapping = await service.create_field_mapping(mapping_data)
            created_mappings.append(mapping)
            created_count += 1
        except Exception as e:
            errors.append(f"Failed to create mapping '{mapping_data.name}': {str(e)}")
            failed_count += 1
    
    return BulkFieldMappingResponse(
        created_count=created_count,
        updated_count=0,  # Not implemented in this endpoint
        failed_count=failed_count,
        created_mappings=created_mappings,
        errors=errors if errors else None
    )


@router.post("/templates/{template_id}/apply")
async def apply_template_to_jira_data(
    template_id: int,
    jira_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Apply a field mapping template to JIRA data."""
    service = FieldMappingService(db)
    
    # Verify template exists
    template = await service.get_field_mapping_template(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Field mapping template with ID {template_id} not found"
        )
    
    try:
        mapped_data = await service.apply_field_mappings(
            jira_data=jira_data,
            template_id=template_id
        )
        
        return {
            "template_id": template_id,
            "template_name": template.name,
            "original_data": jira_data,
            "mapped_data": mapped_data,
            "mapping_count": len(mapped_data)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply field mappings: {str(e)}"
        )


# Testing and Utilities
@router.get("/test/connection")
async def test_jira_connection(
    db: AsyncSession = Depends(get_db)
):
    """Test connection to JIRA instance."""
    jira_service = JiraService(db=db)
    
    try:
        return await jira_service.test_connection()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connection test failed: {str(e)}"
        )