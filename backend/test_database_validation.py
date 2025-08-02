#!/usr/bin/env python3
"""
Database Schema Validation Test for Epic 050
Tests database connectivity, schema, and admin user creation
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.core.database import get_database
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.user import UserRole
from app.models.role import RolePermission

async def test_database_connectivity():
    """Test basic database connectivity"""
    print("🔍 Testing database connectivity...")
    try:
        async for db in get_database():
            result = await db.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ PostgreSQL connected: {version}")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

async def test_database_schema():
    """Test that all required tables exist"""
    print("\n🔍 Testing database schema...")
    try:
        async for db in get_database():
            # Get all tables
            result = await db.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            
            print("📋 Existing tables:")
            for table in tables:
                print(f"   - {table}")
            
            # Check required tables for RBAC system
            required_tables = ['users', 'roles', 'permissions', 'user_roles', 'role_permissions']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                print(f"❌ Missing required tables: {missing_tables}")
                return False
            else:
                print("✅ All required RBAC tables present")
                return True
                
    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        return False

async def test_admin_user():
    """Test that admin user was created successfully"""
    print("\n🔍 Testing admin user creation...")
    try:
        async for db in get_database():
            # Check for admin user
            result = await db.execute(text("""
                SELECT u.email, u.is_active, u.is_superuser, r.name as role_name
                FROM users u
                LEFT JOIN user_roles ur ON u.id = ur.user_id
                LEFT JOIN roles r ON ur.role_id = r.id
                WHERE u.email = 'admin@sprint-reports.com'
            """))
            admin_data = result.fetchall()
            
            if not admin_data:
                print("❌ Admin user not found")
                return False
            
            admin_info = admin_data[0]
            print(f"✅ Admin user found:")
            print(f"   - Email: {admin_info[0]}")
            print(f"   - Active: {admin_info[1]}")
            print(f"   - Superuser: {admin_info[2]}")
            print(f"   - Role: {admin_info[3] or 'No role assigned'}")
            
            # Check user count
            result = await db.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            print(f"   - Total users in system: {user_count}")
            
            return True
            
    except Exception as e:
        print(f"❌ Admin user validation failed: {e}")
        return False

async def test_rbac_relationships():
    """Test RBAC model relationships"""
    print("\n🔍 Testing RBAC relationships...")
    try:
        async for db in get_database():
            # Check roles
            result = await db.execute(text("SELECT name FROM roles ORDER BY name"))
            roles = [row[0] for row in result.fetchall()]
            print(f"📋 Available roles: {roles}")
            
            # Check permissions
            result = await db.execute(text("SELECT name FROM permissions ORDER BY name"))
            permissions = [row[0] for row in result.fetchall()]
            print(f"📋 Available permissions: {permissions}")
            
            # Check role-permission mappings
            result = await db.execute(text("""
                SELECT r.name as role, p.name as permission
                FROM role_permissions rp
                JOIN roles r ON rp.role_id = r.id
                JOIN permissions p ON rp.permission_id = p.id
                ORDER BY r.name, p.name
            """))
            mappings = result.fetchall()
            print(f"📋 Role-Permission mappings: {len(mappings)} total")
            
            for role, permission in mappings[:5]:  # Show first 5
                print(f"   - {role} -> {permission}")
            if len(mappings) > 5:
                print(f"   ... and {len(mappings) - 5} more")
            
            return True
            
    except Exception as e:
        print(f"❌ RBAC relationship validation failed: {e}")
        return False

async def main():
    """Run all database validation tests"""
    print("🚀 Epic 050 Database Validation Test Suite")
    print("=" * 50)
    
    tests = [
        test_database_connectivity,
        test_database_schema,
        test_admin_user,
        test_rbac_relationships
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
    
    print("\n" + "=" * 50)
    print("🎯 Database Validation Summary:")
    
    all_passed = all(results)
    if all_passed:
        print("✅ ALL TESTS PASSED - Database foundation is ready!")
    else:
        print("❌ SOME TESTS FAILED - Database needs attention")
    
    print(f"📊 Test Results: {sum(results)}/{len(results)} passed")
    
    return all_passed

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        sys.exit(1)