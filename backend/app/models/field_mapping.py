"""
Field mapping models for dynamic JIRA field mapping configuration.

Extends existing model patterns to support flexible field mappings and transformations.
"""

from enum import Enum as PyEnum
from typing import Dict, Any, Optional

from sqlalchemy import Column, String, Integer, Boolean, Text, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.models.base import Base


class FieldType(str, PyEnum):
    """Supported field types for mapping."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    LIST = "list"
    OBJECT = "object"
    CUSTOM = "custom"


class MappingType(str, PyEnum):
    """Types of field mappings."""
    DIRECT = "direct"           # Direct field mapping
    TRANSFORMATION = "transformation"  # Field with transformation
    COMPUTED = "computed"       # Computed from multiple fields
    TEMPLATE = "template"       # Template-based mapping


class FieldMapping(Base):
    """
    Dynamic field mapping configuration.
    
    Extends existing model patterns to support flexible JIRA field mappings.
    """
    __tablename__ = "field_mappings"
    
    # Core mapping information
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # JIRA field information
    jira_field_id = Column(String(100), nullable=False, index=True)  # e.g., "customfield_10002"
    jira_field_name = Column(String(200), nullable=True)  # Human-readable name
    
    # Target mapping information
    target_field = Column(String(100), nullable=False)  # Target field in our system
    field_type = Column(Enum(FieldType), nullable=False, default=FieldType.STRING)
    mapping_type = Column(Enum(MappingType), nullable=False, default=MappingType.DIRECT)
    
    # Transformation configuration
    transformation_config = Column(JSON, nullable=True)  # JSON config for transformations
    default_value = Column(String(500), nullable=True)  # Default value if field is missing
    is_required = Column(Boolean, default=False)  # Whether field is required
    
    # Validation configuration
    validation_rules = Column(JSON, nullable=True)  # JSON validation rules
    
    # Template and versioning
    template_id = Column(Integer, ForeignKey("field_mapping_templates.id"), nullable=True)
    version = Column(String(20), nullable=False, default="1.0")
    is_active = Column(Boolean, default=True)
    
    # Relationships
    template = relationship("FieldMappingTemplate", back_populates="mappings")
    
    def __repr__(self) -> str:
        return f"<FieldMapping(name='{self.name}', jira_field='{self.jira_field_id}')>"


class FieldMappingTemplate(Base):
    """
    Templates for common field mapping configurations.
    
    Allows pre-configured mapping sets for different JIRA configurations.
    """
    __tablename__ = "field_mapping_templates"
    
    # Template information
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Configuration metadata
    jira_project_type = Column(String(100), nullable=True)  # e.g., "scrum", "kanban"
    organization = Column(String(200), nullable=True)  # Organization-specific templates
    
    # Template configuration
    template_config = Column(JSON, nullable=True)  # JSON template configuration
    is_default = Column(Boolean, default=False)  # Whether this is a default template
    is_active = Column(Boolean, default=True)
    
    # Versioning
    version = Column(String(20), nullable=False, default="1.0")
    parent_template_id = Column(Integer, ForeignKey("field_mapping_templates.id"), nullable=True)
    
    # Relationships
    mappings = relationship("FieldMapping", back_populates="template", cascade="all, delete-orphan")
    parent_template = relationship("FieldMappingTemplate", remote_side=[id])
    
    def __repr__(self) -> str:
        return f"<FieldMappingTemplate(name='{self.name}', version='{self.version}')>"


class FieldMappingVersion(Base):
    """
    Field mapping versioning and migration tracking.
    
    Tracks changes to field mappings for migration purposes.
    """
    __tablename__ = "field_mapping_versions"
    
    # Version information
    mapping_id = Column(Integer, ForeignKey("field_mappings.id"), nullable=False)
    version_number = Column(String(20), nullable=False)
    
    # Change tracking
    change_type = Column(String(50), nullable=False)  # "create", "update", "delete"
    change_description = Column(Text, nullable=True)
    previous_config = Column(JSON, nullable=True)  # Previous configuration
    new_config = Column(JSON, nullable=True)  # New configuration
    
    # Migration information
    migration_required = Column(Boolean, default=False)
    migration_script = Column(Text, nullable=True)  # Migration SQL or logic
    applied_at = Column(String, nullable=True)  # When migration was applied
    
    # Relationships
    mapping = relationship("FieldMapping")
    
    def __repr__(self) -> str:
        return f"<FieldMappingVersion(mapping_id={self.mapping_id}, version='{self.version_number}')>"