#!/usr/bin/env python3
"""
API Integration Testing for Epic 3

Tests that API endpoints correctly import and reference the new Epic 3 models.
Focuses on webhook endpoints and worker integration.
"""

import ast
import re
from pathlib import Path
from datetime import datetime

def test_webhook_endpoints_imports():
    """Test that webhook endpoints correctly import WebhookEvent model."""
    print("Testing webhook endpoints imports...")
    
    webhook_file = Path("app/api/v1/endpoints/webhooks.py")
    content = webhook_file.read_text()
    
    # Test 1: WebhookEvent model is imported
    assert "from app.models.webhook_event import WebhookEvent" in content
    print("✓ Webhook endpoints import WebhookEvent model")
    
    # Test 2: WebhookEvent is used in endpoint functions
    webhook_usage_patterns = [
        "WebhookEvent(",  # Constructor usage
        "select(WebhookEvent)",  # SQLAlchemy select usage
        "WebhookEvent.event_id",  # Attribute access
        "WebhookEvent.processing_status"  # Attribute access
    ]
    
    for pattern in webhook_usage_patterns:
        assert pattern in content, f"WebhookEvent pattern '{pattern}' not found"
    print("✓ Webhook endpoints use WebhookEvent model correctly")
    
    # Test 3: Endpoint functions exist
    expected_endpoints = [
        "@router.post(\"/jira\")",  # Main webhook receiver
        "@router.get(\"/events/{event_id}\")",  # Get event details
        "@router.get(\"/stats\")",  # Get webhook stats
        "@router.post(\"/events/{event_id}/retry\")"  # Retry failed events
    ]
    
    for endpoint in expected_endpoints:
        assert endpoint in content, f"Expected endpoint '{endpoint}' not found"
    print("✓ All expected webhook endpoints are defined")
    
    # Test 4: New WebhookEvent fields are used
    new_fields = [
        "processing_duration_ms",
        "retry_count", 
        "processed_at"
    ]
    
    for field in new_fields:
        assert field in content, f"New field '{field}' not used in endpoints"
    print("✓ New WebhookEvent fields are utilized in endpoints")
    
    return True

def test_webhook_processor_imports():
    """Test that webhook processor correctly imports and uses new models."""
    print("\nTesting webhook processor imports...")
    
    processor_file = Path("app/workers/webhook_processor.py")
    content = processor_file.read_text()
    
    # Test 1: Required models are imported
    required_imports = [
        "from app.models.webhook_event import WebhookEvent",
        "from app.models.queue import QueueItem, SprintQueue",
        "from app.models.sprint import Sprint"
    ]
    
    for import_statement in required_imports:
        assert import_statement in content, f"Missing import: {import_statement}"
    print("✓ Webhook processor imports all required models")
    
    # Test 2: WebhookEvent fields are accessed correctly
    webhook_fields = [
        "event.processing_status",
        "event.processing_attempts", 
        "event.last_processed_at",
        "event.payload",
        "event.processed_data"
    ]
    
    for field in webhook_fields:
        assert field in content, f"WebhookEvent field '{field}' not accessed"
    print("✓ Webhook processor accesses WebhookEvent fields")
    
    # Test 3: Processing functions exist
    processing_functions = [
        "def process_webhook_event(",
        "async def process_issue_event(",
        "async def process_sprint_event("
    ]
    
    for func in processing_functions:
        assert func in content, f"Processing function '{func}' not found"
    print("✓ All processing functions are defined")
    
    # Test 4: Error handling and status updates
    status_updates = [
        'event.processing_status = "processing"',
        'event.processing_status = "completed"',
        'event.processing_status = "failed"'
    ]
    
    for update in status_updates:
        assert update in content, f"Status update '{update}' not found"
    print("✓ Webhook processor updates processing status correctly")
    
    return True

def test_model_references_consistency():
    """Test that model references are consistent across files."""
    print("\nTesting model references consistency...")
    
    # Files that should reference WebhookEvent
    webhook_event_files = [
        "app/api/v1/endpoints/webhooks.py",
        "app/workers/webhook_processor.py"
    ]
    
    # Files that should reference Sprint with new fields
    sprint_files = [
        "app/workers/webhook_processor.py",
        "app/models/sprint.py"
    ]
    
    # Test WebhookEvent references
    for file_path in webhook_event_files:
        content = Path(file_path).read_text()
        assert "WebhookEvent" in content, f"{file_path} should reference WebhookEvent"
    print("✓ WebhookEvent references are consistent")
    
    # Test Sprint references
    for file_path in sprint_files:
        if Path(file_path).exists():
            content = Path(file_path).read_text()
            assert "Sprint" in content, f"{file_path} should reference Sprint"
    print("✓ Sprint references are consistent")
    
    return True

