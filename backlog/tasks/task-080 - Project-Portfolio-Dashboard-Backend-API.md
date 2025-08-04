---
id: task-080
title: Project Portfolio Dashboard Backend API
status: In Progress
assignee:
  - >-
    [ ] Create /api/v1/meta-boards/{board_id}/project-portfolio endpoint for
    dashboard data, [ ] Implement service layer to aggregate project metrics
    across current sprint, [ ] Add endpoint to retrieve project completion
    forecasts based on velocity and remaining work, [ ] Create API for project
    priority rankings and resource allocation within the sprint, [ ] Implement
    caching strategy for expensive project aggregation queries, [ ] Add
    filtering and sorting capabilities for project portfolio view, [ ] Ensure
    API responses include project health indicators and risk metrics, [ ] Add
    comprehensive error handling and validation for meta-board specific requests
created_date: '2025-08-04'
updated_date: '2025-08-04'
labels: []
dependencies: []
---

## Description

Develop backend API endpoints to support project portfolio dashboard, providing overview of all projects being worked on in current sprint with project-level metrics and progress tracking.

## Implementation Plan

## IMPLEMENTATION PLAN - PROJECT PORTFOLIO DASHBOARD BACKEND API

### 1. Essential New Files (Minimal Creation)
-  - Portfolio API endpoints
-  - Response schemas

### 2. Extend Existing Files (Prioritized Reuse)
-  - Add meta-boards router
-  - Portfolio aggregation methods  
-  - Portfolio caching strategy
-  - Project metrics methods

### 3. Implementation Sequence
1. Create response schemas following existing Pydantic patterns
2. Create API endpoints following existing FastAPI router patterns
3. Extend services with portfolio aggregation logic
4. Add caching strategy with Redis-based portfolio cache
5. Update router configuration and test endpoints

### 4. Compliance Validation
- Extends existing ADR patterns (FastAPI, SQLAlchemy, Redis)
- Builds on task-078/079 meta-board and project models
- Minimal new file creation with maximum code reuse
- Follows established error handling and validation patterns
## Implementation Notes

## ARCHITECTURAL SPECIFICATION COMPLETE - READY FOR FULLSTACK-ENGINEER IMPLEMENTATION

### COMPLIANCE VALIDATION ✅
- ADR-001 (Microservices): Extensions follow existing FastAPI service patterns
- ADR-002 (Database): Builds upon existing SQLAlchemy models and caching infrastructure  
- ADR-003 (API Design): Maintains existing router structure and endpoint patterns
- CLAUDE.md Compliance: Prioritizes code reuse, extends existing files vs. creating new ones

### ARCHITECTURAL DECISIONS

**1. API Endpoint Structure**
- Primary endpoint: GET /api/v1/meta-boards/{board_id}/project-portfolio
- Forecasting: GET /api/v1/meta-boards/{board_id}/project-forecasts  
- Resource allocation: GET /api/v1/meta-boards/{board_id}/resource-allocation
- Follows existing router patterns in /backend/app/api/v1/router.py

**2. Service Layer Integration**
- Extends SprintService with portfolio aggregation methods
- Enhances SprintCacheService with Redis-based portfolio caching
- Reuses existing JIRA service for project-level data retrieval
- Cache TTL: 5 minutes for real-time, 1 hour for historical metrics

**3. Data Model Reuse**
- Leverages task-078 MetaBoardConfiguration for meta-board detection
- Uses task-079 ProjectWorkstream relationships for project aggregation
- Extends existing CachedSprint model for project metrics calculations
- No new database tables required - builds on existing architecture

**4. Implementation Strategy**
- Minimal new file creation: Only meta_boards.py endpoints and schemas
- Maximum code reuse: Extends 4 existing service/model files
- Caching strategy: Redis-based with intelligent cache invalidation
- Error handling: Comprehensive validation for meta-board specific requests

### FILES TO MODIFY (NO NEW CORE FILES)

**Create (Essential Only):**
- /backend/app/api/v1/endpoints/meta_boards.py (API endpoints)
- /backend/app/schemas/meta_boards.py (Response schemas)

**Extend (Prioritized Reuse):**
- /backend/app/api/v1/router.py (Add meta-boards router)
- /backend/app/services/sprint_service.py (Portfolio aggregation methods)
- /backend/app/services/sprint_cache_service.py (Portfolio caching)
- /backend/app/models/cached_sprint.py (Project metrics methods)

### TECHNICAL SPECIFICATIONS

**Caching Strategy:**
- Cache Key Pattern: meta_board:{board_id}:portfolio:{filter_hash}
- Redis-based with 5min TTL for real-time, 1hr for historical
- Intelligent invalidation on sprint/project updates

**Health Indicators & Risk Metrics:**
- Project completion percentage and velocity tracking
- Blocked issue detection and risk scoring
- Resource allocation vs capacity analysis
- Sprint scope change impact assessment

**Filtering & Sorting:**
- Project priority rankings within sprint context
- Resource allocation efficiency metrics
- Completion forecast accuracy indicators
- Multi-project sprint health aggregation

### INTEGRATION DEPENDENCIES
- Task-078: Meta-board detection and configuration
- Task-079: Project-based data organization models
- Existing cache infrastructure: CachedSprint and SprintCacheService
- JIRA service integration for real-time project health data

### RISK ASSESSMENT: LOW RISK ✅
- Extends proven architectural patterns from existing ADRs
- Builds on established caching infrastructure
- Minimal new code creation, maximum pattern reuse
- Graceful degradation if meta-board features unavailable

**Ready for fullstack-engineer implementation with complete architectural blueprint.**

Architecture complete. Ready for fullstack-engineer implementation. All acceptance criteria addressed through architectural specification that prioritizes code reuse and follows existing ADR patterns. Implementation blueprint provided with specific file extensions and minimal new file creation.
