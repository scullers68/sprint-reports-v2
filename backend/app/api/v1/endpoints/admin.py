"""
Administrative endpoints for role and permission management.

Handles RBAC administration including role management, permission assignment,
and user role administration.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from app.core.database import get_db
from app.core.middleware import require_permission, get_current_user_permissions
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.schemas.rbac import (
    RoleCreate, RoleUpdate, RoleRead, RoleWithStats,
    PermissionCreate, PermissionUpdate, PermissionRead,
    UserRoleAssignment, BulkRoleAssignment, BulkOperationResult,
    RolePermissionMatrix, SystemRolesSummary, UserPermissionSummary
)

router = APIRouter()


# Role Management Endpoints
@router.get("/roles", response_model=List[RoleWithStats])
@require_permission("admin.roles")
async def list_roles(
    request: Request,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True)
):
    """List all roles with statistics."""
    query = db.query(Role)
    
    if active_only:
        query = query.filter(Role.is_active == True)
    
    roles = query.offset(skip).limit(limit).all()
    
    # Add statistics to each role
    roles_with_stats = []
    for role in roles:
        user_count = db.query(func.count(User.id)).join(User.roles).filter(Role.id == role.id).scalar()
        role_dict = {
            **role.__dict__,
            "user_count": user_count or 0,
            "permission_count": len(role.permissions)
        }
        roles_with_stats.append(RoleWithStats(**role_dict))
    
    return roles_with_stats


@router.post("/roles", response_model=RoleRead)
@require_permission("admin.roles")
async def create_role(
    role_data: RoleCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a new role."""
    # Check if role name already exists
    existing_role = db.query(Role).filter(Role.name == role_data.name).first()
    if existing_role:
        raise HTTPException(
            status_code=400,
            detail=f"Role '{role_data.name}' already exists"
        )
    
    # Create role
    role = Role(
        name=role_data.name,
        description=role_data.description,
        is_active=role_data.is_active
    )
    
    # Add permissions if specified
    if role_data.permission_ids:
        permissions = db.query(Permission).filter(
            Permission.id.in_(role_data.permission_ids)
        ).all()
        
        if len(permissions) != len(role_data.permission_ids):
            raise HTTPException(
                status_code=400,
                detail="One or more permission IDs are invalid"
            )
        
        role.permissions = permissions
    
    db.add(role)
    db.commit()
    db.refresh(role)
    
    return role


