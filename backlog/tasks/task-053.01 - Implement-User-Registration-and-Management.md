---
id: task-053.01
title: Implement User Registration and Management
status: To Do
assignee: []
created_date: '2025-08-02'
labels: ['mvp', 'users', 'registration']
dependencies: ['task-052.01']
---

## Description

Implement comprehensive user registration system with invitation functionality, profile management with avatars, and password reset capabilities. This provides essential user management features for team collaboration.

## Acceptance Criteria

- [ ] User registration form with email verification
- [ ] Admin invitation system for new users
- [ ] User profile editing with avatar upload
- [ ] Password reset via email
- [ ] User list management for admins
- [ ] Account activation/deactivation
- [ ] User activity tracking and last login display

## Implementation Approach

### Step 1: Registration System
**Files**: Frontend and Backend registration endpoints
- Public registration form (if enabled)
- Admin invitation system
- Email verification workflow
- Account activation process

### Step 2: Profile Management
**Files**: Profile pages and API endpoints
- User profile editing interface
- Avatar upload and management
- Password change functionality
- Account settings management

### Step 3: Admin User Management
**Files**: Admin dashboard components
- User list with search and filters
- User details and activity tracking
- Account management actions
- Bulk user operations

### Step 4: Password Reset
**Files**: Password reset flow
- Forgot password request
- Email with reset token
- Password reset form
- Confirmation and redirect

## Technical Details

### Registration Flow
```typescript
// Registration process
1. User fills registration form
2. System validates email uniqueness
3. Send verification email
4. User clicks verification link
5. Account activated and login enabled

// Admin invitation flow
1. Admin enters email addresses
2. System sends invitation emails
3. Users click invitation link
4. Users complete registration
5. Accounts activated automatically
```

### Backend API Endpoints
```python
# User management endpoints
POST /api/v1/auth/register          # Public registration
POST /api/v1/auth/invite            # Admin invitation
POST /api/v1/auth/verify-email      # Email verification
POST /api/v1/auth/forgot-password   # Password reset request
POST /api/v1/auth/reset-password    # Password reset completion

GET /api/v1/users/                  # List users (admin)
GET /api/v1/users/{id}              # Get user details
PUT /api/v1/users/{id}              # Update user profile
POST /api/v1/users/{id}/avatar      # Upload avatar
PUT /api/v1/users/{id}/status       # Activate/deactivate
```

### Frontend Components
```typescript
// Registration components
- RegistrationForm.tsx
- EmailVerification.tsx
- InvitationForm.tsx (admin)
- UserList.tsx (admin)

// Profile components
- UserProfile.tsx
- AvatarUpload.tsx
- PasswordChange.tsx
- AccountSettings.tsx
```

## Files to Create/Modify

### Backend Files
1. **`/app/api/v1/auth.py`** (extend)
   - Registration endpoint
   - Email verification
   - Password reset endpoints

2. **`/app/api/v1/users.py`** (extend)
   - User CRUD operations
   - Profile update endpoints
   - Avatar upload handling

3. **`/app/services/email.py`** (create)
   - Email sending service
   - Template management
   - Verification and reset emails

4. **`/app/services/user_service.py`** (extend)
   - User registration logic
   - Invitation management
   - Profile update logic

### Frontend Files
1. **`/frontend/src/app/register/page.tsx`**
   - Public registration form
   - Email verification handling

2. **`/frontend/src/app/profile/page.tsx`**
   - User profile display and editing
   - Avatar upload interface

3. **`/frontend/src/app/admin/users/page.tsx`**
   - Admin user management interface
   - User list with actions

4. **`/frontend/src/components/auth/`**
   - RegistrationForm.tsx
   - PasswordResetForm.tsx
   - EmailVerification.tsx

5. **`/frontend/src/components/users/`**
   - UserProfile.tsx
   - AvatarUpload.tsx
   - UserList.tsx
   - InvitationForm.tsx

## Email Templates

### Verification Email
```html
<!-- Welcome email with verification link -->
<h2>Welcome to Sprint Reports v2</h2>
<p>Please verify your email address by clicking the link below:</p>
<a href="{verification_url}">Verify Email Address</a>
```

### Invitation Email
```html
<!-- Admin invitation email -->
<h2>You've been invited to Sprint Reports v2</h2>
<p>{admin_name} has invited you to join the team.</p>
<a href="{invitation_url}">Accept Invitation</a>
```

### Password Reset Email
```html
<!-- Password reset email -->
<h2>Password Reset Request</h2>
<p>Click the link below to reset your password:</p>
<a href="{reset_url}">Reset Password</a>
```

## Database Schema Updates

### User Model Extensions
```sql
-- Add fields to users table
ALTER TABLE users ADD COLUMN avatar_url VARCHAR(255);
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN last_login TIMESTAMP;
ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN registration_date TIMESTAMP DEFAULT NOW();

-- Create email verification tokens table
CREATE TABLE email_verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create password reset tokens table
CREATE TABLE password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Success Criteria

- New users can register and verify their email
- Admins can invite users via email
- Users can upload and update their profile avatar
- Password reset works via email link
- Admin can view and manage all users
- User activity is tracked and displayed

## Estimated Effort

**Time**: 12-15 hours
**Complexity**: High
**Dependencies**: Sprint list and dashboard (task-052.01)

## Testing Checklist

- [ ] Registration form validates input correctly
- [ ] Email verification links work
- [ ] Admin invitation system sends emails
- [ ] Profile editing saves changes
- [ ] Avatar upload works with file validation
- [ ] Password reset flow completes successfully
- [ ] Admin user management functions work
- [ ] Email templates render correctly