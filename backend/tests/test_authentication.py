"""
Tests for authentication system.

Tests user registration, login, password management, and security features.
"""

import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_password_hash, verify_password, create_access_token
from app.models.user import User
from app.services.auth_service import AuthenticationService


class TestUserModel:
    """Test User model methods."""
    
    def test_is_locked_when_not_locked(self):
        """Test is_locked returns False when user is not locked."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            locked_until=None
        )
        assert not user.is_locked()
    
    def test_is_locked_when_locked_in_future(self):
        """Test is_locked returns True when locked_until is in future."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            locked_until=datetime.now(timezone.utc) + timedelta(minutes=30)
        )
        assert user.is_locked()
    
    def test_is_locked_when_lock_expired(self):
        """Test is_locked returns False when lock has expired."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            locked_until=datetime.now(timezone.utc) - timedelta(minutes=30)
        )
        assert not user.is_locked()
    
    def test_lock_account(self):
        """Test lock_account sets locked_until."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed"
        )
        user.lock_account(30)
        assert user.locked_until is not None
        assert user.is_locked()
    
    def test_unlock_account(self):
        """Test unlock_account clears lock and failed attempts."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            failed_login_attempts=3,
            locked_until=datetime.now(timezone.utc) + timedelta(minutes=30)
        )
        user.unlock_account()
        assert user.locked_until is None
        assert user.failed_login_attempts == 0
    
    def test_record_failed_login(self):
        """Test record_failed_login increments attempts."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            failed_login_attempts=0
        )
        user.record_failed_login()
        assert user.failed_login_attempts == 1
    
    def test_record_failed_login_locks_after_5_attempts(self):
        """Test account gets locked after 5 failed attempts."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            failed_login_attempts=4
        )
        user.record_failed_login()
        assert user.failed_login_attempts == 5
        assert user.is_locked()
    
    def test_record_successful_login(self):
        """Test record_successful_login clears attempts and updates last_login."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            failed_login_attempts=3,
            locked_until=datetime.now(timezone.utc) + timedelta(minutes=30)
        )
        user.record_successful_login()
        assert user.failed_login_attempts == 0
        assert user.locked_until is None
        assert user.last_login is not None


class TestPasswordSecurity:
    """Test password hashing and verification."""
    
    def test_create_password_hash(self):
        """Test password hash creation."""
        password = "testpassword123"
        hashed = create_password_hash(password)
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
    
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "testpassword123"
        hashed = create_password_hash(password)
        assert verify_password(password, hashed)
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = create_password_hash(password)
        assert not verify_password(wrong_password, hashed)


