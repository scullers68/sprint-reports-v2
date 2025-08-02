"""
User model for authentication and authorization.

Handles user accounts, roles, and authentication tokens.
"""

from sqlalchemy import Boolean, Column, String, Text, Index, CheckConstraint, Integer, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship, validates
from datetime import datetime, timezone, timedelta

from app.models.base import Base


# Association table for user-role many-to-many relationship
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('assigned_by', Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    Index('idx_user_roles_user', 'user_id'),
    Index('idx_user_roles_role', 'role_id'),
    Index('idx_user_roles_assigned_by', 'assigned_by')
)


class User(Base):
    """User model for authentication."""
    
    __tablename__ = "users"
    __allow_unmapped__ = True
    
    # Basic user info
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    
    # Authentication
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Profile info
    department = Column(String(100), nullable=True)
    role = Column(String(100), nullable=True)
    avatar_url = Column(Text, nullable=True)
    
    # JIRA integration
    jira_account_id = Column(String(128), nullable=True, index=True)
    jira_display_name = Column(String(255), nullable=True)
    
    # SSO Integration
    sso_provider = Column(String(50), nullable=True, index=True)  # 'saml', 'oauth', 'oidc'
    sso_provider_id = Column(String(255), nullable=True, index=True)  # External provider user ID
    sso_provider_name = Column(String(100), nullable=True)  # Provider name (e.g., 'Azure AD', 'Okta')
    sso_last_login = Column(DateTime(timezone=True), nullable=True)  # Last SSO authentication
    sso_attributes = Column(Text, nullable=True)  # JSON string of additional SSO attributes
    
    # Authentication security (for future implementation)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Password reset functionality
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    
    # RBAC Relationships - temporarily disabled due to relationship error
    # roles = relationship(
    #     "Role",
    #     secondary=user_roles,
    #     primaryjoin="User.id == user_roles.c.user_id",
    #     secondaryjoin="Role.id == user_roles.c.role_id",
    #     back_populates="users",
    #     lazy="select"
    # )
    
    # Table constraints and indexes
    __table_args__ = (
        # Ensure email format is valid
        CheckConstraint("email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'", name='valid_email_format'),
        # Ensure username is not empty when trimmed
        CheckConstraint("trim(username) != ''", name='username_not_empty'),
        # Ensure full_name is not empty when provided
        CheckConstraint("full_name IS NULL OR trim(full_name) != ''", name='full_name_not_empty'),
        # Compound index for JIRA integration lookups
        Index('idx_user_jira_lookup', 'jira_account_id', 'is_active'),
        # Index for department and role filtering
        Index('idx_user_department_role', 'department', 'role', 'is_active'),
        # Compound index for SSO provider lookups
        Index('idx_user_sso_lookup', 'sso_provider', 'sso_provider_id', 'is_active'),
        # Index for SSO authentication
        Index('idx_user_sso_auth', 'sso_provider', 'is_active'),
        # Index for password reset tokens
        Index('idx_user_reset_token', 'reset_token'),
        # Index for account lockout queries
        Index('idx_user_locked_until', 'locked_until', 'is_active'),
    )
    
    @validates('email')
    def validate_email(self, key, email):
        """Validate email format."""
        if email and '@' not in email:
            raise ValueError("Invalid email format")
        return email.lower() if email else email
    
    @validates('username')
    def validate_username(self, key, username):
        """Validate username format."""
        if username and len(username.strip()) < 3:
            raise ValueError("Username must be at least 3 characters long")
        return username.strip() if username else username
    
    def is_locked(self) -> bool:
        """Check if user account is currently locked."""
        if not self.locked_until:
            return False
        return datetime.now(timezone.utc) < self.locked_until
    
    def lock_account(self, duration_minutes: int = 30) -> None:
        """Lock the user account for specified duration."""
        self.locked_until = datetime.now(timezone.utc).replace(microsecond=0) + \
            timedelta(minutes=duration_minutes)
    
    def unlock_account(self) -> None:
        """Unlock the user account and reset failed attempts."""
        self.locked_until = None
        self.failed_login_attempts = 0
    
    def record_failed_login(self) -> None:
        """Record a failed login attempt."""
        self.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.lock_account(30)  # Lock for 30 minutes
    
    def record_successful_login(self) -> None:
        """Record a successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login = datetime.now(timezone.utc)
    
    # RBAC Methods - temporarily disabled due to relationship error
    def has_permission(self, permission_name: str) -> bool:
        """Check if user has a specific permission through their roles."""
        if not self.is_active:
            return False
        
        # Superuser has all permissions
        if self.is_superuser:
            return True
        
        # TODO: Re-enable when relationship issue is fixed
        # Check permissions through roles
        # for role in self.roles:
        #     if role.has_permission(permission_name):
        #         return True
        return False
    
    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role."""
        if not self.is_active:
            return False
        # TODO: Re-enable when relationship issue is fixed
        # return any(role.name == role_name and role.is_active for role in self.roles)
        return False
    
    def get_permissions(self) -> list[str]:
        """Get all permissions for this user through their roles."""
        if not self.is_active:
            return []
        
        # TODO: Re-enable when relationship issue is fixed
        # permissions = set()
        # for role in self.roles:
        #     permissions.update(role.get_permissions())
        # return list(permissions)
        return []
    
    def get_roles(self) -> list[str]:
        """Get list of role names for this user."""
        if not self.is_active:
            return []
        # TODO: Re-enable when relationship issue is fixed
        # return [role.name for role in self.roles if role.is_active]
        return []
    
    def add_role(self, role) -> None:
        """Add a role to this user."""
        # TODO: Re-enable when relationship issue is fixed
        # if role not in self.roles:
        #     self.roles.append(role)
        pass
    
    def remove_role(self, role) -> None:
        """Remove a role from this user."""
        # TODO: Re-enable when relationship issue is fixed
        # if role in self.roles:
        #     self.roles.remove(role)
        pass
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', username='{self.username}')>"