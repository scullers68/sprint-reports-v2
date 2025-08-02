"""
Role model for role-based access control.

Handles role definitions and role-permission relationships.
"""

from sqlalchemy import Boolean, Column, String, Text, Integer, ForeignKey, Table, Index, CheckConstraint
from sqlalchemy.orm import relationship, validates

from app.models.base import Base
# Import user_roles table from user module
from app.models.user import user_roles


# Association table for role-permission many-to-many relationship
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    Index('idx_role_permissions_role', 'role_id'),
    Index('idx_role_permissions_permission', 'permission_id')
)


class Role(Base):
    """Role model for RBAC system."""
    
    __tablename__ = "roles"
    __allow_unmapped__ = True
    
    # Basic role info
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin"
    )
    users = relationship(
        "User",
        secondary=user_roles,
        primaryjoin="Role.id == user_roles.c.role_id",
        secondaryjoin="User.id == user_roles.c.user_id",
        back_populates="roles",
        lazy="select"
    )
    
    # Table constraints and indexes
    __table_args__ = (
        # Ensure role name is not empty when trimmed
        CheckConstraint("trim(name) != ''", name='role_name_not_empty'),
        # Index for active role filtering
        Index('idx_roles_active', 'is_active', 'name'),
    )
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate role name format."""
        if name and len(name.strip()) < 2:
            raise ValueError("Role name must be at least 2 characters long")
        return name.strip().lower() if name else name
    
    def has_permission(self, permission_name: str) -> bool:
        """Check if role has a specific permission."""
        if not self.is_active:
            return False
        return any(
            perm.name == permission_name and perm.is_active 
            for perm in self.permissions
        )
    
    def get_permissions(self) -> list[str]:
        """Get list of permission names for this role."""
        if not self.is_active:
            return []
        return [
            perm.name for perm in self.permissions 
            if perm.is_active
        ]
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}', active={self.is_active})>"