#!/usr/bin/env python3
"""
Direct test of authentication service
"""

import asyncio
import os

# Set environment variables for Docker environment
os.environ.setdefault("SECRET_KEY", "dev-secret-key-change-in-production-minimum-32-chars")
os.environ.setdefault("POSTGRES_SERVER", "db")
os.environ.setdefault("POSTGRES_USER", "sprint_reports")
os.environ.setdefault("POSTGRES_PASSWORD", "password")
os.environ.setdefault("POSTGRES_DB", "sprint_reports_v2_local")
os.environ.setdefault("REDIS_URL", "redis://redis:6379/1")

from app.core.database import async_session
from app.services.auth_service import AuthenticationService

async def test_auth():
    """Test authentication directly."""
    print("🧪 Testing authentication service directly...")
    
    async with async_session() as session:
        auth_service = AuthenticationService(session)
        
        print("1. Testing authenticate_user method...")
        try:
            user = await auth_service.authenticate_user("admin@sprint-reports.com", "admin123")
            if user:
                print(f"✅ Authentication successful! User ID: {user.id}, Email: {user.email}")
                
                print("2. Testing authenticate_and_login method...")
                user2, token = await auth_service.authenticate_and_login("admin@sprint-reports.com", "admin123")
                print(f"✅ Login successful! Token: {token.access_token[:50]}...")
                
            else:
                print("❌ Authentication failed")
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_auth())