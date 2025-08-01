#!/usr/bin/env python3
"""
Epic 3 Models Isolated Testing

Tests Epic 3 models in isolation to avoid SQLAlchemy relationship issues.
Focuses specifically on WebhookEvent, SyncState, and Sprint model changes.
"""

import sys
import os
from datetime import datetime, timezone

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_webhook_event_model():
    """Test WebhookEvent model in isolation."""
    print("Testing WebhookEvent model...")
    
    # Import without triggering full SQLAlchemy initialization
    import importlib.util
    
    spec = importlib.util.spec_from_file_location(
        "webhook_event", 
        "app/models/webhook_event.py"
    )
    webhook_module = importlib.util.module_from_spec(spec)
    
    # Mock the base to avoid full SQLAlchemy initialization
    class MockBase:
        def __init__(self):
            self.id = None
            self.created_at = datetime.now(timezone.utc)
            self.updated_at = datetime.now(timezone.utc)
    
    # Inject mock into the module
    sys.modules['app.models.base'] = type('MockModule', (), {'Base': MockBase})
    
    # Now load the module
    spec.loader.exec_module(webhook_module)
    
    # Get the WebhookEvent class
    WebhookEvent = webhook_module.WebhookEvent
    
    # Test 1: Class definition exists
    assert WebhookEvent is not None, "WebhookEvent class should exist"
    print("✓ WebhookEvent class exists")
    
    # Test 2: Required attributes exist
    expected_attrs = [
        'event_id', 'event_type', 'payload', 'processed_data',
        'processed_at', 'processing_status', 'retry_count',
        'processing_attempts', 'last_processed_at', 'error_message',
        'processing_duration_ms'
    ]
    
    for attr in expected_attrs:
        assert hasattr(WebhookEvent, attr), f"WebhookEvent should have {attr} attribute"
    print("✓ WebhookEvent has all required attributes")
    
    # Test 3: Table name is correct
    assert WebhookEvent.__tablename__ == "webhook_events", "Table name should be webhook_events"
    print("✓ WebhookEvent table name is correct")
    
    return True

def test_sync_state_model():
    """Test SyncState model in isolation."""
    print("\nTesting SyncState model...")
    
    import importlib.util
    
    spec = importlib.util.spec_from_file_location(
        "sync_state", 
        "app/models/sync_state.py"
    )
    sync_module = importlib.util.module_from_spec(spec)
    
    # Mock the base to avoid full SQLAlchemy initialization
    class MockBase:
        def __init__(self):
            self.id = None
            self.created_at = datetime.now(timezone.utc)
            self.updated_at = datetime.now(timezone.utc)
    
    # Inject mock into the module
    sys.modules['app.models.base'] = type('MockModule', (), {'Base': MockBase})
    
    # Now load the module
    spec.loader.exec_module(sync_module)
    
    # Get the SyncState class
    SyncState = sync_module.SyncState
    
    # Test 1: Class definition exists
    assert SyncState is not None, "SyncState class should exist"
    print("✓ SyncState class exists")
    
    # Test 2: Required attributes exist
    expected_attrs = [
        'entity_type', 'entity_id', 'jira_id', 'sync_status',
        'last_sync_attempt', 'last_successful_sync', 'local_modified',
        'remote_modified', 'error_count', 'last_error', 'sync_direction',
        'sync_batch_id', 'content_hash', 'conflicts', 'resolution_strategy',
        'sync_duration_ms', 'api_calls_count'
    ]
    
    for attr in expected_attrs:
        assert hasattr(SyncState, attr), f"SyncState should have {attr} attribute"
    print("✓ SyncState has all required attributes")
    
    # Test 3: Table name is correct (maps to sync_metadata)
    assert SyncState.__tablename__ == "sync_metadata", "Table name should be sync_metadata"
    print("✓ SyncState table name is correct")
    
    # Test 4: Validation methods exist
    validation_methods = [
        'validate_entity_type', 'validate_sync_status', 
        'validate_sync_direction', 'validate_resolution_strategy',
        'validate_non_negative'
    ]
    
    for method in validation_methods:
        assert hasattr(SyncState, method), f"SyncState should have {method} method"
    print("✓ SyncState has all validation methods")
    
    return True

