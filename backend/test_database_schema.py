#!/usr/bin/env python3
"""
Database Schema Validation for Epic 3

Tests that the database schema changes for Epic 3 are correctly structured
and that the migration files contain the expected table modifications.
"""

import re
import ast
from pathlib import Path
from datetime import datetime

def test_migration_005_webhook_events():
    """Test migration 005 updates webhook_events correctly."""
    print("Testing Migration 005 (webhook_events schema update)...")
    
    migration_file = Path("alembic/versions/005_update_webhook_events_schema.py")
    content = migration_file.read_text()
    
    # Test 1: Migration metadata is correct
    assert "revision = '005_update_webhook_events_schema'" in content
    assert "down_revision = '004_add_webhook_tables'" in content
    print("✓ Migration 005 metadata is correct")
    
    # Test 2: Column renames are present
    expected_renames = [
        ("raw_payload", "payload"),
        ("processing_attempts", "retry_count"),
        ("last_processed_at", "processed_at")
    ]
    
    for old_name, new_name in expected_renames:
        assert f"alter_column('webhook_events', '{old_name}'" in content
        assert f"new_column_name='{new_name}'" in content
    print("✓ Migration 005 contains expected column renames")
    
    # Test 3: New columns are added
    expected_new_columns = ["processing_duration_ms"]
    for col in expected_new_columns:
        assert f"add_column('webhook_events'" in content
        assert col in content
    print("✓ Migration 005 adds new columns")
    
    # Test 4: Unwanted columns are dropped
    expected_drops = [
        "webhook_id", "user_account_id", "user_display_name",
        "issue_key", "issue_id", "project_key", "processed_data",
        "received_at", "jira_timestamp", "processing_priority"
    ]
    
    for col in expected_drops:
        assert f"drop_column('webhook_events', '{col}')" in content
    print("✓ Migration 005 drops unwanted columns")
    
    # Test 5: Downgrade function exists and reverses changes
    assert "def downgrade()" in content
    assert "alter_column('webhook_events', 'payload'" in content
    assert "new_column_name='raw_payload'" in content
    print("✓ Migration 005 has correct downgrade function")
    
    return True

def test_migration_007_sync_schema():
    """Test migration 007 aligns sync schema correctly."""
    print("\nTesting Migration 007 (sync schema alignment)...")
    
    migration_file = Path("alembic/versions/007_align_sync_schema.py")
    content = migration_file.read_text()
    
    # Test 1: Migration metadata is correct
    assert "revision = '007_align_sync_schema'" in content
    assert "down_revision = '005_update_webhook_events_schema'" in content
    print("✓ Migration 007 metadata is correct")
    
    # Test 2: New columns added to sync_metadata
    expected_columns = [
        "resolution_strategy",
        "sync_duration_ms", 
        "api_calls_count",
        "conflicts"
    ]
    
    for col in expected_columns:
        assert f"add_column('sync_metadata'" in content
        assert col in content
    print("✓ Migration 007 adds required columns to sync_metadata")
    
    # Test 3: Check constraints are added
    expected_constraints = [
        "valid_resolution_strategy",
        "non_negative_duration",
        "non_negative_api_calls"
    ]
    
    for constraint in expected_constraints:
        assert f"create_check_constraint" in content
        assert constraint in content
    print("✓ Migration 007 adds check constraints")
    
    # Test 4: Performance index is added
    assert "create_index('idx_sync_performance'" in content
    assert "sync_duration_ms" in content and "api_calls_count" in content
    print("✓ Migration 007 adds performance index")
    
    # Test 5: Downgrade function exists
    assert "def downgrade()" in content
    assert "drop_index('idx_sync_performance'" in content
    assert "drop_constraint" in content
    print("✓ Migration 007 has correct downgrade function")
    
    return True

