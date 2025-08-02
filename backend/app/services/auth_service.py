"""
Authentication service with SSO integration support.

Handles user authentication including traditional password-based auth
and SSO providers (SAML, OAuth 2.0, OIDC).
"""

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode, parse_qs

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from jose import JWTError, jwt
import httpx
try:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth
    from onelogin.saml2.utils import OneLogin_Saml2_Utils
    SAML_AVAILABLE = True
except ImportError:
    SAML_AVAILABLE = False

try:
    from authlib.integrations.base_client import BaseClient
    from authlib.integrations.httpx_client import AsyncOAuth2Client
    OAUTH_AVAILABLE = True
except ImportError:
    OAUTH_AVAILABLE = False

from app.core.config import settings
from app.models.user import User
from app.models.role import Role
from app.schemas.auth import UserRegister, Token
import structlog

logger = structlog.get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticationService:
    """Service for handling user authentication and SSO integration."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate user with email and password.
        
        Args:
            email: User email address
            password: Plain text password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        try:
            # Get user by email - avoid relationship loading for now
            result = await self.db.execute(
                select(User).where(User.email == email.lower(), User.is_active == True).options()
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"Authentication failed: user not found", email=email)
                return None
            
            # Check if account is locked
            if user.locked_until and user.locked_until > datetime.now(timezone.utc):
                logger.warning(f"Authentication failed: account locked", email=email)
                return None
            
            # Verify password
            if not self.verify_password(password, user.hashed_password):
                # Increment failed attempts
                user.failed_login_attempts += 1
                
                # Lock account after 5 failed attempts
                if user.failed_login_attempts >= 5:
                    user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
                    logger.warning(f"Account locked due to failed attempts", email=email)
                
                await self.db.commit()
                return None
            
            # Reset failed attempts on successful login
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login = datetime.now(timezone.utc)
            await self.db.commit()
            
            logger.info(f"User authenticated successfully", email=email)
            return user
            
        except Exception as e:
            logger.error(f"Authentication error", email=email, error=str(e))
            return None
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash."""
        return pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    async def get_current_user(self, token: str) -> Optional[User]:
        """Get current user from JWT token."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                return None
        except JWTError:
            return None
        
        result = await self.db.execute(
            select(User).where(User.email == email, User.is_active == True)
        )
        user = result.scalar_one_or_none()
        return user
    
    async def authenticate_and_login(self, email: str, password: str) -> Tuple[User, Token]:
        """
        Authenticate user and create login token.
        
        Args:
            email: User email address
            password: Plain text password
            
        Returns:
            Tuple of (User, Token) objects
            
        Raises:
            ValueError: If authentication fails
        """
        # Authenticate user
        user = await self.authenticate_user(email, password)
        if not user:
            raise ValueError("Invalid email or password")
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={"sub": user.email, "user_id": user.id},
            expires_delta=access_token_expires
        )
        
        # Create refresh token (simplified - in production should be stored securely)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = self.create_access_token(
            data={"sub": user.email, "user_id": user.id, "type": "refresh"},
            expires_delta=refresh_token_expires
        )
        
        # Create token response
        token = Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
        logger.info(f"User login successful", email=email, user_id=user.id)
        return user, token
    
    async def register_user(self, user_data: UserRegister) -> User:
        """
        Register a new user.
        
        Args:
            user_data: User registration data
            
        Returns:
            Created User object
            
        Raises:
            ValueError: If registration fails (duplicate email, etc.)
        """
        try:
            # Check if user already exists
            result = await self.db.execute(
                select(User).where(User.email == user_data.email.lower())
            )
            existing_user = result.scalar_one_or_none()
            if existing_user:
                raise ValueError("A user with this email already exists")
            
            # Check if username is taken
            result = await self.db.execute(
                select(User).where(User.username == user_data.username)
            )
            existing_username = result.scalar_one_or_none()
            if existing_username:
                raise ValueError("This username is already taken")
            
            # Hash password
            hashed_password = self.get_password_hash(user_data.password)
            
            # Create user
            user = User(
                email=user_data.email.lower(),
                username=user_data.username,
                full_name=user_data.full_name or "",
                hashed_password=hashed_password,
                is_active=True,
                is_superuser=False
            )
            
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            
            # TODO: Assign default role when RBAC relationships are fixed
            # result = await self.db.execute(
            #     select(Role).where(Role.name == "viewer", Role.is_active == True)
            # )
            # default_role = result.scalar_one_or_none()
            # if default_role:
            #     user.add_role(default_role)
            #     await self.db.commit()
            #     await self.db.refresh(user)
            
            logger.info(f"User registered successfully", email=user.email, username=user.username)
            return user
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"User registration failed", email=user_data.email, error=str(e))
            await self.db.rollback()
            raise ValueError("Failed to register user")
    
    async def refresh_token(self, refresh_token: str) -> Token:
        """
        Refresh authentication token.
        
        Args:
            refresh_token: Current refresh token
            
        Returns:
            New Token object
            
        Raises:
            ValueError: If refresh token is invalid
        """
        try:
            # Decode refresh token
            payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email: str = payload.get("sub")
            token_type: str = payload.get("type")
            
            if email is None or token_type != "refresh":
                raise ValueError("Invalid refresh token")
            
            # Get user
            result = await self.db.execute(
                select(User).where(User.email == email, User.is_active == True)
            )
            user = result.scalar_one_or_none()
            if not user:
                raise ValueError("User not found")
            
            # Create new tokens
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = self.create_access_token(
                data={"sub": user.email, "user_id": user.id},
                expires_delta=access_token_expires
            )
            
            refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            new_refresh_token = self.create_access_token(
                data={"sub": user.email, "user_id": user.id, "type": "refresh"},
                expires_delta=refresh_token_expires
            )
            
            token = Token(
                access_token=access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
            
            logger.info(f"Token refreshed", email=email, user_id=user.id)
            return token
            
        except JWTError:
            raise ValueError("Invalid refresh token")
        except Exception as e:
            logger.error(f"Token refresh failed", error=str(e))
            raise ValueError("Failed to refresh token")
    
    async def request_password_reset(self, email: str) -> bool:
        """
        Request password reset token.
        
        Args:
            email: User email address
            
        Returns:
            True if reset email was sent (or would have been sent)
        """
        try:
            # Get user by email
            result = await self.db.execute(
                select(User).where(User.email == email.lower(), User.is_active == True)
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Generate reset token
                reset_token = secrets.token_urlsafe(32)
                reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
                
                # Store reset token
                user.reset_token = reset_token
                user.reset_token_expires = reset_token_expires
                await self.db.commit()
                
                # TODO: Send email with reset token
                # For now, just log the token (in production, send email)
                logger.info(f"Password reset requested", email=email, reset_token=reset_token)
            
            # Always return True to prevent email enumeration
            return True
            
        except Exception as e:
            logger.error(f"Password reset request failed", email=email, error=str(e))
            return True  # Still return True to prevent enumeration
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset user password with token.
        
        Args:
            token: Password reset token
            new_password: New password
            
        Returns:
            True if password was reset successfully
        """
        try:
            # Find user by reset token
            result = await self.db.execute(
                select(User).where(
                    User.reset_token == token,
                    User.reset_token_expires > datetime.now(timezone.utc),
                    User.is_active == True
                )
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            # Update password and clear reset token
            user.hashed_password = self.get_password_hash(new_password)
            user.reset_token = None
            user.reset_token_expires = None
            user.failed_login_attempts = 0
            user.locked_until = None
            
            await self.db.commit()
            
            logger.info(f"Password reset successful", email=user.email)
            return True
            
        except Exception as e:
            logger.error(f"Password reset failed", token=token, error=str(e))
            return False
    
    async def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """
        Change user password.
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            
        Returns:
            True if password was changed successfully
        """
        try:
            # Get user
            result = await self.db.execute(
                select(User).where(User.id == user_id, User.is_active == True)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            # Verify current password
            if not self.verify_password(current_password, user.hashed_password):
                return False
            
            # Update password
            user.hashed_password = self.get_password_hash(new_password)
            user.failed_login_attempts = 0
            user.locked_until = None
            
            await self.db.commit()
            
            logger.info(f"Password changed successfully", email=user.email)
            return True
            
        except Exception as e:
            logger.error(f"Password change failed", user_id=user_id, error=str(e))
            return False
    
    # SSO Authentication Methods
    
    async def initiate_saml_auth(self, request_data: Dict[str, Any]) -> str:
        """
        Initiate SAML authentication flow.
        
        Args:
            request_data: HTTP request data for SAML
            
        Returns:
            SAML authentication URL
        """
        if not settings.SSO_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SSO authentication is not enabled"
            )
        
        if not SAML_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SAML support not available. Install python3-saml package."
            )
        
        try:
            # Create SAML auth object
            auth = OneLogin_Saml2_Auth(request_data, self._get_saml_settings())
            
            # Generate SAML request
            sso_url = auth.login()
            
            logger.info("SAML authentication initiated")
            return sso_url
            
        except Exception as e:
            logger.error(f"SAML authentication initiation failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initiate SAML authentication"
            )
    
    async def process_saml_response(self, request_data: Dict[str, Any]) -> User:
        """
        Process SAML response and authenticate user.
        
        Args:
            request_data: HTTP request data containing SAML response
            
        Returns:
            Authenticated user object
        """
        try:
            # Create SAML auth object
            auth = OneLogin_Saml2_Auth(request_data, self._get_saml_settings())
            
            # Process the response
            auth.process_response()
            
            # Check for errors
            errors = auth.get_errors()
            if errors:
                logger.error(f"SAML response errors", errors=errors)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="SAML authentication failed"
                )
            
            # Get user attributes
            attributes = auth.get_attributes()
            email = attributes.get('email', [None])[0]
            full_name = attributes.get('name', [None])[0]
            
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email not provided in SAML response"
                )
            
            # Get or create user
            user = await self._get_or_create_sso_user(
                email=email,
                full_name=full_name,
                provider='saml',
                provider_id=auth.get_nameid(),
                provider_name=settings.SAML_IDP_ENTITY_ID,
                attributes=attributes
            )
            
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"SAML response processing failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process SAML authentication"
            )
    
    async def initiate_oauth_auth(self, provider: str = "oauth") -> Tuple[str, str]:
        """
        Initiate OAuth 2.0 authentication flow.
        
        Args:
            provider: OAuth provider ('google', 'azure', or 'oauth' for generic)
        
        Returns:
            Tuple of (authorization_url, state)
        """
        if not settings.SSO_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SSO authentication is not enabled"
            )
        
        if not OAUTH_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth support not available. Install authlib package."
            )
        
        try:
            # Generate state parameter for security
            state = secrets.token_urlsafe(32)
            
            # Provider-specific configuration
            if provider == "google":
                return await self._initiate_google_auth(state)
            elif provider == "azure":
                return await self._initiate_azure_auth(state)
            else:
                # Generic OAuth provider
                return await self._initiate_generic_oauth_auth(state)
            
        except Exception as e:
            logger.error(f"OAuth authentication initiation failed", provider=provider, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initiate OAuth authentication"
            )
    
    async def _initiate_google_auth(self, state: str) -> Tuple[str, str]:
        """Initiate Google OAuth 2.0 authentication."""
        if not settings.GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google OAuth not configured"
            )
        
        # Google OAuth 2.0 parameters
        params = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            'scope': 'openid email profile',
            'state': state,
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        logger.info("Google OAuth authentication initiated")
        return auth_url, state
    
    async def _initiate_azure_auth(self, state: str) -> Tuple[str, str]:
        """Initiate Microsoft Azure AD authentication."""
        if not settings.AZURE_CLIENT_ID or not settings.AZURE_AUTHORITY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Azure AD OAuth not configured"
            )
        
        # Azure AD OAuth 2.0 parameters
        params = {
            'client_id': settings.AZURE_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': settings.AZURE_REDIRECT_URI,
            'scope': 'openid email profile User.Read',
            'state': state,
            'response_mode': 'query'
        }
        
        auth_url = f"{settings.AZURE_AUTHORITY}/oauth2/v2.0/authorize?{urlencode(params)}"
        logger.info("Azure AD OAuth authentication initiated")
        return auth_url, state
    
    async def _initiate_generic_oauth_auth(self, state: str) -> Tuple[str, str]:
        """Initiate generic OAuth 2.0 authentication."""
        if not settings.OAUTH_CLIENT_ID or not settings.OAUTH_AUTHORIZATION_URL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Generic OAuth not configured"
            )
        
        # Generic OAuth 2.0 parameters
        params = {
            'client_id': settings.OAUTH_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': settings.OAUTH_REDIRECT_URI,
            'scope': settings.OAUTH_SCOPE,
            'state': state
        }
        
        auth_url = f"{settings.OAUTH_AUTHORIZATION_URL}?{urlencode(params)}"
        logger.info("Generic OAuth authentication initiated")
        return auth_url, state
    
    async def process_oauth_callback(self, code: str, state: str, provider: str = "oauth") -> User:
        """
        Process OAuth callback and authenticate user.
        
        Args:
            code: Authorization code from OAuth provider
            state: State parameter for security validation
            provider: OAuth provider ('google', 'azure', or 'oauth' for generic)
            
        Returns:
            Authenticated user object
        """
        try:
            # Provider-specific processing
            if provider == "google":
                return await self._process_google_callback(code, state)
            elif provider == "azure":
                return await self._process_azure_callback(code, state)
            else:
                return await self._process_generic_oauth_callback(code, state)
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"OAuth callback processing failed", provider=provider, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process OAuth authentication"
            )
    
    async def _process_google_callback(self, code: str, state: str) -> User:
        """Process Google OAuth callback."""
        async with AsyncOAuth2Client(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        ) as client:
            # Exchange code for token
            token = await client.fetch_token(
                "https://oauth2.googleapis.com/token",
                code=code,
                redirect_uri=settings.GOOGLE_REDIRECT_URI
            )
            
            # Get user info from Google
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={'Authorization': f"Bearer {token['access_token']}"}
            )
            user_info = resp.json()
        
        # Extract user data
        email = user_info.get('email')
        full_name = user_info.get('name')
        provider_id = user_info.get('id')
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided in Google OAuth response"
            )
        
        # Get or create user
        return await self._get_or_create_sso_user(
            email=email,
            full_name=full_name,
            provider='google',
            provider_id=str(provider_id),
            provider_name='Google',
            attributes=user_info
        )
    
    async def _process_azure_callback(self, code: str, state: str) -> User:
        """Process Azure AD OAuth callback."""
        async with AsyncOAuth2Client(
            client_id=settings.AZURE_CLIENT_ID,
            client_secret=settings.AZURE_CLIENT_SECRET
        ) as client:
            # Exchange code for token
            token = await client.fetch_token(
                f"{settings.AZURE_AUTHORITY}/oauth2/v2.0/token",
                code=code,
                redirect_uri=settings.AZURE_REDIRECT_URI
            )
            
            # Get user info from Microsoft Graph
            resp = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={'Authorization': f"Bearer {token['access_token']}"}
            )
            user_info = resp.json()
        
        # Extract user data
        email = user_info.get('mail') or user_info.get('userPrincipalName')
        full_name = user_info.get('displayName')
        provider_id = user_info.get('id')
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided in Azure AD OAuth response"
            )
        
        # Get or create user
        return await self._get_or_create_sso_user(
            email=email,
            full_name=full_name,
            provider='azure',
            provider_id=str(provider_id),
            provider_name='Microsoft Azure AD',
            attributes=user_info
        )
    
    async def _process_generic_oauth_callback(self, code: str, state: str) -> User:
        """Process generic OAuth callback."""
        async with AsyncOAuth2Client(
            client_id=settings.OAUTH_CLIENT_ID,
            client_secret=settings.OAUTH_CLIENT_SECRET
        ) as client:
            # Exchange code for token
            token = await client.fetch_token(
                settings.OAUTH_TOKEN_URL,
                code=code,
                redirect_uri=settings.OAUTH_REDIRECT_URI
            )
            
            # Get user info
            resp = await client.get(
                settings.OAUTH_USERINFO_URL,
                headers={'Authorization': f"Bearer {token['access_token']}"}
            )
            user_info = resp.json()
        
        # Extract user data
        email = user_info.get('email')
        full_name = user_info.get('name')
        provider_id = user_info.get('sub') or user_info.get('id')
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided in OAuth response"
            )
        
        # Get or create user
        return await self._get_or_create_sso_user(
            email=email,
            full_name=full_name,
            provider='oauth',
            provider_id=str(provider_id),
            provider_name='OAuth Provider',
            attributes=user_info
        )
    
    async def _get_or_create_sso_user(
        self,
        email: str,
        full_name: Optional[str],
        provider: str,
        provider_id: str,
        provider_name: str,
        attributes: Dict[str, Any]
    ) -> User:
        """
        Get existing user or create new user for SSO authentication.
        
        Args:
            email: User email address
            full_name: User's full name
            provider: SSO provider type ('saml', 'oauth', 'oidc')
            provider_id: External provider user ID
            provider_name: Human-readable provider name
            attributes: Additional user attributes from provider
            
        Returns:
            User object
        """
        # Check domain restrictions
        if settings.SSO_ALLOWED_DOMAINS:
            email_domain = email.split('@')[1].lower()
            if email_domain not in [d.lower() for d in settings.SSO_ALLOWED_DOMAINS]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Email domain not allowed for SSO authentication"
                )
        
        # Try to find existing user by email
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Update SSO information for existing user
            user.sso_provider = provider
            user.sso_provider_id = provider_id
            user.sso_provider_name = provider_name
            user.sso_last_login = datetime.now(timezone.utc)
            user.sso_attributes = json.dumps(attributes)
            
            # Update user info if not set
            if not user.full_name and full_name:
                user.full_name = full_name
            
            # Ensure user is active
            user.is_active = True
            
            logger.info(f"Updated existing user with SSO info", email=email, provider=provider)
            
        elif settings.SSO_AUTO_PROVISION_USERS:
            # Create new user
            username = email.split('@')[0]  # Use email prefix as username
            
            # Ensure username is unique
            counter = 1
            original_username = username
            while True:
                result = await self.db.execute(
                    select(User).where(User.username == username)
                )
                if not result.scalar_one_or_none():
                    break
                username = f"{original_username}{counter}"
                counter += 1
            
            user = User(
                email=email.lower(),
                username=username,
                full_name=full_name or '',
                hashed_password=self.get_password_hash(secrets.token_urlsafe(32)),  # Random password
                is_active=True,
                role=settings.SSO_DEFAULT_ROLE,
                sso_provider=provider,
                sso_provider_id=provider_id,
                sso_provider_name=provider_name,
                sso_last_login=datetime.now(timezone.utc),
                sso_attributes=json.dumps(attributes)
            )
            
            self.db.add(user)
            logger.info(f"Created new SSO user", email=email, provider=provider)
            
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not found and auto-provisioning is disabled"
            )
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    def _get_saml_settings(self) -> Dict[str, Any]:
        """Get SAML configuration settings."""
        return {
            'sp': {
                'entityId': settings.SAML_SP_ENTITY_ID,
                'assertionConsumerService': {
                    'url': f"{settings.OAUTH_REDIRECT_URI}/saml/acs",
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST'
                },
                'singleLogoutService': {
                    'url': f"{settings.OAUTH_REDIRECT_URI}/saml/sls",
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                },
                'NameIDFormat': 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress',
                'x509cert': settings.SAML_SP_X509_CERT,
                'privateKey': settings.SAML_SP_PRIVATE_KEY
            },
            'idp': {
                'entityId': settings.SAML_IDP_ENTITY_ID,
                'singleSignOnService': {
                    'url': settings.SAML_IDP_SSO_URL,
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                },
                'x509cert': settings.SAML_IDP_X509_CERT
            }
        }
    
    async def deprovision_user(self, user_id: int, deactivate_only: bool = True) -> bool:
        """
        Deprovision user account.
        
        Args:
            user_id: User ID to deprovision
            deactivate_only: If True, deactivate user; if False, delete user
            
        Returns:
            True if successful
        """
        try:
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"User not found for deprovisioning", user_id=user_id)
                return False
            
            if deactivate_only:
                user.is_active = False
                user.sso_provider = None
                user.sso_provider_id = None
                user.sso_attributes = None
                logger.info(f"User deactivated", user_id=user_id, email=user.email)
            else:
                await self.db.delete(user)
                logger.info(f"User deleted", user_id=user_id)
            
            await self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"User deprovisioning failed", user_id=user_id, error=str(e))
            return False