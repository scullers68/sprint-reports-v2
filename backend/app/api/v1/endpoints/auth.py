"""
Authentication endpoints.

Handles user authentication, token management, and authorization.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.auth import (
    UserLogin, 
    UserRegister, 
    LoginResponse, 
    Token, 
    RefreshToken,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordChange,
    MessageResponse,
    UserCreated
)
from app.services.auth_service import AuthenticationService

router = APIRouter()


@router.post("/register", response_model=UserCreated, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user."""
    auth_service = AuthenticationService(db)
    
    try:
        user = await auth_service.register_user(user_data)
        return UserCreated(user=user, message="User registered successfully")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """User login endpoint."""
    auth_service = AuthenticationService(db)
    
    try:
        user, token = await auth_service.authenticate_and_login(
            login_data.email, 
            login_data.password
        )
        return LoginResponse(user=user, token=token, message="Login successful")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_current_user)
):
    """User logout endpoint."""
    # In a stateless JWT system, logout is handled client-side
    # This endpoint exists for consistency and future token blacklisting
    return MessageResponse(message="Logout successful")


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshToken,
    db: AsyncSession = Depends(get_db)
):
    """Refresh authentication token."""
    auth_service = AuthenticationService(db)
    
    try:
        token = await auth_service.refresh_token(refresh_data.refresh_token)
        return token
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.post("/password/reset-request", response_model=MessageResponse)
async def request_password_reset(
    reset_request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset token."""
    auth_service = AuthenticationService(db)
    
    # Always return success to prevent email enumeration
    await auth_service.request_password_reset(reset_request.email)
    return MessageResponse(
        message="If the email exists, a password reset link has been sent"
    )


@router.post("/password/reset-confirm", response_model=MessageResponse)
async def confirm_password_reset(
    reset_confirm: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """Confirm password reset with token."""
    auth_service = AuthenticationService(db)
    
    success = await auth_service.reset_password(
        reset_confirm.token, 
        reset_confirm.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    return MessageResponse(message="Password reset successful")


@router.post("/password/change", response_model=MessageResponse)
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password."""
    auth_service = AuthenticationService(db)
    
    success = await auth_service.change_password(
        current_user.id,
        password_change.current_password,
        password_change.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    return MessageResponse(message="Password changed successfully")


# SSO Authentication Endpoints

@router.post("/sso/saml/initiate")
async def initiate_saml_sso(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate SAML SSO authentication flow.
    
    Returns SAML authentication URL to redirect user to IdP.
    """
    auth_service = AuthenticationService(db)
    
    # Prepare request data for SAML
    request_data = {
        'https': 'on' if request.url.scheme == 'https' else 'off',
        'http_host': request.url.hostname,
        'server_port': str(request.url.port or (443 if request.url.scheme == 'https' else 80)),
        'script_name': request.url.path,
        'get_data': dict(request.query_params),
        'post_data': {}
    }
    
    # Get SAML auth URL
    auth_url = await auth_service.initiate_saml_auth(request_data)
    
    return {
        "auth_url": auth_url,
        "provider": "saml"
    }


@router.post("/sso/saml/acs")
async def saml_assertion_consumer_service(
    request: Request,
    saml_response: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    SAML Assertion Consumer Service (ACS) endpoint.
    
    Handles SAML response from Identity Provider and authenticates user.
    """
    auth_service = AuthenticationService(db)
    
    # Prepare request data for SAML processing
    request_data = {
        'https': 'on' if request.url.scheme == 'https' else 'off',
        'http_host': request.url.hostname,
        'server_port': str(request.url.port or (443 if request.url.scheme == 'https' else 80)),
        'script_name': request.url.path,
        'get_data': dict(request.query_params),
        'post_data': {'SAMLResponse': saml_response}
    }
    
    # Process SAML response
    user = await auth_service.process_saml_response(request_data)
    
    # Create access token
    from datetime import timedelta
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "username": user.username,
            "is_active": user.is_active,
            "role": user.role,
            "sso_provider": user.sso_provider
        }
    }


@router.get("/sso/google/initiate")
async def initiate_google_sso(
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate Google OAuth 2.0 SSO authentication flow.
    
    Returns Google OAuth authorization URL to redirect user to provider.
    """
    auth_service = AuthenticationService(db)
    
    # Get Google OAuth auth URL and state
    auth_url, state = await auth_service.initiate_oauth_auth("google")
    
    return {
        "auth_url": auth_url,
        "state": state,
        "provider": "google"
    }


@router.get("/sso/azure/initiate")
async def initiate_azure_sso(
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate Microsoft Azure AD SSO authentication flow.
    
    Returns Azure AD OAuth authorization URL to redirect user to provider.
    """
    auth_service = AuthenticationService(db)
    
    # Get Azure OAuth auth URL and state
    auth_url, state = await auth_service.initiate_oauth_auth("azure")
    
    return {
        "auth_url": auth_url,
        "state": state,
        "provider": "azure"
    }


@router.get("/sso/oauth/initiate")
async def initiate_oauth_sso(
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate generic OAuth 2.0/OIDC SSO authentication flow.
    
    Returns OAuth authorization URL to redirect user to provider.
    """
    auth_service = AuthenticationService(db)
    
    # Get OAuth auth URL and state
    auth_url, state = await auth_service.initiate_oauth_auth("oauth")
    
    return {
        "auth_url": auth_url,
        "state": state,
        "provider": "oauth"
    }


@router.get("/sso/google/callback")
async def google_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Google OAuth 2.0 callback endpoint.
    
    Handles authorization code from Google and authenticates user.
    """
    auth_service = AuthenticationService(db)
    
    # Process Google OAuth callback
    user = await auth_service.process_oauth_callback(code, state, "google")
    
    # Create access token
    from datetime import timedelta
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer", 
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "username": user.username,
            "is_active": user.is_active,
            "role": user.role,
            "sso_provider": user.sso_provider
        }
    }


@router.get("/sso/azure/callback")
async def azure_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Microsoft Azure AD callback endpoint.
    
    Handles authorization code from Azure AD and authenticates user.
    """
    auth_service = AuthenticationService(db)
    
    # Process Azure OAuth callback
    user = await auth_service.process_oauth_callback(code, state, "azure")
    
    # Create access token
    from datetime import timedelta
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer", 
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "username": user.username,
            "is_active": user.is_active,
            "role": user.role,
            "sso_provider": user.sso_provider
        }
    }


@router.get("/sso/oauth/callback")
async def oauth_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Generic OAuth 2.0/OIDC callback endpoint.
    
    Handles authorization code from OAuth provider and authenticates user.
    """
    auth_service = AuthenticationService(db)
    
    # Process OAuth callback
    user = await auth_service.process_oauth_callback(code, state, "oauth")
    
    # Create access token
    from datetime import timedelta
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer", 
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "username": user.username,
            "is_active": user.is_active,
            "role": user.role,
            "sso_provider": user.sso_provider
        }
    }


