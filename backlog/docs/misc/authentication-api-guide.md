# Sprint Reports v2 - Authentication API Guide

## Overview

This guide provides comprehensive documentation for integrating with the Sprint Reports v2 authentication system. All authentication APIs are now functional and ready for Epic 051 frontend development.

## Base URL

- **Local Development**: `http://localhost:3001`
- **API Prefix**: `/api/v1`

## Authentication Flow

### 1. User Registration

**Endpoint**: `POST /api/v1/auth/register`

**Request Body**:
```json
{
  "email": "user@example.com",
  "username": "username",
  "password": "password123",
  "full_name": "User Full Name"
}
```

**Success Response** (201):
```json
{
  "user": {
    "email": "user@example.com",
    "username": "username",
    "full_name": "User Full Name",
    "department": null,
    "role": null,
    "is_active": true,
    "id": 4,
    "is_superuser": false,
    "last_login": null,
    "failed_login_attempts": 0,
    "jira_account_id": null,
    "jira_display_name": null,
    "created_at": "2025-08-02T07:40:38.099476Z",
    "updated_at": "2025-08-02T07:40:38.099476Z"
  },
  "message": "User registered successfully"
}
```

### 2. User Login

**Endpoint**: `POST /api/v1/auth/login`

**Request Body**:
```json
{
  "email": "admin@sprint-reports.com",
  "password": "admin123"
}
```

**Success Response** (200):
```json
{
  "user": {
    "email": "admin@sprint-reports.com",
    "username": "admin",
    "full_name": "System Administrator",
    "department": "IT",
    "role": "Administrator",
    "is_active": true,
    "id": 1,
    "is_superuser": true,
    "last_login": "2025-08-02T06:50:10.967110Z",
    "failed_login_attempts": 0,
    "jira_account_id": null,
    "jira_display_name": null,
    "created_at": "2025-08-02T04:28:20.765121Z",
    "updated_at": "2025-08-02T06:50:10.669289Z"
  },
  "token": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "message": "Login successful"
}
```

### 3. Token Refresh

**Endpoint**: `POST /api/v1/auth/refresh`

**Request Body**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response** (200):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 4. User Logout

**Endpoint**: `POST /api/v1/auth/logout`
**Authentication**: Required (Bearer token)

**Headers**:
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

**Success Response** (200):
```json
{
  "message": "Logout successful"
}
```

## Protected Endpoints

All protected endpoints require the `Authorization` header with a valid Bearer token:

```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### User Management

#### Get Current User Profile
**Endpoint**: `GET /api/v1/users/me`
**Authentication**: Required

**Success Response** (200):
```json
{
  "email": "admin@sprint-reports.com",
  "username": "admin",
  "full_name": "System Administrator",
  "department": "IT",
  "role": "Administrator",
  "is_active": true,
  "id": 1,
  "is_superuser": true,
  "last_login": "2025-08-02T07:39:36.879595Z",
  "failed_login_attempts": 0,
  "jira_account_id": null,
  "jira_display_name": null,
  "created_at": "2025-08-02T04:28:20.765121Z",
  "updated_at": "2025-08-02T07:39:36.610571Z"
}
```

#### List All Users (Admin Only)
**Endpoint**: `GET /api/v1/users`
**Authentication**: Required (Superuser only)
**Query Parameters**:
- `skip`: Number of records to skip (default: 0)
- `limit`: Number of records to return (default: 100, max: 1000)
- `active_only`: Only return active users (default: true)

**Success Response** (200):
```json
[
  {
    "email": "user@example.com",
    "username": "user",
    "full_name": "User Name",
    "department": null,
    "role": null,
    "is_active": true,
    "id": 2,
    "is_superuser": false,
    "last_login": null,
    "failed_login_attempts": 0,
    "jira_account_id": null,
    "jira_display_name": null,
    "created_at": "2025-08-02T05:47:01.918737Z",
    "updated_at": "2025-08-02T05:47:01.918737Z"
  }
]
```

#### Get User by ID (Admin Only)
**Endpoint**: `GET /api/v1/users/{user_id}`
**Authentication**: Required (Superuser only)

**Success Response** (200): Same format as user profile

## JWT Token Details

### Token Structure
- **Type**: Bearer token
- **Format**: JWT (JSON Web Token)
- **Expiration**: 30 minutes (1800 seconds)
- **Refresh Token Expiration**: 7 days

### Token Payload
```json
{
  "sub": "user@example.com",
  "user_id": 1,
  "exp": 1754119210,
  "type": "access"
}
```

## Error Responses

### Authentication Errors

#### 401 Unauthorized
```json
{
  "error": "Authentication required",
  "message": "You must be authenticated to access this resource",
  "type": "authentication_error"
}
```

#### 403 Forbidden
```json
{
  "error": "Insufficient permissions",
  "message": "You don't have permission to access this resource",
  "type": "authorization_error"
}
```

### Validation Errors

#### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

#### 400 Bad Request
```json
{
  "error": "Validation error",
  "message": "Invalid input data",
  "type": "validation_error"
}
```

## Frontend Integration Examples

### React Authentication Hook

```typescript
import { useState, useEffect } from 'react';

interface User {
  id: number;
  email: string;
  username: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
}

