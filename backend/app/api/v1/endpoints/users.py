"""
User management endpoints.

Handles user CRUD operations and profile management.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_superuser
from app.core.middleware import require_permission
from app.models.user import User
from app.models.role import Role
from app.schemas.auth import UserRead, UserUpdate, MessageResponse
from app.schemas.rbac import UserPermissionSummary, UserRoleRead
from app.services.auth_service import AuthenticationService

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile."""
    return current_user


@router.put("/me", response_model=UserRead)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile."""
    auth_service = AuthenticationService(db)
    
    updated_user = await auth_service.update_user(current_user.id, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return updated_user


@router.get("/", response_model=List[UserRead])
async def list_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    active_only: bool = Query(True, description="Only return active users"),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """List all users (superuser only)."""
    auth_service = AuthenticationService(db)
    users = await auth_service.get_users(skip=skip, limit=limit, active_only=active_only)
    return users


@router.get("/{user_id}", response_model=UserRead)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID (superuser only)."""
    auth_service = AuthenticationService(db)
    user = await auth_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/{user_id}", response_model=UserRead)
async def update_user_by_id(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Update user by ID (superuser only)."""
    auth_service = AuthenticationService(db)
    
    updated_user = await auth_service.update_user(user_id, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return updated_user


@router.post("/{user_id}/deactivate", response_model=MessageResponse)
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate user account (superuser only)."""
    auth_service = AuthenticationService(db)
    
    success = await auth_service.deactivate_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return MessageResponse(message="User deactivated successfully")


@router.post("/{user_id}/activate", response_model=MessageResponse)
async def activate_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Activate user account (superuser only)."""
    auth_service = AuthenticationService(db)
    
    success = await auth_service.activate_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return MessageResponse(message="User activated successfully")


@router.post("/{user_id}/unlock", response_model=MessageResponse)
async def unlock_user_account(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Unlock user account (superuser only)."""
    auth_service = AuthenticationService(db)
    
    success = await auth_service.unlock_user_account(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return MessageResponse(message="User account unlocked successfully")


# RBAC Extensions
@router.get("/me/permissions", response_model=UserPermissionSummary)
async def get_current_user_permissions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's roles and permissions."""
    # Refresh user data from database to get latest roles
    user = db.query(User).filter(User.id == current_user.id).first()
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


@router.get("/{user_id}/roles", response_model=List[UserRoleRead])
@require_permission("user.read")
async def get_user_roles(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all roles assigned to a specific user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Build user role assignments with metadata
    user_roles = []
    for role in user.roles:
        if role.is_active:
            user_roles.append(UserRoleRead(
                user_id=user.id,
                role_id=role.id,
                role_name=role.name,
                assigned_at=role.created_at,  # Simplified - in real scenario would track assignment time
                assigned_by=None  # Would need to track who assigned the role
            ))
    
    return user_roles


@router.put("/{user_id}/roles")
@require_permission("user.roles")
async def update_user_roles(
    user_id: int,
    role_ids: List[int],
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user's role assignments."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate all role IDs exist and are active
    roles = db.query(Role).filter(
        Role.id.in_(role_ids),
        Role.is_active == True
    ).all()
    
    if len(roles) != len(role_ids):
        raise HTTPException(
            status_code=400,
            detail="One or more role IDs are invalid or inactive"
        )
    
    # Replace user's roles
    user.roles = roles
    db.commit()
    
    return {
        "message": f"Updated roles for user {user.username}",
        "roles": [role.name for role in roles]
    }


@router.post("/{user_id}/roles/{role_id}")
@require_permission("user.roles")
async def add_user_role(
    user_id: int,
    role_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a single role to a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role = db.query(Role).filter(Role.id == role_id, Role.is_active == True).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found or inactive")
    
    # Check if user already has this role
    if role in user.roles:
        return {"message": f"User {user.username} already has role {role.name}"}
    
    # Add role to user
    user.add_role(role)
    db.commit()
    
    return {"message": f"Added role {role.name} to user {user.username}"}


@router.delete("/{user_id}/roles/{role_id}")
@require_permission("user.roles")
async def remove_user_role(
    user_id: int,
    role_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a single role from a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Check if user has this role
    if role not in user.roles:
        return {"message": f"User {user.username} doesn't have role {role.name}"}
    
    # Remove role from user
    user.remove_role(role)
    db.commit()
    
    return {"message": f"Removed role {role.name} from user {user.username}"}


# SSO Administration Endpoints

@router.get("/sso/users")
async def list_sso_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    provider: str = Query(None, description="Filter by SSO provider"),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """List all SSO users (superuser only)."""
    from sqlalchemy import select
    
    # Build query
    query = select(User).where(User.sso_provider.isnot(None))
    
    if provider:
        query = query.where(User.sso_provider == provider)
    
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [
        {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "sso_provider": user.sso_provider,
            "sso_provider_id": user.sso_provider_id,
            "sso_provider_name": user.sso_provider_name,
            "sso_last_login": user.sso_last_login.isoformat() if user.sso_last_login else None,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
        for user in users
    ]


@router.post("/{user_id}/sso/deprovision", response_model=MessageResponse)
async def deprovision_sso_user(
    user_id: int,
    deactivate_only: bool = Query(True, description="Deactivate user instead of deleting"),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Deprovision SSO user account (superuser only)."""
    auth_service = AuthenticationService(db)
    
    success = await auth_service.deprovision_user(user_id, deactivate_only)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    action = "deactivated" if deactivate_only else "deleted"
    return MessageResponse(message=f"SSO user {action} successfully")


@router.get("/{user_id}/sso/details")
async def get_user_sso_details(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed SSO information for a user (superuser only)."""
    from sqlalchemy import select
    import json
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Parse SSO attributes if they exist
    sso_attributes = {}
    if user.sso_attributes:
        try:
            sso_attributes = json.loads(user.sso_attributes)
        except json.JSONDecodeError:
            sso_attributes = {"error": "Failed to parse SSO attributes"}
    
    return {
        "user_id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "sso_provider": user.sso_provider,
        "sso_provider_id": user.sso_provider_id,
        "sso_provider_name": user.sso_provider_name,
        "sso_last_login": user.sso_last_login.isoformat() if user.sso_last_login else None,
        "sso_attributes": sso_attributes,
        "failed_login_attempts": user.failed_login_attempts,
        "locked_until": user.locked_until.isoformat() if user.locked_until else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None
    }