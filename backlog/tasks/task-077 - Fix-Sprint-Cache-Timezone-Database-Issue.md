---
id: task-077
title: Fix Sprint Cache Timezone Database Issue
status: To Do
priority: P0
assignee: []
created_date: '2025-08-04'
updated_date: '2025-08-04'
labels: [critical, bug, database, timezone]
dependencies: []
---

## Description

**CRITICAL BUG**: Sprint cache service is failing to insert sprint data into PostgreSQL due to timezone handling conflicts between JIRA API responses and database expectations.

## Problem Analysis

The backend successfully connects to JIRA and fetches sprint data, but database insertion fails with:
```
Error processing sprint: can't subtract offset-naive and offset-aware datetimes
asyncpg.exceptions.DataError: invalid input for query argument $5: 
datetime.datetime(2020, 4, 2, 9, 3, 36, 6000, tzinfo=datetime.timezone.utc)
```

**Root Cause**: JIRA API returns timezone-aware datetimes, but the database model/SQLAlchemy expects timezone-naive datetimes.

## Impact

- ❌ Sprint cache remains empty (0 sprints cached)
- ❌ Sprint discovery functionality not working
- ❌ Core analytics features blocked
- ❌ User sees "No sprints found" despite JIRA connection working

## Acceptance Criteria

- [x] Analyze timezone handling in sprint cache service
- [ ] Fix datetime conversion for JIRA API responses
- [ ] Ensure database insertion works with timezone-aware datetimes
- [ ] Verify sprint cache populates with real JIRA data
- [ ] Test sprint discovery functionality returns cached sprints
- [ ] Add proper error handling for timezone conversion failures

## Technical Analysis

### Files Involved
- `backend/app/services/sprint_cache_service.py` - Contains timezone conversion logic
- `backend/app/models/cached_sprint.py` - Database model with datetime fields
- JIRA API responses contain: `"startDate": "2020-04-02T09:03:36.006Z"`

### Current Error Pattern
```python
# JIRA API returns timezone-aware datetime
start_date = datetime.datetime(2020, 4, 2, 9, 3, 36, 6000, tzinfo=datetime.timezone.utc)

# Database expects timezone-naive datetime  
# SQLAlchemy Column: start_date = Column(DateTime)  # Should be DateTime(timezone=True)
```

## Implementation Plan

### Phase 1: Database Model Fix
1. **Update CachedSprint model** (`cached_sprint.py`):
   - Change `DateTime` columns to `DateTime(timezone=True)` for timezone-aware storage
   - Update migration to handle existing data

### Phase 2: Service Layer Fix  
2. **Update SprintCacheService** (`sprint_cache_service.py`):
   - Ensure proper timezone handling for JIRA datetime parsing
   - Add timezone conversion utilities if needed
   - Handle None/missing datetime values gracefully

### Phase 3: Validation & Testing
3. **Verify functionality**:
   - Test database insertion with timezone-aware datetimes
   - Confirm sprint cache populates with real JIRA data
   - Validate sprint search returns cached results
   - Test background refresh service continues working

## Current Background Service Status

✅ **Working Components**:
- JIRA API connection established
- Background service running and scheduled (every 2 hours)
- Sprint data successfully fetched from JIRA
- Service logs show "Successfully refreshed" attempts

❌ **Failing Components**:
- Database insertion due to timezone conflicts
- Sprint cache remains empty
- Sprint discovery returns no results

## Error Log Example

```
Error processing sprint 4: This Session's transaction has been rolled back due to a previous exception during flush.
Original exception was: (sqlalchemy.dialects.postgresql.asyncpg.Error) 
<class 'asyncpg.exceptions.DataError'>: invalid input for query argument $5: 
datetime.datetime(2020, 4, 2, 9, 3, 36, 6000, tzinfo=datetime.timezone.utc)
(can't subtract offset-naive and offset-aware datetimes)
```

## Expected Outcome

After fix implementation:
- ✅ Background service successfully caches sprints from JIRA
- ✅ Sprint discovery returns active and future sprints (e.g., "US EMEA INFRA SP-15", "US EMEA INFRA SP-16")
- ✅ Frontend shows cached sprint count and statistics
- ✅ Users can search and find relevant sprints for analytics

## Priority Justification

**P0 Critical** because:
1. **Blocks Core Functionality**: Sprint discovery is the primary feature
2. **User-Facing Impact**: Users see empty results despite working JIRA connection
3. **Analytics Foundation**: All reporting features depend on cached sprint data
4. **Simple Fix**: Likely only requires timezone column configuration changes

This is the highest priority issue blocking user value delivery.