interface AuthToken {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for stored token on mount
    const storedToken = localStorage.getItem('access_token');
    if (storedToken) {
      setToken(storedToken);
      fetchCurrentUser(storedToken);
    } else {
      setLoading(false);
    }
  }, []);

  const fetchCurrentUser = async (accessToken: string) => {
    try {
      const response = await fetch('http://localhost:3001/api/v1/users/me', {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        // Token might be expired
        logout();
      }
    } catch (error) {
      console.error('Failed to fetch user:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    try {
      const response = await fetch('http://localhost:3001/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (response.ok) {
        const data = await response.json();
        const { user: userData, token: tokenData } = data;
        
        setUser(userData);
        setToken(tokenData.access_token);
        
        // Store tokens
        localStorage.setItem('access_token', tokenData.access_token);
        localStorage.setItem('refresh_token', tokenData.refresh_token);
        
        return { success: true };
      } else {
        const error = await response.json();
        return { success: false, error: error.message };
      }
    } catch (error) {
      return { success: false, error: 'Network error' };
    }
  };

  const logout = async () => {
    try {
      if (token) {
        await fetch('http://localhost:3001/api/v1/auth/logout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      setToken(null);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  };

  const register = async (userData: {
    email: string;
    username: string;
    password: string;
    full_name?: string;
  }) => {
    try {
      const response = await fetch('http://localhost:3001/api/v1/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      });

      if (response.ok) {
        const data = await response.json();
        return { success: true, user: data.user };
      } else {
        const error = await response.json();
        return { success: false, error: error.message };
      }
    } catch (error) {
      return { success: false, error: 'Network error' };
    }
  };

  return {
    user,
    token,
    loading,
    login,
    logout,
    register,
    isAuthenticated: !!user,
  };
};
```

### API Client with Token Management

```typescript
class ApiClient {
  private baseUrl = 'http://localhost:3001/api/v1';
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    this.accessToken = localStorage.getItem('access_token');
    this.refreshToken = localStorage.getItem('refresh_token');
  }

  setTokens(accessToken: string, refreshToken: string) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  }

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  private async refreshAccessToken(): Promise<boolean> {
    if (!this.refreshToken) return false;

    try {
      const response = await fetch(`${this.baseUrl}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      });

      if (response.ok) {
        const data = await response.json();
        this.setTokens(data.access_token, data.refresh_token);
        return true;
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
    }

    this.clearTokens();
    return false;
  }

  async request(endpoint: string, options: RequestInit = {}): Promise<Response> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    } as HeadersInit;

    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    let response = await fetch(url, {
      ...options,
      headers,
    });

    // If token expired, try to refresh and retry
    if (response.status === 401 && this.refreshToken) {
      const refreshed = await this.refreshAccessToken();
      if (refreshed) {
        headers['Authorization'] = `Bearer ${this.accessToken}`;
        response = await fetch(url, {
          ...options,
          headers,
        });
      }
    }

    return response;
  }

  // Convenience methods
  async get(endpoint: string) {
    return this.request(endpoint, { method: 'GET' });
  }

  async post(endpoint: string, data: any) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async put(endpoint: string, data: any) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async delete(endpoint: string) {
    return this.request(endpoint, { method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();
```

## Testing Guide

### Using curl

#### 1. Login and Save Token
```bash
# Login and extract token
TOKEN=$(curl -s -X POST "http://localhost:3001/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@sprint-reports.com", "password": "admin123"}' | \
  jq -r '.token.access_token')

echo "Token: $TOKEN"
```

#### 2. Test Protected Endpoint
```bash
# Get current user profile
curl -X GET "http://localhost:3001/api/v1/users/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json"
```

#### 3. List Users (Admin Only)
```bash
# List all users
curl -X GET "http://localhost:3001/api/v1/users?limit=10&active_only=true" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json"
```

#### 4. Register New User
```bash
# Register new user
curl -X POST "http://localhost:3001/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "username": "newuser",
    "password": "password123",
    "full_name": "New User"
  }'
```

## Security Best Practices

### Token Storage
- **Web Applications**: Use secure HTTP-only cookies or encrypted localStorage
- **Mobile Apps**: Use secure keychain/keystore
- **Never store tokens in plain text or unsecured storage**

### Token Handling
- Always check token expiration before making requests
- Implement automatic token refresh logic
- Handle 401 responses by refreshing tokens or redirecting to login
- Clear all tokens on logout

### Request Security
- Always use HTTPS in production
- Validate SSL certificates
- Implement proper CORS policies
- Use CSP headers to prevent XSS attacks

### Error Handling
- Don't expose sensitive error information to end users
- Log authentication failures for monitoring
- Implement rate limiting for login attempts
- Handle network errors gracefully

## Admin Users

For testing and development, use these credentials:

- **Email**: `admin@sprint-reports.com`
- **Password**: `admin123`
- **Permissions**: Superuser access to all endpoints

## Epic 051 Readiness Status

✅ **READY FOR DEVELOPMENT**

All authentication systems are functional and tested:
- ✅ User registration working
- ✅ User login working  
- ✅ JWT token generation working
- ✅ Protected endpoints accessible with valid tokens
- ✅ Token refresh working
- ✅ User management endpoints working
- ✅ Authorization middleware functional
- ✅ Error handling consistent
- ✅ API documentation complete

**No authentication blockers remain for Epic 051 frontend development.**