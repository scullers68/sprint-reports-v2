---
id: task-051.02
title: Implement Authentication UI
status: In Progress
assignee: []
created_date: '2025-08-02'
updated_date: '2025-08-02'
labels:
  - mvp
  - frontend
  - authentication
dependencies:
  - task-051.01
---

## Description

Create login page with username/password authentication, implement JWT token management, and add protected route wrapper. This provides the essential authentication flow for users to access the application.

## Acceptance Criteria

- [ ] Login page with username/password form
- [ ] Form validation with error messages
- [ ] JWT token storage and management
- [ ] Protected route wrapper for authenticated pages
- [ ] Automatic redirect after login
- [ ] Logout functionality
- [ ] Authentication state persistence across browser refresh


## Implementation Plan

1. Enhance existing login form with React state management and form validation
2. Implement JWT token management using existing TokenManager class 
3. Create useAuth hook for authentication state management
4. Add route protection using Next.js middleware
5. Implement logout functionality in Header component
6. Add automatic redirects and authentication persistence
7. Test integration with Epic 050 backend authentication endpoints
## Implementation Approach

### Step 1: Login Page
**File**: `/frontend/src/app/login/page.tsx`
- Clean, responsive login form
- Username and password fields
- Form validation with error display
- Loading states during authentication

### Step 2: Authentication Context
**File**: `/frontend/src/lib/auth.tsx`
- React Context for authentication state
- Token storage in localStorage
- Automatic token refresh logic
- User information management

### Step 3: Protected Routes
**File**: `/frontend/src/components/auth/ProtectedRoute.tsx`
- HOC or component for route protection
- Redirect to login if not authenticated
- Loading state while checking authentication

### Step 4: API Integration
**Files**: `/frontend/src/lib/api.ts` (extend)
- Login API call implementation
- Token attachment to requests
- Logout API call
- Error handling for auth failures

## Technical Details

### Authentication Flow
```typescript
// Login process
1. User submits login form
2. Call POST /api/v1/auth/login
3. Store JWT token in localStorage
4. Update authentication context
5. Redirect to dashboard

// Protected route access
1. Check for valid token
2. If no token, redirect to login
3. If token expired, attempt refresh
4. If refresh fails, redirect to login
```

### Login Form Component
```typescript
// /frontend/src/app/login/page.tsx
interface LoginForm {
  username: string
  password: string
}

const LoginPage = () => {
  const { login, isLoading, error } = useAuth()
  
  const onSubmit = async (data: LoginForm) => {
    await login(data.username, data.password)
  }
  
  return (
    // Login form UI with validation
  )
}
```

### Authentication Context
```typescript
// /frontend/src/lib/auth.tsx
interface AuthContext {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

export const AuthProvider = ({ children }) => {
  // Authentication state management
}
```

## Files to Create/Modify

1. **`/frontend/src/app/login/page.tsx`**
   - Login page component
   - Form with validation
   - Error handling and loading states

2. **`/frontend/src/lib/auth.tsx`**
   - Authentication context provider
   - Token management
   - User state management

3. **`/frontend/src/components/auth/ProtectedRoute.tsx`**
   - Protected route wrapper
   - Authentication checks
   - Redirect logic

4. **`/frontend/src/lib/api.ts`** (extend)
   - Login/logout API functions
   - Token attachment to requests
   - Authentication error handling

5. **`/frontend/src/types/auth.ts`**
   - User interface definition
   - Authentication state types
   - API response types

## API Endpoints Used

### Authentication
- `POST /api/v1/auth/login`
  ```json
  {
    "username": "admin",
    "password": "password"
  }
  ```
  Response:
  ```json
  {
    "access_token": "jwt_token_here",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin"
    }
  }
  ```

- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me` - Get current user info

## Success Criteria

- User can login with admin credentials
- Invalid credentials show error message
- Successful login redirects to dashboard
- Protected routes require authentication
- Logout clears session and redirects to login
- Authentication state persists on page refresh

## Estimated Effort

**Time**: 6-8 hours
**Complexity**: Medium-High
**Dependencies**: Next.js application setup (task-051.01)

## Testing Checklist

- [ ] Login form accepts valid credentials
- [ ] Invalid credentials show error message
- [ ] Successful login redirects to dashboard
- [ ] Protected routes require authentication
- [ ] Logout functionality works correctly
- [ ] Authentication state persists on refresh
- [ ] API errors are handled gracefully
