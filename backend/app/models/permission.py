"""
Permission model for role-based access control.

Handles permission definitions and permission validation.
"""

from sqlalchemy import Boolean, Column, String, Text, Index, CheckConstraint
from sqlalchemy.orm import relationship, validates

from app.models.base import Base


class Permission(Base):
    """Permission model for RBAC system."""
    
    __tablename__ = "permissions"
    __allow_unmapped__ = True
    
    # Basic permission info
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    resource_type = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships - temporarily disabled
    # roles = relationship(
    #     "Role",
    #     secondary="role_permissions",
    #     back_populates="permissions",
    #     lazy="select"
    # )
    
    # Table constraints and indexes
    __table_args__ = (
        # Ensure permission fields are not empty when trimmed
        CheckConstraint("trim(name) != ''", name='permission_name_not_empty'),
        CheckConstraint("trim(resource_type) != ''", name='resource_type_not_empty'),
        CheckConstraint("trim(action) != ''", name='action_not_empty'),
        # Index for resource and action filtering
        Index('idx_permissions_resource_action', 'resource_type', 'action'),
        # Index for active permission filtering
        Index('idx_permissions_active', 'is_active', 'resource_type'),
    )
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate permission name format."""
        if name and len(name.strip()) < 3:
            raise ValueError("Permission name must be at least 3 characters long")
        return name.strip().lower() if name else name
    
    @validates('resource_type')
    def validate_resource_type(self, key, resource_type):
        """Validate resource type format."""
        if resource_type and len(resource_type.strip()) < 2:
            raise ValueError("Resource type must be at least 2 characters long")
        return resource_type.strip().lower() if resource_type else resource_type
    
    @validates('action')
    def validate_action(self, key, action):
        """Validate action format."""
        if action and len(action.strip()) < 2:
            raise ValueError("Action must be at least 2 characters long")
        return action.strip().lower() if action else action
    
    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name='{self.name}', resource='{self.resource_type}', action='{self.action}')>"