@pytest.mark.asyncio
class TestAuthenticationService:
    """Test AuthenticationService methods."""
    
    async def test_register_user_success(self, db_session: AsyncSession):
        """Test successful user registration."""
        auth_service = AuthenticationService(db_session)
        
        from app.schemas.auth import UserRegister
        user_data = UserRegister(
            email="newuser@example.com",
            username="newuser",
            password="TestPass123",
            full_name="New User"
        )
        
        user = await auth_service.register_user(user_data)
        assert user.email == "newuser@example.com"
        assert user.username == "newuser"
        assert user.full_name == "New User"
        assert user.is_active
        assert not user.is_superuser
        assert verify_password("TestPass123", user.hashed_password)
    
    async def test_register_user_duplicate_email(self, db_session: AsyncSession):
        """Test user registration with duplicate email fails."""
        auth_service = AuthenticationService(db_session)
        
        # Create first user
        user1 = User(
            email="duplicate@example.com",
            username="user1",
            hashed_password=create_password_hash("password")
        )
        db_session.add(user1)
        await db_session.commit()
        
        # Try to create second user with same email
        from app.schemas.auth import UserRegister
        user_data = UserRegister(
            email="duplicate@example.com",
            username="user2",
            password="TestPass123"
        )
        
        with pytest.raises(ValueError, match="User with this email already exists"):
            await auth_service.register_user(user_data)
    
    async def test_authenticate_and_login_success(self, db_session: AsyncSession):
        """Test successful authentication and login."""
        auth_service = AuthenticationService(db_session)
        
        # Create user
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=create_password_hash("testpassword"),
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        
        # Authenticate
        result_user, token = await auth_service.authenticate_and_login(
            "test@example.com", "testpassword"
        )
        
        assert result_user.email == "test@example.com"
        assert token.access_token is not None
        assert token.refresh_token is not None
        assert token.token_type == "bearer"
    
    async def test_authenticate_and_login_wrong_password(self, db_session: AsyncSession):
        """Test authentication with wrong password fails."""
        auth_service = AuthenticationService(db_session)
        
        # Create user
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=create_password_hash("testpassword"),
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        
        # Try wrong password
        with pytest.raises(ValueError, match="Invalid email or password"):
            await auth_service.authenticate_and_login(
                "test@example.com", "wrongpassword"
            )
    
    async def test_authenticate_and_login_locked_account(self, db_session: AsyncSession):
        """Test authentication with locked account fails."""
        auth_service = AuthenticationService(db_session)
        
        # Create locked user
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=create_password_hash("testpassword"),
            is_active=True,
            locked_until=datetime.now(timezone.utc) + timedelta(minutes=30)
        )
        db_session.add(user)
        await db_session.commit()
        
        # Try to authenticate
        with pytest.raises(ValueError, match="Account is temporarily locked"):
            await auth_service.authenticate_and_login(
                "test@example.com", "testpassword"
            )
    
    async def test_request_password_reset(self, db_session: AsyncSession):
        """Test password reset request."""
        auth_service = AuthenticationService(db_session)
        
        # Create user
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=create_password_hash("testpassword"),
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        
        # Request reset
        token = await auth_service.request_password_reset("test@example.com")
        
        assert token is not None
        assert len(token) > 20  # Should be a decent length token
        
        # Check user has reset token
        await db_session.refresh(user)
        assert user.reset_token == token
        assert user.reset_token_expires is not None
    
    async def test_reset_password_success(self, db_session: AsyncSession):
        """Test successful password reset."""
        auth_service = AuthenticationService(db_session)
        
        # Create user with reset token
        reset_token = "test_reset_token"
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=create_password_hash("oldpassword"),
            is_active=True,
            reset_token=reset_token,
            reset_token_expires=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        db_session.add(user)
        await db_session.commit()
        
        # Reset password
        success = await auth_service.reset_password(reset_token, "newpassword")
        
        assert success
        await db_session.refresh(user)
        assert verify_password("newpassword", user.hashed_password)
        assert user.reset_token is None
        assert user.reset_token_expires is None


@pytest.mark.asyncio
class TestAuthEndpoints:
    """Test authentication endpoints."""
    
    async def test_register_endpoint(self, client: AsyncClient):
        """Test user registration endpoint."""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "TestPass123",
            "full_name": "New User"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "User registered successfully"
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["username"] == "newuser"
    
    async def test_login_endpoint_success(self, client: AsyncClient, test_user: User):
        """Test successful login endpoint."""
        login_data = {
            "email": test_user.email,
            "password": "testpassword"
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Login successful"
        assert data["user"]["email"] == test_user.email
        assert "access_token" in data["token"]
        assert "refresh_token" in data["token"]
    
    async def test_login_endpoint_wrong_password(self, client: AsyncClient, test_user: User):
        """Test login endpoint with wrong password."""
        login_data = {
            "email": test_user.email,
            "password": "wrongpassword"
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "Invalid email or password" in data["detail"]
    
    async def test_get_current_user(self, client: AsyncClient, test_user: User):
        """Test get current user endpoint."""
        # First login to get token
        login_data = {
            "email": test_user.email,
            "password": "testpassword"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        token = login_response.json()["token"]["access_token"]
        
        # Get current user
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username
    
    async def test_password_change(self, client: AsyncClient, test_user: User):
        """Test password change endpoint."""
        # First login to get token
        login_data = {
            "email": test_user.email,
            "password": "testpassword"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        token = login_response.json()["token"]["access_token"]
        
        # Change password
        password_data = {
            "current_password": "testpassword",
            "new_password": "NewPass123"
        }
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post("/api/v1/auth/password/change", json=password_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Password changed successfully"


# Test fixtures
@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=create_password_hash("testpassword"),
        is_active=True,
        full_name="Test User"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user