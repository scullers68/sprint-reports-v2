---
id: task-052.01
title: Implement Sprint List and Dashboard
status: In Progress
assignee: []
created_date: '2025-08-02'
updated_date: '2025-08-03'
labels:
  - mvp
  - frontend
  - sprints
dependencies:
  - task-051.02
parent_task_id: task-052
---

## Description

Create sprint list page showing real data from backend API and implement dashboard with sprint overview and navigation. This delivers the core "Basic Data Display" requirement from the health check action plan.

## Acceptance Criteria

- [ ] Sprint list page displaying real backend data
- [ ] Dashboard with sprint overview and quick stats
- [ ] Navigation menu for accessing different sections
- [ ] Pagination for large sprint lists
- [ ] Search and filter functionality
- [ ] Loading states and error handling
- [ ] Responsive design for mobile and desktop


## Implementation Plan

1. Analyze existing Frontend codebase and Sprint API endpoints
2. Implement Sprint List page with real backend API integration
3. Create Dashboard component with sprint overview and navigation
4. Add pagination, search, and filter functionality to Sprint List
5. Implement responsive design and loading/error states
6. Test local deployment and integration with backend
7. Validate all acceptance criteria are met
## Implementation Approach

### Step 1: Dashboard Page
**File**: `/frontend/src/app/dashboard/page.tsx`
- Overview cards with sprint statistics
- Recent sprints table
- Quick action buttons
- Navigation to other sections

### Step 2: Sprint List Page
**File**: `/frontend/src/app/sprints/page.tsx`
- Table/card view of all sprints
- Search and filter controls
- Pagination controls
- Sort by various columns

### Step 3: Data Fetching
**Files**: `/frontend/src/lib/api.ts` (extend)
- Sprint list API integration
- Dashboard statistics API
- Search and filter API calls
- Caching for performance

### Step 4: UI Components
**Files**: `/frontend/src/components/sprints/`
- SprintCard component
- SprintTable component
- SearchFilter component
- Pagination component

## Technical Details

### Sprint List API Integration
```typescript
// API endpoints to implement
const sprintService = {
  getAll: (params?: {
    page?: number
    limit?: number
    search?: string
    status?: string
  }) => apiClient.get<SprintListResponse>('/api/v1/sprints', { params }),
  
  getStats: () => apiClient.get<DashboardStats>('/api/v1/sprints/stats')
}
```

### Sprint List Component
```typescript
interface Sprint {
  id: number
  name: string
  status: 'planning' | 'active' | 'completed'
  start_date: string
  end_date: string
  team_id: number
  progress: number
}

const SprintList = () => {
  const [sprints, setSprints] = useState<Sprint[]>([])
  const [loading, setLoading] = useState(true)
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 10,
    total: 0
  })
  
  // Implementation for data fetching and display
}
```

### Dashboard Stats
```typescript
interface DashboardStats {
  totalSprints: number
  activeSprints: number
  completedSprints: number
  totalIssues: number
  completedIssues: number
  averageVelocity: number
}
```

## UI Components to Create

### 1. Dashboard Overview Cards
```typescript
// /frontend/src/components/dashboard/StatsCard.tsx
interface StatsCardProps {
  title: string
  value: number | string
  change?: number
  icon: ReactNode
}
```

### 2. Sprint Table
```typescript
// /frontend/src/components/sprints/SprintTable.tsx
interface SprintTableProps {
  sprints: Sprint[]
  loading: boolean
  onSort: (field: string) => void
  onFilter: (filters: FilterOptions) => void
}
```

### 3. Search and Filter
```typescript
// /frontend/src/components/sprints/SprintFilters.tsx
interface FilterOptions {
  search: string
  status: string[]
  dateRange: [Date, Date] | null
}
```

## Files to Create/Modify

1. **`/frontend/src/app/dashboard/page.tsx`**
   - Main dashboard page
   - Stats cards and overview
   - Recent activity section

2. **`/frontend/src/app/sprints/page.tsx`**
   - Sprint list page
   - Search and filter interface
   - Pagination controls

3. **`/frontend/src/components/dashboard/`**
   - StatsCard.tsx
   - RecentSprints.tsx
   - QuickActions.tsx

4. **`/frontend/src/components/sprints/`**
   - SprintTable.tsx
   - SprintCard.tsx
   - SprintFilters.tsx
   - SprintPagination.tsx

5. **`/frontend/src/lib/api.ts`** (extend)
   - Sprint API functions
   - Dashboard stats API
   - Search and pagination logic

6. **`/frontend/src/types/sprint.ts`**
   - Sprint interface definitions
   - API response types
   - Filter and pagination types

## API Endpoints Required

### Sprint Management
- `GET /api/v1/sprints` - List sprints with pagination/filtering
- `GET /api/v1/sprints/stats` - Dashboard statistics
- `GET /api/v1/sprints/{id}` - Sprint details

### Sample API Response
```json
{
  "sprints": [
    {
      "id": 1,
      "name": "Sprint 2025-01",
      "status": "active",
      "start_date": "2025-01-01",
      "end_date": "2025-01-14",
      "team_id": 1,
      "progress": 65,
      "issue_count": 25,
      "completed_issues": 16
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 45,
    "pages": 5
  }
}
```

## Success Criteria

- Dashboard loads with real sprint statistics
- Sprint list displays data from backend API
- Search finds sprints by name
- Filter works for sprint status
- Pagination allows browsing all sprints
- Loading states show during API calls
- Error messages display for API failures

## Estimated Effort

**Time**: 8-10 hours
**Complexity**: Medium-High
**Dependencies**: Authentication UI (task-051.02)

## Testing Checklist

- [ ] Dashboard loads with correct statistics
- [ ] Sprint list shows real backend data
- [ ] Search functionality works correctly
- [ ] Filters apply and update results
- [ ] Pagination navigates through results
- [ ] Loading states appear during API calls
- [ ] Error handling works for API failures
- [ ] Mobile responsive design works
