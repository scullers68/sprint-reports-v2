---
id: task-051.01
parent_task_id: task-051
title: Create Next.js Application
status: Done
assignee: [fullstack-implementer]
created_date: '2025-08-02'
labels: ['mvp', 'frontend', 'setup']
dependencies: ['task-050.02']
---

## Description

Create a new Next.js application with TypeScript, configure basic routing and layouts, and set up API client for backend integration. This addresses the "No Functional Frontend" critical issue from the health check.

## Acceptance Criteria

- [x] Next.js 14 application created with App Router
- [x] TypeScript configuration working
- [x] Tailwind CSS installed and configured
- [x] Basic layout components created
- [x] API client configured for backend integration
- [x] Environment configuration for API endpoints
- [x] Development server running on port 3000

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

- [x] Next.js application starts successfully
- [x] TypeScript compilation works
- [x] Tailwind CSS styles load correctly
- [x] Basic routing navigation works
- [x] API client can connect to backend
- [x] Environment variables are loaded
- [x] Development workflow is smooth

## Implementation Notes

**Completion Date**: 2025-08-02
**Implementer**: fullstack-implementer

### Summary of Changes
- **Next.js 14 Application**: Successfully created with App Router structure in `/frontend/` directory
- **TypeScript Configuration**: Strict TypeScript setup with path aliases and proper type checking
- **Tailwind CSS**: Complete design system with custom themes, components, and utilities
- **API Client**: Comprehensive API client with authentication, error handling, and Epic 050 backend integration
- **SSO Integration**: Migrated existing SSO components to work with Next.js App Router
- **Environment Setup**: Development and production environment configurations

### Files Created/Modified
1. **Configuration Files**:
   - `next.config.js` - Next.js configuration with API rewrites
   - `tsconfig.json` - TypeScript strict configuration
   - `tailwind.config.js` - Design system configuration
   - `.env.local` & `.env.example` - Environment variables

2. **Core Application**:
   - `src/app/layout.tsx` - Root layout with metadata
   - `src/app/page.tsx` - Homepage with feature overview
   - `src/app/globals.css` - Global styles and utility classes

3. **Pages**:
   - `src/app/login/page.tsx` - Login page with SSO integration
   - `src/app/dashboard/page.tsx` - Dashboard with metrics overview
   - `src/app/auth/sso/callback/page.tsx` - SSO callback handler

4. **Components**:
   - `src/components/layout/Header.tsx` - Responsive navigation header
   - `src/components/auth/SSOCallback.tsx` - Updated for Next.js router
   - `src/components/auth/SSOProviderSelect.tsx` - Updated for API client

5. **API Integration**:
   - `src/lib/api.ts` - Complete API client with authentication and error handling
   - `src/types/api.ts` - TypeScript definitions for API responses

### Technical Validation
- ✅ Build succeeds without errors: `npm run build`
- ✅ TypeScript compilation passes: `npm run type-check`
- ✅ ESLint validation passes: `npm run lint`
- ✅ Development server starts on port 3000: `npm run dev`
- ✅ Application responds correctly: HTTP 200 status

### Integration Points
- **Backend API**: Configured to communicate with Epic 050 backend at `http://localhost:8000`
- **Authentication**: SSO components ready for Epic 050 authentication endpoints
- **Environment**: Development environment configured for local backend integration

### Next Steps
This implementation provides the foundation for task-051.02 (Authentication UI) and establishes the frontend architecture for the complete Epic 051 user workflows.