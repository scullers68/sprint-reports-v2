#!/usr/bin/env python3
"""
Quick script to create admin user for testing
"""

import asyncio
import os
from datetime import datetime, timezone

# Set environment variables for Docker environment
os.environ.setdefault("SECRET_KEY", "dev-secret-key-change-in-production-minimum-32-chars")
os.environ.setdefault("POSTGRES_SERVER", "db")
os.environ.setdefault("POSTGRES_USER", "sprint_reports")
os.environ.setdefault("POSTGRES_PASSWORD", "password")
os.environ.setdefault("POSTGRES_DB", "sprint_reports_v2_local")
os.environ.setdefault("REDIS_URL", "redis://redis:6379/1")

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
        import app.models.user
        import app.models.role
        import app.models.permission
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Database tables created successfully")

async def create_admin_user():
    """Create admin user."""
    print("Creating admin user...")
    async with async_session() as session:
        try:
            # Check if admin user already exists
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.email == 'admin@sprint-reports.com')
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print("✓ Admin user already exists")
                return existing_user
            
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
            
            print(f"✓ Admin user created:")
            print(f"  Email: admin@sprint-reports.com")
            print(f"  Password: admin123")
            print(f"  Username: admin")
            print(f"  ID: {admin_user.id}")
            
            return admin_user
            
        except Exception as e:
            print(f"❌ Error creating admin user: {e}")
            await session.rollback()
            raise

async def main():
    """Main setup function."""
    print("🚀 Creating admin user for testing...")
    print("=" * 50)
    
    try:
        await create_tables()
        await create_admin_user()
        
        print("=" * 50)
        print("✅ Admin user setup completed successfully!")
        print("\n📋 Admin Credentials:")
        print("   Email: admin@sprint-reports.com")
        print("   Password: admin123")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())