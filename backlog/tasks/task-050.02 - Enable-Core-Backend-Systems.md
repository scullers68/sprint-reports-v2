---
id: task-050.02
title: Enable Core Backend Systems
status: In Progress
assignee: []
created_date: '2025-08-02'
updated_date: '2025-08-02'
labels:
  - mvp
  - backend
  - api
dependencies:
  - task-050.01
---

## Description

Re-enable disabled core systems (database initialization, audit system) and fix environment configuration to get the backend API fully operational. This addresses the "Disabled Core Systems" critical issue from the health check.

## Acceptance Criteria

- [ ] Database initialization system re-enabled and working
- [ ] Audit system re-enabled for user actions
- [ ] Environment variables reduced from 150+ to <20 required
- [ ] Authentication endpoints responding correctly
- [ ] User CRUD operations working
- [ ] Sprint CRUD operations working
- [ ] API documentation accessible at `/docs`

## Implementation Approach

### Step 1: Re-enable Database Initialization
**Files**: `/app/core/database.py`, `/app/main.py`
- Uncomment database initialization code
- Ensure startup hooks are active
- Add proper error handling

### Step 2: Re-enable Audit System
**Files**: `/app/core/audit.py`, `/app/models/audit.py`
- Uncomment audit logging code
- Ensure audit middleware is active
- Test audit trail creation

### Step 3: Simplify Environment Configuration
**File**: `/app/core/config.py`
- Create development defaults for non-critical settings
- Mark optional environment variables
- Create `.env.development` template

### Step 4: Fix Core API Endpoints
**Files**: `/app/api/v1/users.py`, `/app/api/v1/sprints.py`
- Ensure endpoints are working
- Fix any broken imports
- Add proper error handling

## Technical Details

### Environment Variables Reduction
**Essential Variables Only** (<20):
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/sprint_reports
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# Basic Config
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=info
```

### Database Initialization Fix
```python
# In app/main.py - uncomment this
@app.on_event("startup")
async def startup_event():
    await initialize_database()
    await setup_audit_system()
```

### Audit System Re-enablement
```python
# In app/core/audit.py - ensure this is active
async def log_user_action(user_id: int, action: str, details: dict):
    # Audit logging implementation
    pass
```

## Files to Modify

1. **`/app/core/config.py`**
   - Reduce required environment variables
   - Add development defaults
   - Create optional vs required distinction

2. **`/app/main.py`**
   - Re-enable startup event handlers
   - Uncomment database initialization
   - Add audit system startup

3. **`/app/core/database.py`**
   - Uncomment initialization functions
   - Add proper error handling
   - Ensure connection pooling works

4. **`/app/core/audit.py`**
   - Re-enable audit logging
   - Ensure audit middleware is active
   - Test audit trail functionality

5. **`/.env.development`** (create)
   - Development environment template
   - All required variables with defaults
   - Clear documentation

## API Endpoints to Test

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout
- `GET /api/v1/auth/me` - Current user info

### Users
- `GET /api/v1/users/` - List users
- `POST /api/v1/users/` - Create user
- `GET /api/v1/users/{id}` - Get user
- `PUT /api/v1/users/{id}` - Update user

### Sprints
- `GET /api/v1/sprints/` - List sprints
- `POST /api/v1/sprints/` - Create sprint
- `GET /api/v1/sprints/{id}` - Get sprint

## Success Criteria

- `curl http://localhost:8000/health` returns 200 OK
- API documentation accessible at `http://localhost:8000/docs`
- Admin user can login via API
- User and sprint endpoints respond correctly
- Audit logs are created for user actions
- Backend starts with <20 environment variables

## Estimated Effort

**Time**: 6-8 hours
**Complexity**: Medium-High
**Dependencies**: Database setup (task-050.01)

## Testing Checklist

- [ ] Backend starts without errors
- [ ] Database initialization runs successfully
- [ ] Audit system logs user actions
- [ ] Authentication endpoints work
- [ ] CRUD operations work for users and sprints
- [ ] API documentation is accessible
- [ ] Environment setup takes <5 minutes