def test_api_error_handling():
    """Test that API endpoints have proper error handling for new models."""
    print("\nTesting API error handling...")
    
    webhook_file = Path("app/api/v1/endpoints/webhooks.py")
    content = webhook_file.read_text()
    
    # Test 1: HTTP exceptions are used
    http_exceptions = [
        "HTTPException",
        "status.HTTP_400_BAD_REQUEST",
        "status.HTTP_401_UNAUTHORIZED", 
        "status.HTTP_404_NOT_FOUND",
        "status.HTTP_500_INTERNAL_SERVER_ERROR"
    ]
    
    for exception in http_exceptions:
        assert exception in content, f"HTTP exception '{exception}' not used"
    print("✓ Proper HTTP exceptions are used")
    
    # Test 2: Error responses are structured
    error_responses = [
        "JSONResponse",
        '"status":', 
        "detail=",
        '"error_message":'
    ]
    
    for response in error_responses:
        assert response in content, f"Error response element '{response}' not found"
    print("✓ Error responses are properly structured")
    
    # Test 3: Try-catch blocks exist
    assert "try:" in content and "except" in content
    print("✓ Error handling with try-catch blocks exists")
    
    return True

def test_background_task_integration():
    """Test background task integration with new models."""
    print("\nTesting background task integration...")
    
    processor_file = Path("app/workers/webhook_processor.py")
    content = processor_file.read_text()
    
    # Test 1: Celery task decorators exist
    celery_decorators = [
        "@celery_app.task(bind=True, max_retries=3)",
        "@celery_app.task"
    ]
    
    for decorator in celery_decorators:
        assert decorator in content, f"Celery decorator '{decorator}' not found"
    print("✓ Celery task decorators are properly used")
    
    # Test 2: Async functions for database operations
    async_functions = [
        "async def _process_event",
        "async def process_issue_event",
        "async def process_sprint_event"
    ]
    
    for func in async_functions:
        assert func in content, f"Async function '{func}' not found"
    print("✓ Async functions for database operations exist")
    
    # Test 3: Database session management
    db_session_patterns = [
        "AsyncSessionLocal()",
        "async with",
        "await db.commit()",
        "await db.execute("
    ]
    
    for pattern in db_session_patterns:
        assert pattern in content, f"Database session pattern '{pattern}' not found"
    print("✓ Proper database session management")
    
    return True

def test_webhook_payload_processing():
    """Test webhook payload processing logic."""
    print("\nTesting webhook payload processing...")
    
    processor_file = Path("app/workers/webhook_processor.py")
    content = processor_file.read_text()
    
    # Test 1: Payload extraction functions
    extraction_patterns = [
        "payload.get(",
        "issue_data.get(",
        "sprint_data.get(",
        "processed_data ="
    ]
    
    for pattern in extraction_patterns:
        assert pattern in content, f"Payload extraction pattern '{pattern}' not found"
    print("✓ Payload extraction logic exists")
    
    # Test 2: Event type handling
    event_types = [
        "jira:issue",
        "jira:sprint"
    ]
    
    for event_type in event_types:
        assert event_type in content, f"Event type '{event_type}' not handled"
    print("✓ Different event types are handled")
    
    return True

def main():
    """Run all API integration tests."""
    print("=== EPIC 3 API INTEGRATION TESTING ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    tests = [
        test_webhook_endpoints_imports,
        test_webhook_processor_imports,
        test_model_references_consistency,
        test_api_error_handling,
        test_background_task_integration,
        test_webhook_payload_processing
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
    print(f"API INTEGRATION TEST SUMMARY: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL API INTEGRATION TESTS PASSED!")
        return True
    else:
        print(f"⚠️  {failed} TESTS FAILED")
        return False

if __name__ == "__main__":
    success = main()
    import sys
    sys.exit(0 if success else 1)