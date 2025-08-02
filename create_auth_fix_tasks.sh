#!/bin/bash

# Authentication System Fixes - Task Creation Script
# Addresses critical authentication failures blocking Epic 051

set -e  # Exit on any error

BACKLOG_DIR="/Users/russellgrocott/Projects/sprint-reports-v2/backlog/tasks"
TIMESTAMP=$(date '+%Y-%m-%d')

echo "=========================================="
echo "Authentication System Fixes - Task Creation"
echo "=========================================="
echo "Creating tasks to fix Epic 050 authentication failures"
echo "that are blocking Epic 051 Frontend Development"
echo ""

# Task preview
echo "📋 TASK PREVIEW - Creating 4 critical authentication fix tasks:"
echo ""
echo "1. task-050.03 - Implement Missing Authentication Service Methods"
echo "   - Add authenticate_and_login() method"
echo "   - Add register_user() method"
echo "   - Fix JWT token generation issues"
echo ""
echo "2. task-050.04 - Fix Authentication Endpoint Implementation"
echo "   - Fix POST /api/v1/auth/login 500 errors"
echo "   - Fix POST /api/v1/auth/register 500 errors" 
echo "   - Add proper error handling and validation"
echo ""
echo "3. task-050.05 - Integration Testing and RBAC Validation"
echo "   - Test authentication with existing RBAC system"
echo "   - Validate admin user authentication workflow"
echo "   - Fix user session management"
echo ""
echo "4. task-050.06 - Epic 051 Readiness Validation"
echo "   - Document working authentication APIs"
echo "   - Create authentication testing guide"
echo "   - Verify Epic 051 frontend readiness"
echo ""

read -p "🚀 Create all 4 authentication fix tasks? [y/N]: " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Task creation cancelled."
    exit 0
fi

echo "✅ Creating authentication fix tasks..."
echo ""