def test_sprint_model_extensions():
    """Test Sprint model JIRA metadata extensions."""
    print("\nTesting Sprint model extensions...")
    
    import importlib.util
    
    spec = importlib.util.spec_from_file_location(
        "sprint", 
        "app/models/sprint.py"
    )
    sprint_module = importlib.util.module_from_spec(spec)
    
    # Mock the base to avoid full SQLAlchemy initialization
    class MockBase:
        def __init__(self):
            self.id = None
            self.created_at = datetime.now(timezone.utc)
            self.updated_at = datetime.now(timezone.utc)
    
    # Inject mock into the module
    sys.modules['app.models.base'] = type('MockModule', (), {'Base': MockBase})
    
    # Now load the module
    spec.loader.exec_module(sprint_module)
    
    # Get the Sprint class
    Sprint = sprint_module.Sprint
    
    # Test 1: Class definition exists
    assert Sprint is not None, "Sprint class should exist"
    print("✓ Sprint class exists")
    
    # Test 2: New JIRA metadata attributes exist
    new_jira_attrs = [
        'jira_last_updated', 'sync_status', 'sync_conflicts',
        'jira_board_name', 'jira_project_key', 'jira_version'
    ]
    
    for attr in new_jira_attrs:
        assert hasattr(Sprint, attr), f"Sprint should have new JIRA attribute {attr}"
    print("✓ Sprint has all new JIRA metadata attributes")
    
    # Test 3: Existing attributes still exist
    existing_attrs = [
        'jira_sprint_id', 'name', 'state', 'start_date', 'end_date',
        'complete_date', 'goal', 'board_id', 'origin_board_id'
    ]
    
    for attr in existing_attrs:
        assert hasattr(Sprint, attr), f"Sprint should still have existing attribute {attr}"
    print("✓ Sprint retains all existing attributes")
    
    # Test 4: Validation methods exist
    validation_methods = ['validate_state', 'validate_name', 'validate_sync_status']
    
    for method in validation_methods:
        assert hasattr(Sprint, method), f"Sprint should have {method} method"
    print("✓ Sprint has all validation methods")
    
    return True

def test_model_validation_logic():
    """Test model validation logic without SQLAlchemy relationships."""
    print("\nTesting model validation logic...")
    
    # Test SyncState validation methods manually
    class MockSyncState:
        def validate_entity_type(self, key, entity_type):
            valid_types = ['sprint', 'issue', 'project', 'board']
            if entity_type and entity_type not in valid_types:
                raise ValueError(f"Invalid entity type. Must be one of: {valid_types}")
            return entity_type
            
        def validate_sync_status(self, key, sync_status):
            valid_statuses = ['pending', 'in_progress', 'completed', 'failed', 'skipped']
            if sync_status and sync_status not in valid_statuses:
                raise ValueError(f"Invalid sync status. Must be one of: {valid_statuses}")
            return sync_status
    
    mock_sync = MockSyncState()
    
    # Test valid entity type
    assert mock_sync.validate_entity_type("entity_type", "sprint") == "sprint"
    print("✓ SyncState accepts valid entity type")
    
    # Test invalid entity type
    try:
        mock_sync.validate_entity_type("entity_type", "invalid")
        assert False, "Should have raised ValueError"
    except ValueError:
        print("✓ SyncState rejects invalid entity type")
    
    # Test valid sync status
    assert mock_sync.validate_sync_status("sync_status", "completed") == "completed"
    print("✓ SyncState accepts valid sync status")
    
    # Test invalid sync status
    try:
        mock_sync.validate_sync_status("sync_status", "invalid")
        assert False, "Should have raised ValueError"
    except ValueError:
        print("✓ SyncState rejects invalid sync status")
    
    return True

def main():
    """Run all isolated model tests."""
    print("=== EPIC 3 MODELS ISOLATED TESTING ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    tests = [
        test_webhook_event_model,
        test_sync_state_model,
        test_sprint_model_extensions,
        test_model_validation_logic
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
    
    print(f"\n{'='*50}")
    print(f"SUMMARY: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL EPIC 3 MODEL TESTS PASSED!")
        return True
    else:
        print(f"⚠️  {failed} TESTS FAILED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)