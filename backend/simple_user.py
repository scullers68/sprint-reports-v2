#!/usr/bin/env python3
"""
Simple user model test without RBAC relationships
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
from sqlalchemy import Column, String, Boolean, Integer, DateTime, select
from passlib.context import CryptContext

from app.core.database import engine, async_session
from app.models.base import Base

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SimpleUser(Base):
    """Simplified User model for testing."""
    
    __tablename__ = "simple_users"
    
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

async def create_simple_tables():
    """Create simple table."""
    print("Creating simple user table...")
    async with engine.begin() as conn:
        await conn.run_sync(SimpleUser.metadata.create_all)
    print("✓ Simple user table created")

async def create_simple_admin():
    """Create simple admin user."""
    print("Creating simple admin user...")
    async with async_session() as session:
        try:
            # Check if admin user already exists
            result = await session.execute(
                select(SimpleUser).where(SimpleUser.email == 'simple@admin.com')
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print("✓ Simple admin user already exists")
                return existing_user
            
            # Hash password
            hashed_password = pwd_context.hash("admin123")
            
            admin_user = SimpleUser(
                email="simple@admin.com",
                username="simpleadmin",
                full_name="Simple Administrator",
                hashed_password=hashed_password,
                is_active=True,
                is_superuser=True
            )
            session.add(admin_user)
            await session.commit()
            await session.refresh(admin_user)
            
            print(f"✓ Simple admin user created: ID {admin_user.id}")
            return admin_user
            
        except Exception as e:
            print(f"❌ Error creating simple admin user: {e}")
            await session.rollback()
            raise

async def test_simple_auth():
    """Test simple authentication."""
    print("Testing simple authentication...")
    async with async_session() as session:
        try:
            # Get user by email
            result = await session.execute(
                select(SimpleUser).where(SimpleUser.email == 'simple@admin.com', SimpleUser.is_active == True)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print("❌ User not found")
                return False
            
            # Verify password
            if pwd_context.verify("admin123", user.hashed_password):
                print(f"✅ Simple authentication successful! User: {user.email}")
                return True
            else:
                print("❌ Password verification failed")
                return False
                
        except Exception as e:
            print(f"❌ Simple authentication error: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Main test function."""
    print("🧪 Testing simplified authentication...")
    print("=" * 50)
    
    try:
        await create_simple_tables()
        await create_simple_admin()
        success = await test_simple_auth()
        
        print("=" * 50)
        if success:
            print("✅ Simple authentication test passed!")
        else:
            print("❌ Simple authentication test failed!")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())