@router.get("/roles/{role_id}", response_model=RoleRead)
@require_permission("admin.roles")
async def get_role(
    role_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific role by ID."""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    return role


@router.put("/roles/{role_id}", response_model=RoleRead)
@require_permission("admin.roles")
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing role."""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Update basic fields
    if role_data.name is not None:
        # Check for name conflicts
        existing_role = db.query(Role).filter(
            Role.name == role_data.name,
            Role.id != role_id
        ).first()
        if existing_role:
            raise HTTPException(
                status_code=400,
                detail=f"Role '{role_data.name}' already exists"
            )
        role.name = role_data.name
    
    if role_data.description is not None:
        role.description = role_data.description
    
    if role_data.is_active is not None:
        role.is_active = role_data.is_active
    
    # Update permissions if specified
    if role_data.permission_ids is not None:
        permissions = db.query(Permission).filter(
            Permission.id.in_(role_data.permission_ids)
        ).all()
        
        if len(permissions) != len(role_data.permission_ids):
            raise HTTPException(
                status_code=400,
                detail="One or more permission IDs are invalid"
            )
        
        role.permissions = permissions
    
    db.commit()
    db.refresh(role)
    
    return role


@router.delete("/roles/{role_id}")
@require_permission("admin.roles")
async def delete_role(
    role_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Delete a role (soft delete by deactivating)."""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Check if role is assigned to any users
    user_count = db.query(func.count(User.id)).join(User.roles).filter(Role.id == role_id).scalar()
    if user_count > 0:
        # Soft delete - deactivate instead of removing
        role.is_active = False
        db.commit()
        return {"message": f"Role '{role.name}' deactivated (was assigned to {user_count} users)"}
    else:
        # Hard delete if no users assigned
        db.delete(role)
        db.commit()
        return {"message": f"Role '{role.name}' deleted"}


# Permission Management Endpoints
@router.get("/permissions", response_model=List[PermissionRead])
@require_permission("admin.roles")
async def list_permissions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    resource_type: Optional[str] = Query(None),
    active_only: bool = Query(True)
):
    """List all permissions."""
    query = db.query(Permission)
    
    if active_only:
        query = query.filter(Permission.is_active == True)
    
    if resource_type:
        query = query.filter(Permission.resource_type == resource_type)
    
    permissions = query.offset(skip).limit(limit).all()
    return permissions


@router.post("/permissions", response_model=PermissionRead)
@require_permission("admin.roles")
async def create_permission(
    permission_data: PermissionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a new permission."""
    # Check if permission name already exists
    existing_permission = db.query(Permission).filter(
        Permission.name == permission_data.name
    ).first()
    if existing_permission:
        raise HTTPException(
            status_code=400,
            detail=f"Permission '{permission_data.name}' already exists"
        )
    
    permission = Permission(**permission_data.dict())
    db.add(permission)
    db.commit()
    db.refresh(permission)
    
    return permission


# User Role Management
@router.post("/users/{user_id}/roles", response_model=dict)
@require_permission("user.roles")
async def assign_user_roles(
    user_id: int,
    role_assignment: UserRoleAssignment,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Assign roles to a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get valid roles
    roles = db.query(Role).filter(
        Role.id.in_(role_assignment.role_ids),
        Role.is_active == True
    ).all()
    
    if len(roles) != len(role_assignment.role_ids):
        raise HTTPException(
            status_code=400,
            detail="One or more role IDs are invalid or inactive"
        )
    
    # Replace user's current roles
    user.roles = roles
    db.commit()
    
    return {
        "message": f"Assigned {len(roles)} roles to user {user.username}",
        "roles": [role.name for role in roles]
    }


@router.get("/users/{user_id}/permissions", response_model=UserPermissionSummary)
@require_permission("user.read")
async def get_user_permissions(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get user's complete permission summary."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserPermissionSummary(
        user_id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        roles=user.get_roles(),
        permissions=user.get_permissions()
    )


# Bulk Operations
@router.post("/bulk/assign-roles", response_model=BulkOperationResult)
@require_permission("user.roles")
async def bulk_assign_roles(
    bulk_assignment: BulkRoleAssignment,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Assign roles to multiple users in bulk."""
    result = BulkOperationResult()
    
    # Validate roles exist and are active
    roles = db.query(Role).filter(
        Role.id.in_(bulk_assignment.role_ids),
        Role.is_active == True
    ).all()
    
    if len(roles) != len(bulk_assignment.role_ids):
        result.errors.append("One or more role IDs are invalid or inactive")
        result.error_count = 1
        return result
    
    # Process each user
    for user_id in bulk_assignment.user_ids:
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                result.errors.append(f"User ID {user_id} not found")
                result.error_count += 1
                continue
            
            # Add roles to user (don't replace existing roles)
            for role in roles:
                if role not in user.roles:
                    user.roles.append(role)
            
            result.success_count += 1
            
        except Exception as e:
            result.errors.append(f"Error processing user {user_id}: {str(e)}")
            result.error_count += 1
    
    db.commit()
    return result


# System Overview
@router.get("/system/summary", response_model=SystemRolesSummary)
@require_permission("admin.system")
async def get_system_summary(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get system-wide RBAC summary."""
    total_roles = db.query(func.count(Role.id)).scalar()
    active_roles = db.query(func.count(Role.id)).filter(Role.is_active == True).scalar()
    total_permissions = db.query(func.count(Permission.id)).scalar()
    active_permissions = db.query(func.count(Permission.id)).filter(Permission.is_active == True).scalar()
    
    # Count users with at least one role
    users_with_roles = db.query(func.count(func.distinct(User.id))).join(User.roles).scalar()
    
    return SystemRolesSummary(
        total_roles=total_roles or 0,
        active_roles=active_roles or 0,
        total_permissions=total_permissions or 0,
        active_permissions=active_permissions or 0,
        total_users_with_roles=users_with_roles or 0
    )


@router.get("/matrix", response_model=RolePermissionMatrix)
@require_permission("admin.roles")
async def get_role_permission_matrix(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get role-permission matrix for administration interface."""
    roles = db.query(Role).filter(Role.is_active == True).all()
    permissions = db.query(Permission).filter(Permission.is_active == True).all()
    
    # Build matrix
    matrix = {}
    for role in roles:
        matrix[role.id] = [perm.id for perm in role.permissions]
    
    return RolePermissionMatrix(
        roles=roles,
        permissions=permissions,
        matrix=matrix
    )