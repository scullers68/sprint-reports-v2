"""
Field mapping service for dynamic JIRA field mapping management.

Extends existing service patterns to handle field mappings, transformations, and validation.
"""

import json
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.field_mapping import (
    FieldMapping, FieldMappingTemplate, FieldMappingVersion,
    FieldType, MappingType
)
from app.schemas.field_mapping import (
    FieldMappingCreate, FieldMappingUpdate, FieldMappingTemplateCreate,
    FieldTransformationRequest, FieldTransformationResponse,
    FieldValidationRequest, FieldValidationResponse
)


class FieldMappingService:
    """Service class for field mapping operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # Field Mapping CRUD operations
    async def get_field_mappings(
        self, 
        skip: int = 0, 
        limit: int = 100,
        template_id: Optional[int] = None,
        is_active: Optional[bool] = None
    ) -> List[FieldMapping]:
        """Get list of field mappings with optional filtering."""
        query = select(FieldMapping).options(selectinload(FieldMapping.template))
        
        if template_id:
            query = query.where(FieldMapping.template_id == template_id)
        if is_active is not None:
            query = query.where(FieldMapping.is_active == is_active)
        
        query = query.offset(skip).limit(limit).order_by(desc(FieldMapping.updated_at))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_field_mapping(self, mapping_id: int) -> Optional[FieldMapping]:
        """Get a field mapping by ID."""
        query = select(FieldMapping).options(
            selectinload(FieldMapping.template)
        ).where(FieldMapping.id == mapping_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_field_mapping_by_jira_field(
        self, 
        jira_field_id: str,
        template_id: Optional[int] = None
    ) -> Optional[FieldMapping]:
        """Get a field mapping by JIRA field ID."""
        query = select(FieldMapping).where(
            and_(
                FieldMapping.jira_field_id == jira_field_id,
                FieldMapping.is_active == True
            )
        )
        
        if template_id:
            query = query.where(FieldMapping.template_id == template_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_field_mapping(self, mapping_data: FieldMappingCreate) -> FieldMapping:
        """Create a new field mapping."""
        # Check if mapping with same JIRA field already exists
        existing = await self.get_field_mapping_by_jira_field(
            mapping_data.jira_field_id,
            mapping_data.template_id
        )
        if existing:
            raise ValueError(
                f"Field mapping for JIRA field {mapping_data.jira_field_id} already exists"
            )
        
        mapping = FieldMapping(**mapping_data.model_dump())
        self.db.add(mapping)
        await self.db.commit()
        await self.db.refresh(mapping, ["template"])
        
        # Create version record
        await self._create_version_record(
            mapping.id, "create", "Initial creation", None, mapping_data.model_dump()
        )
        
        return mapping
    
    async def update_field_mapping(
        self, 
        mapping_id: int, 
        mapping_data: FieldMappingUpdate
    ) -> Optional[FieldMapping]:
        """Update an existing field mapping."""
        mapping = await self.get_field_mapping(mapping_id)
        if not mapping:
            return None
        
        # Store previous config for versioning
        previous_config = {
            "name": mapping.name,
            "jira_field_id": mapping.jira_field_id,
            "target_field": mapping.target_field,
            "field_type": mapping.field_type.value,
            "mapping_type": mapping.mapping_type.value,
            "transformation_config": mapping.transformation_config,
            "validation_rules": mapping.validation_rules,
            "default_value": mapping.default_value,
            "is_required": mapping.is_required
        }
        
        update_data = mapping_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(mapping, field, value)
        
        await self.db.commit()
        await self.db.refresh(mapping, ["template"])
        
        # Create version record
        await self._create_version_record(
            mapping.id, "update", "Field mapping updated", 
            previous_config, update_data
        )
        
        return mapping
    
    async def delete_field_mapping(self, mapping_id: int) -> bool:
        """Delete a field mapping (soft delete by setting is_active=False)."""
        mapping = await self.get_field_mapping(mapping_id)
        if not mapping:
            return False
        
        mapping.is_active = False
        await self.db.commit()
        
        # Create version record
        await self._create_version_record(
            mapping.id, "delete", "Field mapping deactivated", None, None
        )
        
        return True
    
    # Template operations
    async def get_field_mapping_templates(
        self, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[FieldMappingTemplate]:
        """Get list of field mapping templates."""
        query = select(FieldMappingTemplate).options(
            selectinload(FieldMappingTemplate.mappings)
        )
        
        if is_active is not None:
            query = query.where(FieldMappingTemplate.is_active == is_active)
        
        query = query.offset(skip).limit(limit).order_by(desc(FieldMappingTemplate.updated_at))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_field_mapping_template(self, template_id: int) -> Optional[FieldMappingTemplate]:
        """Get a field mapping template by ID."""
        query = select(FieldMappingTemplate).options(
            selectinload(FieldMappingTemplate.mappings)
        ).where(FieldMappingTemplate.id == template_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_field_mapping_template(
        self, 
        template_data: FieldMappingTemplateCreate
    ) -> FieldMappingTemplate:
        """Create a new field mapping template."""
        # Check if template with same name already exists
        existing = await self._get_template_by_name(template_data.name)
        if existing:
            raise ValueError(f"Template with name '{template_data.name}' already exists")
        
        # Extract mappings if provided
        mappings_data = template_data.mappings or []
        template_dict = template_data.model_dump(exclude={"mappings"})
        
        template = FieldMappingTemplate(**template_dict)
        self.db.add(template)
        await self.db.flush()  # Get the ID
        
        # Create associated mappings
        for mapping_data in mappings_data:
            mapping_data.template_id = template.id
            mapping = FieldMapping(**mapping_data.model_dump())
            self.db.add(mapping)
        
        await self.db.commit()
        await self.db.refresh(template, ["mappings"])
        
        return template
    
    # Field transformation and validation
    async def transform_field_value(
        self, 
        transformation_request: FieldTransformationRequest
    ) -> FieldTransformationResponse:
        """Transform a field value based on transformation configuration."""
        try:
            source_value = transformation_request.source_value
            field_type = transformation_request.field_type
            transformation_config = transformation_request.transformation_config or {}
            
            # Apply transformation based on type
            transformed_value = await self._apply_transformation(
                source_value, transformation_request.transformation_type, 
                transformation_config, field_type
            )
            
            # Convert to target type
            final_value = await self._convert_to_type(transformed_value, field_type)
            
            return FieldTransformationResponse(
                transformed_value=final_value,
                success=True
            )
            
        except Exception as e:
            return FieldTransformationResponse(
                transformed_value=None,
                success=False,
                error_message=str(e)
            )
    
    async def validate_field_value(
        self, 
        validation_request: FieldValidationRequest
    ) -> FieldValidationResponse:
        """Validate a field value against validation rules."""
        try:
            field_value = validation_request.field_value
            validation_rules = validation_request.validation_rules
            field_type = validation_request.field_type
            is_required = validation_request.is_required
            
            # Check required validation
            if is_required and (field_value is None or field_value == ""):
                return FieldValidationResponse(
                    is_valid=False,
                    error_messages=["Field is required but no value provided"]
                )
            
            # Skip validation if value is None/empty and not required
            if field_value is None or field_value == "":
                return FieldValidationResponse(is_valid=True)
            
            # Apply validation rules
            validation_result = await self._apply_validation_rules(
                field_value, validation_rules, field_type
            )
            
            return validation_result
            
        except Exception as e:
            return FieldValidationResponse(
                is_valid=False,
                error_messages=[f"Validation error: {str(e)}"]
            )
    
    async def apply_field_mappings(
        self, 
        jira_data: Dict[str, Any],
        template_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Apply field mappings to JIRA data."""
        result = {}
        
        # Get active field mappings
        mappings = await self.get_field_mappings(
            template_id=template_id, 
            is_active=True
        )
        
        for mapping in mappings:
            try:
                # Extract value from JIRA data
                jira_value = self._extract_jira_field_value(jira_data, mapping.jira_field_id)
                
                # Apply default if no value found
                if jira_value is None and mapping.default_value:
                    jira_value = mapping.default_value
                
                # Skip if no value and not required
                if jira_value is None and not mapping.is_required:
                    continue
                
                # Apply transformation if configured
                if mapping.transformation_config and mapping.mapping_type == MappingType.TRANSFORMATION:
                    transform_request = FieldTransformationRequest(
                        source_value=jira_value,
                        transformation_type=mapping.transformation_config.get("type", "direct"),
                        transformation_config=mapping.transformation_config,
                        field_type=mapping.field_type
                    )
                    transform_response = await self.transform_field_value(transform_request)
                    
                    if transform_response.success:
                        jira_value = transform_response.transformed_value
                    else:
                        # Log transformation error and use original value
                        jira_value = jira_value
                
                # Apply validation if configured
                if mapping.validation_rules:
                    validation_request = FieldValidationRequest(
                        field_value=jira_value,
                        validation_rules=mapping.validation_rules,
                        field_type=mapping.field_type,
                        is_required=mapping.is_required
                    )
                    validation_response = await self.validate_field_value(validation_request)
                    
                    if not validation_response.is_valid:
                        # Use default value or skip if validation fails
                        if mapping.default_value:
                            jira_value = mapping.default_value
                        else:
                            continue
                
                # Set the mapped value
                result[mapping.target_field] = jira_value
                
            except Exception as e:
                # Log error and continue with other mappings
                print(f"Error processing mapping {mapping.name}: {str(e)}")
                continue
        
        return result
    
    # Private helper methods
    async def _create_version_record(
        self, 
        mapping_id: int, 
        change_type: str, 
        description: str,
        previous_config: Optional[Dict[str, Any]], 
        new_config: Optional[Dict[str, Any]]
    ):
        """Create a version record for field mapping changes."""
        version = FieldMappingVersion(
            mapping_id=mapping_id,
            version_number=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            change_type=change_type,
            change_description=description,
            previous_config=previous_config,
            new_config=new_config
        )
        self.db.add(version)
    
    async def _get_template_by_name(self, name: str) -> Optional[FieldMappingTemplate]:
        """Get template by name."""
        query = select(FieldMappingTemplate).where(FieldMappingTemplate.name == name)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _apply_transformation(
        self, 
        value: Any, 
        transformation_type: str,
        config: Dict[str, Any], 
        field_type: FieldType
    ) -> Any:
        """Apply transformation to a field value."""
        if transformation_type == "direct":
            return value
        
        elif transformation_type == "extract_object_value":
            # Extract value from object (e.g., {value: "Frontend Team"} -> "Frontend Team")
            if isinstance(value, dict):
                return value.get(config.get("key", "value"))
            return value
        
        elif transformation_type == "string_format":
            # Format string with template
            if "template" in config:
                return config["template"].format(value=value)
            return str(value)
        
        elif transformation_type == "numeric_conversion":
            # Convert to numeric with fallback
            try:
                if field_type == FieldType.INTEGER:
                    return int(float(value)) if value is not None else 0
                elif field_type == FieldType.FLOAT:
                    return float(value) if value is not None else 0.0
            except (ValueError, TypeError):
                return config.get("default", 0)
        
        elif transformation_type == "date_format":
            # Convert date format
            from datetime import datetime
            if isinstance(value, str):
                try:
                    input_format = config.get("input_format", "%Y-%m-%dT%H:%M:%S.%fZ")
                    output_format = config.get("output_format", "%Y-%m-%d")
                    dt = datetime.strptime(value, input_format)
                    return dt.strftime(output_format)
                except ValueError:
                    return value
            return value
        
        elif transformation_type == "conditional":
            # Conditional transformation
            conditions = config.get("conditions", [])
            for condition in conditions:
                if self._evaluate_condition(value, condition):
                    return condition.get("result", value)
            return config.get("default", value)
        
        return value
    
    async def _convert_to_type(self, value: Any, field_type: FieldType) -> Any:
        """Convert value to target field type."""
        if value is None:
            return None
        
        try:
            if field_type == FieldType.STRING:
                return str(value)
            elif field_type == FieldType.INTEGER:
                return int(float(value))
            elif field_type == FieldType.FLOAT:
                return float(value)
            elif field_type == FieldType.BOOLEAN:
                if isinstance(value, str):
                    return value.lower() in ["true", "1", "yes", "on"]
                return bool(value)
            elif field_type == FieldType.LIST:
                if isinstance(value, str):
                    return value.split(",")
                elif isinstance(value, list):
                    return value
                else:
                    return [value]
            elif field_type == FieldType.OBJECT:
                if isinstance(value, str):
                    return json.loads(value)
                return value
            else:
                return value
        except (ValueError, TypeError, json.JSONDecodeError):
            return value
    
    async def _apply_validation_rules(
        self, 
        value: Any, 
        rules: Dict[str, Any], 
        field_type: FieldType
    ) -> FieldValidationResponse:
        """Apply validation rules to a field value."""
        errors = []
        warnings = []
        
        # Type validation
        if "type_check" in rules and rules["type_check"]:
            try:
                await self._convert_to_type(value, field_type)
            except:
                errors.append(f"Value cannot be converted to {field_type.value}")
        
        # Range validation for numeric types
        if field_type in [FieldType.INTEGER, FieldType.FLOAT]:
            if "min_value" in rules and float(value) < rules["min_value"]:
                errors.append(f"Value {value} is less than minimum {rules['min_value']}")
            if "max_value" in rules and float(value) > rules["max_value"]:
                errors.append(f"Value {value} is greater than maximum {rules['max_value']}")
        
        # String validation
        if field_type == FieldType.STRING:
            if "min_length" in rules and len(str(value)) < rules["min_length"]:
                errors.append(f"Value length is less than minimum {rules['min_length']}")
            if "max_length" in rules and len(str(value)) > rules["max_length"]:
                errors.append(f"Value length is greater than maximum {rules['max_length']}")
            if "pattern" in rules:
                import re
                if not re.match(rules["pattern"], str(value)):
                    errors.append(f"Value does not match required pattern")
        
        # Allowed values validation
        if "allowed_values" in rules:
            if value not in rules["allowed_values"]:
                errors.append(f"Value must be one of: {rules['allowed_values']}")
        
        return FieldValidationResponse(
            is_valid=len(errors) == 0,
            error_messages=errors if errors else None,
            warnings=warnings if warnings else None,
            normalized_value=value
        )
    
    def _extract_jira_field_value(self, jira_data: Dict[str, Any], field_id: str) -> Any:
        """Extract field value from JIRA data structure."""
        # Handle nested field structure (fields.customfield_xxx)
        if "fields" in jira_data and field_id in jira_data["fields"]:
            return jira_data["fields"][field_id]
        
        # Handle direct field access
        if field_id in jira_data:
            return jira_data[field_id]
        
        return None
    
    def _evaluate_condition(self, value: Any, condition: Dict[str, Any]) -> bool:
        """Evaluate a conditional transformation."""
        operator = condition.get("operator", "equals")
        expected = condition.get("value")
        
        if operator == "equals":
            return value == expected
        elif operator == "not_equals":
            return value != expected
        elif operator == "contains":
            return expected in str(value)
        elif operator == "starts_with":
            return str(value).startswith(str(expected))
        elif operator == "ends_with":
            return str(value).endswith(str(expected))
        elif operator == "greater_than":
            return float(value) > float(expected)
        elif operator == "less_than":
            return float(value) < float(expected)
        
        return False