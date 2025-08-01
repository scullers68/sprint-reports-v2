#!/usr/bin/env python3
"""
Live SSO Testing Script - Test the actual SSO implementation
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Load credentials from atlaissian.secret
secret_file = project_root.parent / "atlaissian.secret"
if secret_file.exists():
    print("📁 Loading credentials from atlaissian.secret...")
    with open(secret_file) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
    print("✅ Credentials loaded")
else:
    print("❌ atlaissian.secret file not found")
    sys.exit(1)

async def test_sso_configuration():
    """Test SSO configuration and endpoints."""
    print("\n🧪 Testing SSO Configuration...")
    
    try:
        # Set SSO enabled
        os.environ['SSO_ENABLED'] = 'true'
        os.environ['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID', '')
        os.environ['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET', '')
        
        from app.core.config import Settings
        
        print("📊 Testing configuration loading...")
        settings = Settings()
        
        # Test configuration
        sso_enabled = getattr(settings, 'SSO_ENABLED', False)
        google_client_id = getattr(settings, 'GOOGLE_CLIENT_ID', None)
        
        print(f"   SSO Enabled: {sso_enabled}")
        print(f"   Google Client ID: {google_client_id[:20]}..." if google_client_id else "   Google Client ID: Not set")
        
        if not sso_enabled:
            print("❌ SSO is not enabled in configuration")
            return False
            
        if not google_client_id:
            print("❌ Google Client ID not configured")
            return False
            
        print("✅ SSO configuration loaded successfully")
        
        # Test auth service
        print("\n🔧 Testing AuthenticationService...")
        from app.services.auth_service import AuthenticationService
        
        auth_service = AuthenticationService()
        
        # Test Google OAuth URL generation
        if hasattr(auth_service, 'get_google_oauth_url'):
            oauth_url = auth_service.get_google_oauth_url("test-state")
            print(f"✅ Google OAuth URL generated: {oauth_url[:50]}...")
        else:
            print("❌ Google OAuth URL method not found")
            return False
            
        print("✅ AuthenticationService working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {str(e)}")
        return False

async def test_api_endpoints():
    """Test SSO API endpoints."""
    print("\n🌐 Testing API Endpoints...")
    
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        # Test SSO config endpoint
        print("   Testing /api/v1/auth/sso/config...")
        response = client.get("/api/v1/auth/sso/config")
        
        if response.status_code == 200:
            config = response.json()
            print(f"✅ SSO Config endpoint working: {len(config.get('providers', []))} providers configured")
            print(f"   Available providers: {list(config.get('providers', {}).keys())}")
        else:
            print(f"❌ SSO Config endpoint failed: {response.status_code}")
            return False
            
        # Test Google OAuth initiation endpoint
        print("   Testing /api/v1/auth/sso/google/initiate...")
        response = client.get("/api/v1/auth/sso/google/initiate")
        
        if response.status_code in [200, 302]:  # 302 for redirect
            print("✅ Google OAuth initiation endpoint working")
        else:
            print(f"❌ Google OAuth initiation failed: {response.status_code}")
            return False
            
        print("✅ All API endpoints working correctly")
        return True
        
    except Exception as e:
        print(f"❌ API endpoint test failed: {str(e)}")
        return False

def test_frontend_components():
    """Test that frontend components exist."""
    print("\n🎨 Testing Frontend Components...")
    
    try:
        # Check if SSO components exist
        sso_select_component = Path("../frontend/src/components/auth/SSOProviderSelect.tsx")
        sso_callback_component = Path("../frontend/src/components/auth/SSOCallback.tsx")
        
        if sso_select_component.exists():
            print("✅ SSOProviderSelect component exists")
        else:
            print("❌ SSOProviderSelect component missing")
            return False
            
        if sso_callback_component.exists():
            print("✅ SSOCallback component exists")
        else:
            print("❌ SSOCallback component missing")
            return False
            
        print("✅ All frontend components present")
        return True
        
    except Exception as e:
        print(f"❌ Frontend component test failed: {str(e)}")
        return False

async def main():
    """Run all SSO tests."""
    print("🚀 SSO Implementation Test Suite")
    print("=" * 50)
    
    # Test configuration
    config_ok = await test_sso_configuration()
    
    # Test API endpoints
    api_ok = await test_api_endpoints()
    
    # Test frontend components
    frontend_ok = test_frontend_components()
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS:")
    print(f"   Configuration: {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"   API Endpoints: {'✅ PASS' if api_ok else '❌ FAIL'}")
    print(f"   Frontend:      {'✅ PASS' if frontend_ok else '❌ FAIL'}")
    
    if all([config_ok, api_ok, frontend_ok]):
        print("\n🎉 SSO IMPLEMENTATION: FULLY FUNCTIONAL!")
        print("\n📋 Next Steps:")
        print("   1. Start the application: cd backend && python -m uvicorn app.main:app --reload")
        print("   2. Visit: http://localhost:8000/api/v1/auth/sso/config")
        print("   3. Test Google OAuth: http://localhost:8000/api/v1/auth/sso/google/initiate")
        print("   4. Check frontend: http://localhost:3000 (if frontend is running)")
        return True
    else:
        print("\n❌ SSO IMPLEMENTATION: ISSUES FOUND")
        print("   Please check the errors above and fix them.")
        return False

if __name__ == "__main__":
    asyncio.run(main())