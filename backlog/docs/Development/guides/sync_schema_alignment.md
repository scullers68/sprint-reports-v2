# Sync Schema Alignment - Task 043 Implementation

## Overview

This document describes the database schema alignment implemented to resolve the mismatch between the existing `sync_metadata` table and the architectural specification for sync state management.

## Problem Statement

The original implementation had two separate sync-related table structures:

1. **`sync_metadata` table** (from migration 004) - Comprehensive sync tracking with detailed metadata
2. **`sync_states` table** (from migration 006) - Simplified architectural specification model

This duplication created:
- Schema inconsistency
- Potential data fragmentation
- Confusion about which model to use
- Maintenance overhead

## Solution

### Schema Unification

**Decision**: Consolidate to use the `sync_metadata` table as the single source of truth, enhanced with architectural specification requirements.

**Rationale**:
- `sync_metadata` already had comprehensive functionality
- Existing services were already using `sync_metadata`
- More efficient to extend existing table than maintain parallel structures

### Migration 007: `align_sync_schema`

The migration adds architectural specification columns to `sync_metadata`:

```sql
-- Added columns for architectural compliance
ALTER TABLE sync_metadata ADD COLUMN resolution_strategy VARCHAR(50);
ALTER TABLE sync_metadata ADD COLUMN sync_duration_ms INTEGER;
ALTER TABLE sync_metadata ADD COLUMN api_calls_count INTEGER DEFAULT 0;
ALTER TABLE sync_metadata ADD COLUMN conflicts JSON;
```

### Model Updates

#### SyncState Model Changes

Updated `app/models/sync_state.py` to:
- Map to `sync_metadata` table (changed `__tablename__`)
- Include all sync_metadata columns
- Add architectural specification fields
- Maintain validation and constraints
- Use `extend_existing=True` to avoid table conflicts

#### Backward Compatibility

- `SyncMetadata` model remains unchanged
- Both models now reference the same table
- Existing code continues to work
- New code can use either model

## Schema Structure

The unified `sync_metadata` table now includes:

### Entity Identification
- `entity_type` - Type of entity (sprint, issue, project, board)
- `entity_id` - Internal entity identifier
- `jira_id` - JIRA entity identifier

### Sync Status & Timing
- `sync_status` - Current sync status (pending, in_progress, completed, failed, skipped)
- `last_sync_attempt` - Last sync attempt timestamp
- `last_successful_sync` - Last successful sync timestamp

### Error Tracking
- `error_count` - Number of sync errors
- `last_error` - Last error message

### Sync Metadata
- `sync_direction` - Sync direction (local_to_remote, remote_to_local, bidirectional)
- `sync_batch_id` - Batch identifier for grouped operations
- `content_hash` - Content hash for change detection

### Architectural Compliance Extensions
- `conflicts` - JSON field for conflict details
- `resolution_strategy` - Conflict resolution strategy (auto, manual, jira_wins, local_wins)
- `sync_duration_ms` - Sync duration in milliseconds
- `api_calls_count` - Number of API calls made

### Change Detection
- `local_modified` - Local modification timestamp
- `remote_modified` - Remote modification timestamp

## Usage Examples

### Using SyncState Model (Architectural Approach)

```python
from app.models.sync_state import SyncState
from app.services.sync_state_service import SyncStateService

# Create sync state
sync_state = await sync_service.create_sync_state(
    entity_type="sprint",
    entity_id="123",
    jira_id="JIRA-456"
)

# Record conflicts
await sync_service.record_conflict(
    sync_state,
    conflicts={"field": "name", "local": "Local Name", "remote": "Remote Name"},
    resolution_strategy="manual"
)
```

### Using SyncMetadata Model (Legacy Compatibility)

```python
from app.models.sprint import SyncMetadata

# Existing code continues to work
sync_metadata = SyncMetadata(
    entity_type="sprint",
    entity_id="123",
    jira_id="JIRA-456",
    sync_status=SyncStatus.PENDING
)
```

## Services

### SyncStateService

New service (`app/services/sync_state_service.py`) provides:
- Clean API for sync state management
- Architectural specification compliance
- Performance tracking
- Conflict management
- Statistics and reporting

### Existing SyncService

Continues to work with `SyncMetadata` model. Can be gradually migrated to use `SyncState` model for new features.

## Database Migration

### Applying the Migration

```bash
# Apply the migration
alembic upgrade head
```

### Rollback if Needed

```bash
# Rollback the migration
alembic downgrade 006
```

## Validation

Schema alignment was validated with `test_sync_schema.py`:

```
✓ Successfully imported SyncState and SyncMetadata models
✓ All required columns present
✓ Both models map to the same table (sync_metadata)
✓ Both models successfully reference the same table schema
✓ Database schema alignment completed successfully
```

## Migration Path

### Immediate (Post-Migration)
- Both models reference the same table
- All existing functionality preserved
- New features can use either model

### Future Consolidation (Optional)
- Gradually migrate services to use SyncState model
- Eventually deprecate SyncMetadata model
- Maintain single architectural approach

## Benefits

1. **Schema Consistency** - Single source of truth for sync data
2. **Architectural Compliance** - Meets specification requirements
3. **Backward Compatibility** - No breaking changes
4. **Performance** - No duplicate storage
5. **Maintainability** - Simpler codebase over time

## Files Modified

- `alembic/versions/007_align_sync_schema.py` - New migration
- `app/models/sync_state.py` - Updated to map to sync_metadata table
- `app/services/sync_state_service.py` - New architectural service
- `docs/sync_schema_alignment.md` - This documentation

## Files Removed

- `alembic/versions/006_add_sync_states_table.py` - Redundant migration removed

## Conclusion

The schema alignment successfully resolves the database mismatch while maintaining full backward compatibility. The solution provides a clean migration path toward architectural compliance without disrupting existing functionality.