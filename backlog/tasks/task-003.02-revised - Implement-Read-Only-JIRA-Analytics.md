---
id: task-003.02-revised
title: Implement Read-Only JIRA Analytics Integration
status: To Do
assignee: [fullstack-engineer]
created_date: '2025-08-03'
updated_date: '2025-08-03'
labels: [analytics, read-only]
dependencies: [task-003.01]
parent_task_id: task-003
---

## Description

Implement simplified read-only JIRA integration focused on analytics and reporting. Replace the over-engineered bi-directional sync with a lightweight analytics-focused approach.

## Acceptance Criteria

- [ ] Sprint snapshot model for point-in-time analytics
- [ ] Read-only JIRA data fetching service
- [ ] Analytics engine for report generation
- [ ] Periodic data refresh mechanism
- [ ] Cache layer for fast report generation

## Vision Alignment

Based on screenshots review, Sprint Reports v2 is a **read-only analytics platform** that:
- Fetches sprint data from JIRA for analysis
- Generates baseline and comparison reports
- Creates capacity-based sprint planning queues
- Publishes reports to Confluence
- **Never modifies JIRA data**

## Implementation Plan

### Phase 1: Remove Over-Engineering

**Remove Unnecessary Components:**
- [ ] Delete bi-directional sync service (`app/services/sync_service.py`)
- [ ] Remove webhook processing (`app/api/v1/endpoints/webhooks.py`, `app/workers/webhook_processor.py`)
- [ ] Remove sync metadata models (`SyncMetadata`, `ConflictResolution`, `SyncHistory`)
- [ ] Remove complex sync endpoints
- [ ] Simplify JIRA service to read-only operations

### Phase 2: Implement Analytics Models

**New Models Needed:**
```python
class SprintSnapshot(Base):
    """Point-in-time sprint data for analytics."""
    __tablename__ = "sprint_snapshots"
    
    # Sprint identification
    jira_sprint_id = Column(Integer, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    state = Column(String(50), nullable=False)
    
    # Snapshot metadata
    snapshot_date = Column(DateTime(timezone=True), nullable=False)
    snapshot_type = Column(String(50), nullable=False)  # baseline, comparison, planning
    
    # Sprint timing
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    complete_date = Column(DateTime(timezone=True))
    
    # Analytics data
    issues_data = Column(JSON, nullable=False)  # Full issues with custom fields
    metrics = Column(JSON, nullable=False)      # Calculated metrics
    stakeholder_analysis = Column(JSON)         # Owner/reporter breakdown
    
    # Board and project info
    board_id = Column(Integer)
    project_key = Column(String(50), index=True)

class SprintAnalytics(Base):
    """Generated analytics and insights."""
    __tablename__ = "sprint_analytics"
    
    sprint_snapshot_id = Column(Integer, ForeignKey("sprint_snapshots.id"))
    analysis_type = Column(String(50), nullable=False)  # baseline, comparison, capacity
    
    # Status distribution
    status_distribution = Column(JSON)
    
    # Story points analysis
    total_story_points = Column(Float)
    avg_story_points = Column(Float)
    story_points_distribution = Column(JSON)
    
    # Stakeholder breakdown
    stakeholder_breakdown = Column(JSON)
    
    # Issue type analysis
    issue_type_distribution = Column(JSON)
    
    # Priority analysis  
    priority_distribution = Column(JSON)
    
    # Generated insights
    insights = Column(JSON)
    recommendations = Column(JSON)
```

### Phase 3: Simplified JIRA Service

**Read-Only Analytics Service:**
```python
class JiraAnalyticsService:
    """Read-only JIRA service for analytics needs."""
    
    async def fetch_sprint_snapshot(self, sprint_id: int, snapshot_type: str = "baseline") -> SprintSnapshot:
        """Fetch complete sprint data and create snapshot."""
        
    async def get_sprint_issues_with_analytics(self, sprint_id: int) -> List[Dict]:
        """Get all issues with custom fields for analysis."""
        
    async def analyze_sprint_data(self, snapshot: SprintSnapshot) -> SprintAnalytics:
        """Generate analytics from sprint snapshot."""
        
    async def generate_stakeholder_analysis(self, issues: List[Dict]) -> Dict:
        """Analyze issues by owner/reporter."""
        
    async def calculate_capacity_metrics(self, issues: List[Dict]) -> Dict:
        """Calculate capacity and velocity metrics."""
        
    async def refresh_active_sprints(self) -> List[SprintSnapshot]:
        """Periodic refresh of active sprint data."""
```

