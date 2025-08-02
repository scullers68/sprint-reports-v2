---
id: task-051.01
title: Create Next.js Application
status: To Do
assignee: []
created_date: '2025-08-02'
labels: ['mvp', 'frontend', 'setup']
dependencies: ['task-050.02']
---

## Description

Create a new Next.js application with TypeScript, configure basic routing and layouts, and set up API client for backend integration. This addresses the "No Functional Frontend" critical issue from the health check.

## Acceptance Criteria

- [ ] Next.js 14 application created with App Router
- [ ] TypeScript configuration working
- [ ] Tailwind CSS installed and configured
- [ ] Basic layout components created
- [ ] API client configured for backend integration
- [ ] Environment configuration for API endpoints
- [ ] Development server running on port 3000

## Implementation Approach

### Step 1: Next.js Project Setup
**Directory**: `/frontend/` (create new)
```bash
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
cd frontend
```

### Step 2: Project Structure
```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Home page
│   │   ├── login/
│   │   │   └── page.tsx        # Login page
│   │   └── dashboard/
│   │       └── page.tsx        # Dashboard page
│   ├── components/
│   │   ├── ui/                 # Reusable UI components
│   │   ├── layout/             # Layout components
│   │   └── forms/              # Form components
│   ├── lib/
│   │   ├── api.ts              # API client
│   │   ├── auth.ts             # Authentication utilities
│   │   └── utils.ts            # General utilities
│   └── types/
│       └── api.ts              # API type definitions
```

### Step 3: API Client Setup
**File**: `/frontend/src/lib/api.ts`
```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

class ApiClient {
  private baseURL: string
  private token: string | null = null

  constructor(baseURL: string) {
    this.baseURL = baseURL
  }

  setToken(token: string) {
    this.token = token
  }

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    // Implementation for API requests with auth headers
  }
}

export const apiClient = new ApiClient(API_BASE_URL)
```

### Step 4: Basic Layout Components
**File**: `/frontend/src/app/layout.tsx`
- Root layout with metadata
- Global styles and providers
- Error boundary wrapper

**File**: `/frontend/src/components/layout/Header.tsx`
- Navigation header
- User menu
- Responsive design

## Technical Details

### Dependencies to Install
```json
{
  "dependencies": {
    "next": "14.x",
    "react": "18.x",
    "react-dom": "18.x",
    "typescript": "5.x",
    "@types/node": "20.x",
    "@types/react": "18.x",
    "@types/react-dom": "18.x",
    "tailwindcss": "3.x",
    "react-hook-form": "7.x",
    "zod": "3.x"
  }
}
```

### Environment Configuration
**File**: `/frontend/.env.local`
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=Sprint Reports v2
```

### Tailwind Configuration
**File**: `/frontend/tailwind.config.js`
- Configure content paths
- Add custom theme colors
- Include component utilities

## Files to Create

1. **`/frontend/`** (entire directory)
   - New Next.js application
   - TypeScript configuration
   - Package.json with dependencies

2. **`/frontend/src/lib/api.ts`**
   - API client with authentication
   - Request/response utilities
   - Error handling

3. **`/frontend/src/types/api.ts`**
   - Type definitions for API responses
   - User and sprint interfaces
   - Authentication types

4. **`/frontend/src/components/layout/`**
   - Header component
   - Sidebar component
   - Layout wrappers

## Success Criteria

- `npm run dev` starts development server
- Application loads at `http://localhost:3000`
- Basic routing works between pages
- API client can make requests to backend
- TypeScript compilation works without errors
- Tailwind CSS styles are applied

## Estimated Effort

**Time**: 4-6 hours
**Complexity**: Medium
**Dependencies**: Backend API working (task-050.02)

## Testing Checklist

- [ ] Next.js application starts successfully
- [ ] TypeScript compilation works
- [ ] Tailwind CSS styles load correctly
- [ ] Basic routing navigation works
- [ ] API client can connect to backend
- [ ] Environment variables are loaded
- [ ] Development workflow is smooth