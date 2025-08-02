#!/usr/bin/env python3
"""
Database setup script for Sprint Reports v2
Creates database tables and initial admin user.
"""

import asyncio
import os
from datetime import datetime, timezone

# Set minimal environment variables
os.environ.setdefault("SECRET_KEY", "dev-secret-key-12345-very-long-key")
os.environ.setdefault("ENCRYPTION_KEY", "dev-encryption-key-32-chars-long!!")
os.environ.setdefault("POSTGRES_SERVER", "localhost")
os.environ.setdefault("POSTGRES_USER", "sprint_reports")
os.environ.setdefault("POSTGRES_PASSWORD", "password")
os.environ.setdefault("POSTGRES_DB", "sprint_reports_v2")
os.environ.setdefault("JIRA_URL", "http://jira.example.com")
os.environ.setdefault("JIRA_EMAIL", "dev@example.com")
os.environ.setdefault("JIRA_API_TOKEN", "dev-token")
os.environ.setdefault("JIRA_WEBHOOK_SECRET", "webhook-secret")
os.environ.setdefault("CONFLUENCE_URL", "http://confluence.example.com")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://sprint_reports:password@localhost:5432/sprint_reports_v2")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TLS_ENABLED", "false")
os.environ.setdefault("DB_ENCRYPTION_ENABLED", "false")

from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.core.database import engine, async_session
from app.models.base import Base
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_tables():
    """Create all database tables."""
    print("Creating database tables...")
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from app.models import user, role, permission, sprint, queue, report, capacity
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Database tables created successfully")

async def create_permissions():
    """Create default permissions."""
    print("Creating default permissions...")
    async with async_session() as session:
        permissions_data = [
            ("admin:full", "Full administrative access", "admin", "full"),
            ("users:read", "Read user information", "users", "read"),
            ("users:write", "Create and update users", "users", "write"),
            ("users:delete", "Delete users", "users", "delete"),
            ("sprints:read", "Read sprint information", "sprints", "read"),
            ("sprints:write", "Create and update sprints", "sprints", "write"),
            ("sprints:delete", "Delete sprints", "sprints", "delete"),
            ("reports:read", "Read reports", "reports", "read"),
            ("reports:write", "Create and update reports", "reports", "write"),
            ("capacity:read", "Read capacity information", "capacity", "read"),
            ("capacity:write", "Manage team capacity", "capacity", "write"),
        ]
        
        for name, description, resource_type, action in permissions_data:
            # Check if permission already exists
            result = await session.execute(
                f"SELECT id FROM permissions WHERE name = '{name}'"
            )
            if not result.first():
                permission = Permission(
                    name=name, 
                    description=description,
                    resource_type=resource_type,
                    action=action
                )
                session.add(permission)
        
        await session.commit()
    print("✓ Default permissions created")

async def create_admin_role():
    """Create admin role with all permissions."""
    print("Creating admin role...")
    async with async_session() as session:
        # Create admin role if it doesn't exist
        result = await session.execute("SELECT id FROM roles WHERE name = 'admin'")
        if not result.first():
            admin_role = Role(
                name="admin",
                description="System administrator with full access",
                is_active=True
            )
            session.add(admin_role)
            await session.commit()
            await session.refresh(admin_role)
            
            # Add all permissions to admin role
            permissions = await session.execute("SELECT * FROM permissions")
            for permission_row in permissions.fetchall():
                await session.execute(
                    f"INSERT INTO role_permissions (role_id, permission_id) VALUES ({admin_role.id}, {permission_row.id})"
                )
            await session.commit()
    print("✓ Admin role created with all permissions")

async def create_admin_user():
    """Create admin user."""
    print("Creating admin user...")
    async with async_session() as session:
        # Check if admin user already exists
        result = await session.execute("SELECT id FROM users WHERE email = 'admin@sprint-reports.com'")
        if not result.first():
            # Hash password
            hashed_password = pwd_context.hash("admin123")
            
            admin_user = User(
                email="admin@sprint-reports.com",
                username="admin",
                full_name="System Administrator",
                hashed_password=hashed_password,
                is_active=True,
                is_superuser=True,
                department="IT",
                role="Administrator"
            )
            session.add(admin_user)
            await session.commit()
            await session.refresh(admin_user)
            
            # Assign admin role to user
            admin_role_result = await session.execute("SELECT id FROM roles WHERE name = 'admin'")
            admin_role_id = admin_role_result.first().id
            await session.execute(
                f"INSERT INTO user_roles (user_id, role_id) VALUES ({admin_user.id}, {admin_role_id})"
            )
            await session.commit()
            
            print(f"✓ Admin user created:")
            print(f"  Email: admin@sprint-reports.com")
            print(f"  Password: admin123")
            print(f"  Username: admin")
        else:
            print("✓ Admin user already exists")

async def create_sample_data():
    """Create sample sprint data for testing."""
    print("Creating sample data...")
    async with async_session() as session:
        # Check if sample data already exists
        result = await session.execute("SELECT id FROM sprints WHERE name = 'Sample Sprint 1'")
        if not result.first():
            from app.models.sprint import Sprint
            
            sample_sprint = Sprint(
                name="Sample Sprint 1",
                description="Initial test sprint for development",
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc),
                is_active=True,
                jira_id="TEST-1",
                jira_key="TEST",
                jira_board_id=1
            )
            session.add(sample_sprint)
            await session.commit()
            print("✓ Sample sprint data created")
        else:
            print("✓ Sample data already exists")

async def main():
    """Main setup function."""
    print("🚀 Setting up Sprint Reports v2 database...")
    print("=" * 50)
    
    try:
        await create_tables()
        await create_permissions()
        await create_admin_role()
        await create_admin_user()
        await create_sample_data()
        
        print("=" * 50)
        print("✅ Database setup completed successfully!")
        print("\n📋 Admin Credentials:")
        print("   Email: admin@sprint-reports.com")
        print("   Password: admin123")
        print("   Role: Administrator")
        print("\n🔗 Next steps:")
        print("   1. Start the FastAPI application")
        print("   2. Access the API docs at http://localhost:8000/docs")
        print("   3. Login with the admin credentials")
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())