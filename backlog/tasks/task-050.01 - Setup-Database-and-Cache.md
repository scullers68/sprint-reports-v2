---
id: task-050.01
title: Setup Database and Cache
status: In Progress
assignee: []
created_date: '2025-08-02'
updated_date: '2025-08-02'
labels:
  - mvp
  - database
  - infrastructure
dependencies: []
---

## Description

Set up PostgreSQL database and Redis cache using Docker Compose, run all migrations, and create initial admin user. This task resolves the "Database Not Running" critical issue identified in the health check.

## Acceptance Criteria

- [ ] PostgreSQL container running and accessible
- [ ] Redis container running and accessible
- [ ] All database migrations applied successfully
- [ ] Initial admin user created with credentials
- [ ] Database connection pool configured
- [ ] Health check endpoints responding
- [ ] Sample sprint data seeded for testing

## Implementation Approach

### Step 1: Docker Compose Setup
**File**: `/docker-compose.yml`
- Ensure PostgreSQL service is properly configured
- Ensure Redis service is properly configured
- Configure proper volumes for data persistence
- Set appropriate environment variables

### Step 2: Database Migrations
**Files**: `/app/database/migrations/`
- Run all existing Alembic migrations
- Verify schema matches current models
- Check for any migration conflicts

### Step 3: Admin User Creation
**File**: `/scripts/create_admin.py` (create if needed)
- Create initial admin user
- Set secure default password
- Assign admin role and permissions

### Step 4: Data Seeding
**File**: `/scripts/seed_sample_data.py` (create if needed)
- Create sample sprint data
- Create sample team and user data
- Create sample JIRA configuration

## Technical Details

### Database Configuration
```bash
# Start services
docker-compose up -d postgres redis

# Run migrations
alembic upgrade head

# Create admin user
python scripts/create_admin.py
```

### Connection Testing
```python
# Test database connection
from app.database.connection import get_db_session
session = get_db_session()
# Should connect without errors
```

### Health Checks
- Database: `SELECT 1` query succeeds
- Redis: `PING` command succeeds
- Connection pool: Active connections < max_connections

## Files to Modify

1. **`/docker-compose.yml`**
   - Verify PostgreSQL and Redis services
   - Ensure correct environment variables
   - Configure volumes and networking

2. **`/app/core/config.py`**
   - Simplify database configuration
   - Set development defaults
   - Reduce required environment variables

3. **`/app/database/connection.py`**
   - Enable database initialization
   - Configure connection pooling
   - Add connection health checks

4. **`/scripts/create_admin.py`** (create)
   - Admin user creation script
   - Default credentials configuration
   - Role assignment logic

## Success Criteria

- `docker-compose ps` shows postgres and redis as healthy
- `alembic current` shows migrations applied
- Admin login works via API
- Health endpoint returns database status
- Sample data visible in database tables

## Estimated Effort

**Time**: 4-6 hours
**Complexity**: Medium
**Dependencies**: None

## Testing Checklist

- [ ] Docker containers start successfully
- [ ] Database accepts connections
- [ ] Redis accepts connections  
- [ ] Migrations run without errors
- [ ] Admin user can authenticate
- [ ] Sample data loads correctly
- [ ] Health checks return success