@router.get("/sso/config")
async def get_sso_config():
    """
    Get SSO configuration information for client applications.
    
    Returns available SSO providers and their configuration.
    """
    if not settings.SSO_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSO authentication is not enabled"
        )
    
    config = {
        "sso_enabled": settings.SSO_ENABLED,
        "auto_provision_users": settings.SSO_AUTO_PROVISION_USERS,
        "allowed_domains": settings.SSO_ALLOWED_DOMAINS,
        "providers": []
    }
    
    # Add Google OAuth provider if configured
    if settings.GOOGLE_CLIENT_ID:
        config["providers"].append({
            "type": "google",
            "name": "Google",
            "initiate_url": "/api/v1/auth/sso/google/initiate",
            "callback_url": "/api/v1/auth/sso/google/callback",
            "client_id": settings.GOOGLE_CLIENT_ID
        })
    
    # Add Azure AD provider if configured
    if settings.AZURE_CLIENT_ID:
        config["providers"].append({
            "type": "azure",
            "name": "Microsoft Azure AD",
            "initiate_url": "/api/v1/auth/sso/azure/initiate",
            "callback_url": "/api/v1/auth/sso/azure/callback",
            "client_id": settings.AZURE_CLIENT_ID,
            "tenant_id": settings.AZURE_TENANT_ID
        })
    
    # Add SAML provider if configured
    if settings.SAML_IDP_ENTITY_ID:
        config["providers"].append({
            "type": "saml",
            "name": "SAML SSO",
            "initiate_url": "/api/v1/auth/sso/saml/initiate",
            "callback_url": "/api/v1/auth/sso/saml/acs",
            "entity_id": settings.SAML_IDP_ENTITY_ID
        })
    
    # Add generic OAuth provider if configured (backward compatibility)
    if settings.OAUTH_CLIENT_ID and not settings.GOOGLE_CLIENT_ID and not settings.AZURE_CLIENT_ID:
        config["providers"].append({
            "type": "oauth",
            "name": "OAuth 2.0 / OIDC",
            "initiate_url": "/api/v1/auth/sso/oauth/initiate",
            "callback_url": "/api/v1/auth/sso/oauth/callback",
            "client_id": settings.OAUTH_CLIENT_ID
        })
    
    return config