### Phase 4: Report Generation Engine

**Report Types from Screenshots:**
- [ ] Sprint Baseline Report (status, story points, stakeholder breakdown)
- [ ] Sprint Comparison Report (before/after analysis, change tracking)
- [ ] Sprint Planning Report (capacity-based queue generation)

### Phase 5: Confluence Integration

**Publishing Features:**
- [ ] Auto-generate Confluence pages from reports
- [ ] Template-based report formatting
- [ ] Export formats (CSV, PDF)

## Technical Implementation

### Database Schema Changes

1. **Remove Complex Sync Tables:**
   - Drop `sync_metadata`
   - Drop `conflict_resolutions` 
   - Drop `sync_history`
   - Drop `webhook_events`

2. **Add Analytics Tables:**
   - Add `sprint_snapshots`
   - Add `sprint_analytics`
   - Extend existing `sprints` table with analytics fields

### Service Layer Changes

1. **Simplify JiraService:**
   - Remove bi-directional sync methods
   - Remove webhook processing
   - Keep only read-only fetching methods
   - Add analytics-focused methods

2. **Create AnalyticsService:**
   - Sprint data analysis
   - Stakeholder breakdown
   - Capacity calculations
   - Insight generation

### API Changes

1. **Remove Complex Endpoints:**
   - Remove webhook endpoints
   - Remove sync conflict endpoints
   - Remove bi-directional sync endpoints

2. **Add Analytics Endpoints:**
   ```
   GET /api/v1/analytics/sprints/{id}/baseline
   GET /api/v1/analytics/sprints/{id}/comparison/{baseline_id}
   POST /api/v1/analytics/sprints/{id}/refresh
   GET /api/v1/analytics/sprints/{id}/stakeholders
   POST /api/v1/analytics/sprints/{id}/generate-queue
   ```

### Caching Strategy

1. **Redis Cache:**
   - Cache fetched JIRA data for 1 hour
   - Cache generated reports for 30 minutes
   - Cache analytics results for 15 minutes

2. **Background Refresh:**
   - Hourly refresh of active sprints
   - Daily refresh of recent closed sprints
   - On-demand refresh for specific sprints

## Expected Outcomes

### Performance Improvements
- **Faster Report Generation**: <5 seconds for 200+ issue sprint
- **Reduced JIRA API Calls**: Cache-first approach
- **Simpler Maintenance**: Less code complexity

### Functional Alignment
- **Screenshot-Accurate Reports**: Match the UI shown in screenshots
- **Analytics Focus**: Stakeholder analysis, status distribution, capacity planning
- **Export Capabilities**: Confluence, CSV, PDF formats

### Architecture Benefits
- **Simpler Codebase**: Remove 70% of sync-related complexity
- **Faster Development**: Focus on analytics features
- **Better Performance**: Lightweight data model
- **Clearer Purpose**: Align with actual product vision

## Migration Plan

1. **Preserve Essential Data:**
   - Export current sprint data
   - Backup existing sprint analyses

2. **Remove Over-Engineering:**
   - Create migration to drop sync tables
   - Remove sync services and endpoints
   - Clean up imports and dependencies

3. **Implement Analytics Core:**
   - Create new analytics models
   - Implement simplified JIRA service
   - Build report generation engine

4. **Validate Against Screenshots:**
   - Ensure baseline reports match screenshots
   - Verify comparison report functionality
   - Test stakeholder analysis accuracy

## Success Criteria

- [ ] Generate accurate baseline reports matching screenshots
- [ ] Create comparison reports with before/after analysis
- [ ] Implement capacity-based queue generation
- [ ] Publish reports to Confluence
- [ ] Achieve <5 second report generation for large sprints
- [ ] Reduce codebase complexity by 70%

This simplified approach aligns Sprint Reports v2 with its true purpose as a read-only analytics and reporting platform.