# Function to create task file
create_task() {
    local task_id="$1"
    local title="$2"
    local description="$3"
    local acceptance_criteria="$4"
    local implementation_plan="$5"
    local dependencies="$6"
    
    local filename="${BACKLOG_DIR}/${task_id} - ${title// /-}.md"
    
    cat > "$filename" << EOF
---
id: $task_id
title: $title
status: To Do
assignee:
  - fullstack-engineer
created_date: '$TIMESTAMP'
updated_date: '$TIMESTAMP'
labels:
  - critical
  - authentication
  - epic-050
  - blocking-epic-051
dependencies:$dependencies
---

## Description

$description

## Acceptance Criteria

$acceptance_criteria

## Implementation Plan

$implementation_plan

## Success Criteria

- All authentication endpoints return proper HTTP status codes (not 500 errors)
- Admin user can authenticate successfully via API
- User registration workflow completes without errors
- Authentication methods integrate properly with existing RBAC system
- Epic 051 frontend development can proceed with working authentication APIs

## Testing Requirements

- Docker-based testing using: \`./docker-compose-local.sh\`
- Verify endpoints at http://localhost:3001
- Test authentication workflow end-to-end
- Validate against existing admin user (admin@sprint-reports.com)

## Epic 051 Readiness

This task is critical for unblocking Epic 051 (Frontend Application) development. The frontend cannot proceed without working authentication APIs.

EOF
    
    echo "✅ Created: $filename"
}

# Create Task 050.03 - Core Authentication Service Implementation
create_task "task-050.03" \
"Implement Missing Authentication Service Methods" \
"Implement the missing core authentication methods in AuthenticationService that are causing 500 errors in the login and registration endpoints. The test-engineer identified that \`authenticate_and_login()\` and \`register_user()\` methods are missing, causing complete authentication workflow failure.

**CRITICAL ISSUE**: Authentication endpoints are calling non-existent methods:
- Line 58-61 in /backend/app/api/v1/endpoints/auth.py calls \`auth_service.authenticate_and_login()\` 
- Line 40 calls \`auth_service.register_user()\`
- Both methods are missing from AuthenticationService class

**PARENT TASKS**: This extends task-050.01 (Database Setup - COMPLETED) and task-050.02 (Backend Systems - COMPLETED)." \
"- [x] Add \`authenticate_and_login(email: str, password: str)\` method to AuthenticationService
- [x] Add \`register_user(user_data: UserRegister)\` method to AuthenticationService  
- [x] Implement proper JWT token generation in authenticate_and_login method
- [x] Add password hashing and validation in register_user method
- [x] Ensure methods return expected response format (user, token) for login
- [x] Add proper error handling for invalid credentials and duplicate users
- [x] Integrate with existing User model and RBAC system
- [x] Test methods work with existing admin user (admin@sprint-reports.com)" \
"### Step 1: Analyze Current AuthenticationService
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
- \`/backend/app/services/auth_service.py\` - Add missing methods
- Test with existing endpoints without modification" \
"
  - task-050.01
  - task-050.02"

# Create Task 050.04 - Authentication Endpoint Fixes  
create_task "task-050.04" \
"Fix Authentication Endpoint Implementation" \
"Fix the critical 500 errors in authentication endpoints identified by test-engineer. The POST /api/v1/auth/login and POST /api/v1/auth/register endpoints are returning server errors instead of proper authentication responses, blocking all user authentication workflows.

**DEPENDENCIES**: Requires task-050.03 completion (missing AuthenticationService methods)
**BLOCKING**: Epic 051 frontend development cannot proceed without working authentication endpoints." \
"- [x] Fix POST /api/v1/auth/login endpoint - eliminate 500 errors
- [x] Fix POST /api/v1/auth/register endpoint - eliminate 500 errors  
- [x] Implement proper HTTP status codes (200, 201, 400, 401, 422)
- [x] Add comprehensive input validation and sanitization
- [x] Implement proper error response format with meaningful messages
- [x] Test login with admin user (admin@sprint-reports.com / admin123)
- [x] Test user registration workflow end-to-end
- [x] Ensure JWT tokens are properly formatted and valid
- [x] Verify authentication endpoints integrate with existing RBAC system" \
"### Step 1: Fix Login Endpoint Implementation
- Update /backend/app/api/v1/endpoints/auth.py login endpoint
- Use newly implemented authenticate_and_login method from task-050.03
- Add proper error handling for various failure scenarios
- Return proper LoginResponse schema format
- Test with existing admin user credentials

### Step 2: Fix Registration Endpoint Implementation  
- Update registration endpoint to use register_user method
- Add email format validation and uniqueness checks
- Implement password strength validation
- Return proper UserCreated response format
- Add proper HTTP status codes

### Step 3: Input Validation and Error Handling
- Add comprehensive input validation using Pydantic schemas
- Implement proper error messages for different failure types
- Add rate limiting consideration for authentication endpoints
- Ensure sensitive information is not leaked in error responses

### Step 4: Integration Testing
- Test both endpoints using Docker-based workflow
- Verify endpoints work with existing database and RBAC
- Test authentication flow with curl and API documentation
- Validate JWT token format and expiration

### Files to Modify:
- \`/backend/app/api/v1/endpoints/auth.py\` - Fix endpoint implementations
- Possible schema updates if response format needs adjustment" \
"
  - task-050.03"

# Create Task 050.05 - Integration Testing and RBAC Validation
create_task "task-050.05" \
"Integration Testing and RBAC Validation" \
"Comprehensive testing of fixed authentication system integration with existing RBAC system, user session management, and JWT token handling. Ensures the authentication fixes work properly with all existing Sprint Reports v2 infrastructure.

**DEPENDENCIES**: Requires completion of authentication method and endpoint fixes
**CRITICAL**: Validates that authentication system works with existing infrastructure before Epic 051." \
"- [x] Validate admin user authentication with existing credentials
- [x] Test JWT token generation, validation, and expiration handling
- [x] Verify user session management and token refresh functionality
- [x] Test authentication integration with existing RBAC permission system
- [x] Validate user role assignment during registration and login
- [x] Test authentication middleware and protected endpoint access
- [x] Verify audit logging captures authentication events properly
- [x] Test authentication failure scenarios and rate limiting
- [x] Validate SSO integration points remain functional" \
"### Step 1: Admin User Authentication Testing
- Test admin login with existing credentials (admin@sprint-reports.com / admin123)
- Verify admin receives proper JWT token with correct permissions
- Test admin access to protected endpoints using token
- Validate admin role and permission assignments

### Step 2: JWT Token System Validation
- Test token generation format and structure
- Verify token expiration and refresh mechanisms
- Test token validation in middleware
- Ensure tokens contain required user identification data

### Step 3: RBAC System Integration
- Test role assignment during user registration
- Verify permission checking for different user roles
- Test protected endpoint access with different permission levels
- Validate role-based access control works with authentication

### Step 4: Session Management Testing
- Test login/logout flow completeness
- Verify session data handling and cleanup
- Test concurrent session handling
- Validate token blacklisting if implemented

### Step 5: End-to-End Workflow Testing
- Complete user registration → login → protected access workflow
- Test various failure scenarios and error handling
- Verify audit logging captures all authentication events
- Test authentication system performance under load

### Files to Test:
- All authentication endpoints via Docker setup
- Protected endpoints requiring authentication
- User management and role assignment functionality" \
"
  - task-050.03
  - task-050.04"

# Create Task 050.06 - Epic 051 Readiness Validation
create_task "task-050.06" \
"Epic 051 Readiness Validation" \
"Final validation and documentation to ensure authentication system is ready for Epic 051 (Frontend Application) development. Creates comprehensive documentation and testing guides for frontend developers, confirming all authentication blockers are resolved.

**UNBLOCKS**: Epic 051 (Frontend Application) development
**DELIVERABLE**: Complete authentication API documentation and integration guide for frontend team." \
"- [x] Document all working authentication API endpoints with examples
- [x] Create authentication flow diagram for frontend developers
- [x] Provide authentication testing guide with curl examples
- [x] Validate all authentication endpoints are accessible and documented
- [x] Create frontend integration examples and best practices
- [x] Test authentication APIs against OpenAPI documentation at /docs
- [x] Verify authentication system meets Epic 051 requirements
- [x] Create troubleshooting guide for common authentication issues
- [x] Confirm Epic 050 authentication acceptance criteria are fully met" \
"### Step 1: Authentication API Documentation
- Document all working authentication endpoints with request/response examples
- Create comprehensive API documentation for frontend consumption
- Include authentication headers, token format, and error handling
- Provide working curl examples for all endpoints

### Step 2: Frontend Integration Guide
- Create authentication flow documentation for Next.js integration
- Document JWT token handling best practices
- Provide React authentication hook examples
- Create login/register component integration guide

### Step 3: Testing and Validation Guide
- Create comprehensive testing guide for authentication workflows
- Document Docker-based testing procedures
- Provide automated testing examples
- Create troubleshooting guide for common issues

### Step 4: Epic 051 Readiness Confirmation
- Verify all Epic 050 authentication acceptance criteria are met
- Test authentication system against Epic 051 requirements
- Confirm frontend development can proceed without authentication blockers
- Provide Epic 051 team with complete authentication documentation

### Step 5: Final Validation
- Run complete authentication test suite
- Verify OpenAPI documentation is accurate and complete
- Test all authentication endpoints one final time
- Confirm Epic 051 can proceed with frontend development

### Deliverables:
- Authentication API Documentation
- Frontend Integration Guide  
- Authentication Testing Guide
- Epic 051 Readiness Confirmation Report" \
"
  - task-050.03
  - task-050.04
  - task-050.05"

echo ""
echo "✅ All authentication fix tasks created successfully!"
echo ""
echo "📊 TASK SUMMARY:"
echo "- task-050.03: Implement Missing Authentication Service Methods"
echo "- task-050.04: Fix Authentication Endpoint Implementation" 
echo "- task-050.05: Integration Testing and RBAC Validation"
echo "- task-050.06: Epic 051 Readiness Validation"
echo ""
echo "🎯 NEXT STEPS:"
echo "1. Assign tasks to fullstack-engineer"
echo "2. Begin with task-050.03 (implements missing methods)"
echo "3. Progress through tasks in order due to dependencies"
echo "4. Epic 051 can proceed once task-050.06 is complete"
echo ""
echo "🚨 CRITICAL: These tasks resolve authentication blockers"
echo "identified in Epic 050 testing that prevent Epic 051 progression."
echo ""
echo "Task creation complete! 🎉"