def test_migration_008_sprint_jira_metadata():
    """Test migration 008 adds JIRA metadata to Sprint model."""
    print("\nTesting Migration 008 (Sprint JIRA metadata)...")
    
    migration_file = Path("alembic/versions/008_add_sprint_jira_metadata.py")
    content = migration_file.read_text()
    
    # Test 1: Migration metadata is correct
    assert "revision = '008_add_sprint_jira_metadata'" in content
    assert "down_revision = '007_align_sync_schema'" in content
    print("✓ Migration 008 metadata is correct")
    
    # Test 2: JIRA sync metadata fields are added
    sync_fields = [
        "jira_last_updated",
        "sync_status", 
        "sync_conflicts"
    ]
    
    for field in sync_fields:
        assert f"add_column('sprints'" in content
        assert field in content
    print("✓ Migration 008 adds JIRA sync metadata fields")
    
    # Test 3: Enhanced JIRA metadata fields are added
    jira_fields = [
        "jira_board_name",
        "jira_project_key",
        "jira_version"
    ]
    
    for field in jira_fields:
        assert f"add_column('sprints'" in content
        assert field in content
    print("✓ Migration 008 adds enhanced JIRA metadata fields")
    
    # Test 4: Check constraint for sync_status is added
    assert "create_check_constraint" in content
    assert "valid_sync_status" in content
    assert "pending" in content and "completed" in content
    print("✓ Migration 008 adds sync_status check constraint")
    
    # Test 5: Indexes are created
    expected_indexes = [
        "idx_sprint_sync_status",
        "idx_sprint_project_key"
    ]
    
    for index in expected_indexes:
        assert f"create_index('{index}'" in content
    print("✓ Migration 008 creates required indexes")
    
    # Test 6: Downgrade function exists
    assert "def downgrade()" in content
    assert "drop_index('idx_sprint_project_key'" in content
    assert "drop_constraint('valid_sync_status'" in content
    print("✓ Migration 008 has correct downgrade function")
    
    return True

def test_migration_dependency_chain():
    """Test that migrations form a correct dependency chain."""
    print("\nTesting migration dependency chain...")
    
    migrations = [
        ("005_update_webhook_events_schema.py", "005_update_webhook_events_schema", "004_add_webhook_tables"),
        ("007_align_sync_schema.py", "007_align_sync_schema", "005_update_webhook_events_schema"),
        ("008_add_sprint_jira_metadata.py", "008_add_sprint_jira_metadata", "007_align_sync_schema")
    ]
    
    for filename, revision, down_revision in migrations:
        migration_file = Path(f"alembic/versions/{filename}")
        content = migration_file.read_text()
        
        assert f"revision = '{revision}'" in content
        assert f"down_revision = '{down_revision}'" in content
        print(f"✓ {filename} has correct dependency chain")
    
    print("✓ All migrations form correct dependency chain")
    return True

def test_model_table_alignment():
    """Test that model definitions align with migration table names."""
    print("\nTesting model-migration table alignment...")
    
    # Test WebhookEvent model uses correct table
    webhook_file = Path("app/models/webhook_event.py")
    webhook_content = webhook_file.read_text()
    assert '__tablename__ = "webhook_events"' in webhook_content
    print("✓ WebhookEvent model uses correct table name")
    
    # Test SyncState model uses sync_metadata table (unified approach)
    sync_file = Path("app/models/sync_state.py")
    sync_content = sync_file.read_text()
    assert '__tablename__ = "sync_metadata"' in sync_content
    print("✓ SyncState model uses sync_metadata table (unified approach)")
    
    # Test Sprint model uses sprints table
    sprint_file = Path("app/models/sprint.py")
    sprint_content = sprint_file.read_text()
    assert '__tablename__ = "sprints"' in sprint_content
    print("✓ Sprint model uses correct table name")
    
    return True

def test_sql_syntax_validation():
    """Test that migration SQL operations are syntactically correct."""
    print("\nTesting SQL syntax in migrations...")
    
    migration_files = [
        "alembic/versions/005_update_webhook_events_schema.py",
        "alembic/versions/007_align_sync_schema.py", 
        "alembic/versions/008_add_sprint_jira_metadata.py"
    ]
    
    for migration_file in migration_files:
        # Test that the migration file can be compiled as valid Python
        try:
            content = Path(migration_file).read_text()
            compile(content, migration_file, 'exec')
            print(f"✓ {Path(migration_file).name} compiles as valid Python")
        except SyntaxError as e:
            print(f"❌ {Path(migration_file).name} has syntax error: {e}")
            return False
    
    return True

def main():
    """Run all database schema tests."""
    print("=== EPIC 3 DATABASE SCHEMA TESTING ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    tests = [
        test_migration_005_webhook_events,
        test_migration_007_sync_schema,
        test_migration_008_sprint_jira_metadata,
        test_migration_dependency_chain,
        test_model_table_alignment,
        test_sql_syntax_validation
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = test()
            if result:
                passed += 1
                print(f"✅ {test.__name__}: PASSED")
            else:
                failed += 1
                print(f"❌ {test.__name__}: FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__}: FAILED - {e}")
    
    print(f"\n{'='*60}")
    print(f"DATABASE SCHEMA TEST SUMMARY: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL DATABASE SCHEMA TESTS PASSED!")
        return True
    else:
        print(f"⚠️  {failed} TESTS FAILED")
        return False

if __name__ == "__main__":
    success = main()
    import sys
    sys.exit(0 if success else 1)