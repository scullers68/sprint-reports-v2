---
id: task-050.03
title: Implement Missing Authentication Service Methods
status: To Do
assignee:
  - fullstack-engineer
created_date: '2025-08-02'
updated_date: '2025-08-02'
labels:
  - critical
  - authentication
  - epic-050
  - blocking-epic-051
dependencies:
  - task-050.01
  - task-050.02
---

## Description

Implement the missing core authentication methods in AuthenticationService that are causing 500 errors in the login and registration endpoints. The test-engineer identified that `authenticate_and_login()` and `register_user()` methods are missing, causing complete authentication workflow failure.

**CRITICAL ISSUE**: Authentication endpoints are calling non-existent methods:
- Line 58-61 in /backend/app/api/v1/endpoints/auth.py calls `auth_service.authenticate_and_login()` 
- Line 40 calls `auth_service.register_user()`
- Both methods are missing from AuthenticationService class

**PARENT TASKS**: This extends task-050.01 (Database Setup - COMPLETED) and task-050.02 (Backend Systems - COMPLETED).

## Acceptance Criteria

- [x] Add `authenticate_and_login(email: str, password: str)` method to AuthenticationService
- [x] Add `register_user(user_data: UserRegister)` method to AuthenticationService  
- [x] Implement proper JWT token generation in authenticate_and_login method
- [x] Add password hashing and validation in register_user method
- [x] Ensure methods return expected response format (user, token) for login
- [x] Add proper error handling for invalid credentials and duplicate users
- [x] Integrate with existing User model and RBAC system
- [x] Test methods work with existing admin user (admin@sprint-reports.com)

## Implementation Plan

### Step 1: Analyze Current AuthenticationService
- Review existing /backend/app/services/auth_service.py
- Identify missing methods and expected signatures
- Understand integration points with existing code

### Step 2: Implement authenticate_and_login Method
- Create method that combines authenticate_user + token creation
- Return tuple of (User, token) as expected by login endpoint
- Handle authentication failures with proper error messages
- Update last_login timestamp on successful authentication

### Step 3: Implement register_user Method
- Accept UserRegister schema as input
- Validate email uniqueness and format
- Hash password using existing password context
- Create User object with proper defaults
- Assign default role using RBAC system
- Return created User object

### Step 4: Integration Testing
- Test both methods with existing database
- Verify admin user authentication works
- Test user registration creates proper RBAC relationships
- Ensure JWT tokens are valid and parseable

### Files to Modify:
- `/backend/app/services/auth_service.py` - Add missing methods
- Test with existing endpoints without modification

## Success Criteria

- All authentication endpoints return proper HTTP status codes (not 500 errors)
- Admin user can authenticate successfully via API
- User registration workflow completes without errors
- Authentication methods integrate properly with existing RBAC system
- Epic 051 frontend development can proceed with working authentication APIs

## Testing Requirements

- Docker-based testing using: `./docker-compose-local.sh`
- Verify endpoints at http://localhost:3001
- Test authentication workflow end-to-end
- Validate against existing admin user (admin@sprint-reports.com)

## Epic 051 Readiness

This task is critical for unblocking Epic 051 (Frontend Application) development. The frontend cannot proceed without working authentication APIs.

