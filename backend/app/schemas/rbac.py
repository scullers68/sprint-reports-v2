"""
RBAC-related Pydantic schemas for API request/response models.

Defines data validation and serialization for role-based access control operations.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, validator


# Permission schemas
class PermissionBase(BaseModel):
    """Base permission schema with common fields."""
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    resource_type: str = Field(..., min_length=2, max_length=50)
    action: str = Field(..., min_length=2, max_length=50)
    is_active: bool = True


class PermissionCreate(PermissionBase):
    """Schema for creating a new permission."""
    pass


class PermissionUpdate(BaseModel):
    """Schema for updating an existing permission."""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = None
    resource_type: Optional[str] = Field(None, min_length=2, max_length=50)
    action: Optional[str] = Field(None, min_length=2, max_length=50)
    is_active: Optional[bool] = None


class PermissionRead(PermissionBase):
    """Schema for reading permission data."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Role schemas
class RoleBase(BaseModel):
    """Base role schema with common fields."""
    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    is_active: bool = True


class RoleCreate(RoleBase):
    """Schema for creating a new role."""
    permission_ids: List[int] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    """Schema for updating an existing role."""
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    permission_ids: Optional[List[int]] = None


class RoleRead(RoleBase):
    """Schema for reading role data."""
    id: int
    permissions: List[PermissionRead] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RoleWithStats(RoleRead):
    """Role schema with additional statistics."""
    user_count: int = 0
    permission_count: int = 0


# User role assignment schemas
class UserRoleAssignment(BaseModel):
    """Schema for user role assignment."""
    user_id: int = Field(..., gt=0)
    role_ids: List[int] = Field(..., min_items=0)


class UserRoleRead(BaseModel):
    """Schema for reading user role assignments."""
    user_id: int
    role_id: int
    role_name: str
    assigned_at: datetime
    assigned_by: Optional[int] = None
    
    class Config:
        from_attributes = True


# User permission summary
class UserPermissionSummary(BaseModel):
    """Schema for user permission summary."""
    user_id: int
    username: str
    email: str
    is_active: bool
    is_superuser: bool
    roles: List[str] = []
    permissions: List[str] = []
    
    class Config:
        from_attributes = True


# Permission check schemas
class PermissionCheck(BaseModel):
    """Schema for permission check requests."""
    permission: str = Field(..., min_length=3)
    resource_id: Optional[int] = None


class PermissionCheckResult(BaseModel):
    """Schema for permission check responses."""
    user_id: int
    permission: str
    has_permission: bool
    reason: Optional[str] = None


# Bulk operations
class BulkRoleAssignment(BaseModel):
    """Schema for bulk role assignment."""
    user_ids: List[int] = Field(..., min_items=1)
    role_ids: List[int] = Field(..., min_items=1)


class BulkOperationResult(BaseModel):
    """Schema for bulk operation results."""
    success_count: int = 0
    error_count: int = 0
    errors: List[str] = []


# Admin schemas
class RolePermissionMatrix(BaseModel):
    """Schema for role-permission matrix view."""
    roles: List[RoleRead] = []
    permissions: List[PermissionRead] = []
    matrix: dict = {}  # role_id -> [permission_ids]


class SystemRolesSummary(BaseModel):
    """Schema for system roles summary."""
    total_roles: int = 0
    active_roles: int = 0
    total_permissions: int = 0
    active_permissions: int = 0
    total_users_with_roles: int = 0