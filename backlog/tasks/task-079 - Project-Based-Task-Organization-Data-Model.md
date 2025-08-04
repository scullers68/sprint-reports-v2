---
id: task-079
title: Project-Based Task Organization Data Model
status: Done
assignee:
  - fullstack-engineer
created_date: '2025-08-04'
updated_date: '2025-08-04'
labels: []
dependencies: []
---

## Description

Enhance data models to support project-based organization of tasks within sprints, enabling tracking and reporting on multiple project workstreams within a single sprint context.

## Implementation Plan

## IMPLEMENTATION PLAN - PROJECT-BASED TASK ORGANIZATION DATA MODEL

### COMPLIANCE CONFIRMED: I will prioritize reuse over creation

Based on architectural analysis, this implementation will extend existing models following ADR-002 database architecture patterns.

### Phase 1: Requirements Analysis (COMPLETE)
- Task-079 requirements: Project-based organization of tasks within sprints
- Architectural specifications: ProjectWorkstream, ProjectSprintMetrics models needed
- Existing models to extend: Sprint, SprintAnalysis following current patterns

### Phase 2: Analyze Existing System
- Review existing models in /backend/app/models/ for extension patterns  
- Identify current Sprint and SprintAnalysis relationship structures
- Map new project-based fields to existing JSON column patterns

### Phase 3: Database Model Implementation
- Extend existing models following Base model patterns in current codebase
- Create new models using existing relationship and validation patterns
- Implement indexes following current index naming conventions

### Phase 4: Migration Implementation
- Create migration scripts to populate project data from existing Sprint records
- Use existing migration patterns and preserve data integrity
- Follow current database setup patterns in /backend/app/core/database.py

### Phase 5: Testing & Validation
- Follow existing test patterns for model validation
- Test relationships and constraints using current testing approach
- Validate project-based queries performance with new indexes
## Implementation Notes

# ARCHITECTURAL SPECIFICATION COMPLETE - READY FOR FULLSTACK-ENGINEER IMPLEMENTATION

## ARCHITECTURE ANALYSIS SUMMARY

**COMPLIANCE CONFIRMED**: All specifications align with existing ADRs and PRD requirements:
- ✅ ADR-001: Extends existing microservices architecture using current service patterns
- ✅ ADR-002: Builds upon existing SQLAlchemy model foundation with PostgreSQL
- ✅ ADR-003: Maintains current API design patterns and router structure
- ✅ Follows existing Base model patterns and relationship conventions
- ✅ Preserves current index and constraint strategies

## NEW MODELS TO IMPLEMENT

### 1. ProjectWorkstream Model
**File**: 
**Purpose**: Represents project sources within meta-board sprints
**Key Features**:
- project_key, project_name, project_id fields
- JIRA integration (jira_board_id, jira_board_name)
- Workstream types: standard, epic, initiative
- Active status management and project categorization
- JSON metadata field for extensibility

### 2. ProjectSprintAssociation Model  
**File**:  (same file)
**Purpose**: Many-to-many relationship between Sprint and ProjectWorkstream
**Key Features**:
- sprint_id, project_workstream_id foreign keys
- Association types: primary, secondary, dependency
- Expected vs actual story points tracking
- Project priority within sprint context

### 3. ProjectSprintMetrics Model
**File**: 
**Purpose**: Project-level metrics tracking within sprints
**Key Features**:
- Comprehensive metrics (issues, story points, completion %)
- Progress tracking (velocity, burndown rate, scope changes)
- Team allocation and capacity utilization
- Quality metrics (blocked issues, bugs)
- JSON breakdowns for detailed analysis
- Historical comparison capability

## EXISTING MODELS TO EXTEND

### 1. Sprint Model Extensions
**File**: 
**Changes**:
- Add project_associations relationship
- Add project_workstreams property
- Add project_aggregation_metadata property
- Extend existing relationship patterns

### 2. SprintAnalysis Model Extensions  
**File**: 
**Changes**:
- Add project_key, project_name fields
- Enhance discipline_breakdown JSON structure for project data
- Add project_breakdown property and get_project_metrics method
- Add project-specific indexes

## DATABASE IMPLEMENTATION REQUIREMENTS

### Relationships


### Key Indexes (High Priority)
- 
- 
- 
- 

### Migration Strategy
1. Extract projects from existing Sprint.jira_project_key data
2. Create ProjectWorkstream records for discovered projects
3. Create ProjectSprintAssociation links
4. Backfill SprintAnalysis project fields
5. Generate baseline ProjectSprintMetrics

### Validation Constraints
- Unique project keys across active workstreams
- Logical metrics (completed ≤ total)
- Cross-model integrity (active associations required)
- Percentage range validations (0-100% completion)

## IMPLEMENTATION FILES TO CREATE/MODIFY

### New Files to Create:
1.  - ProjectWorkstream + ProjectSprintAssociation
2.  - ProjectSprintMetrics model
3. Migration script for project data population

### Files to Extend:
1.  - Add relationships and properties
2.  - Import new models

## RISK ASSESSMENT

**Low Risk**:
- Extends existing proven patterns
- Non-breaking changes to existing models
- Maintains data integrity with existing Sprint/SprintAnalysis data

**Medium Risk**:
- Migration complexity for existing data
- Index creation on large tables
- Cross-model validation performance

**Mitigation Strategies**:
- Use existing Base model patterns and validation approaches
- Implement migration in stages with rollback capability
- Create indexes with CONCURRENTLY option for production

## INTEGRATION POINTS

**Sprint Management Service**: Will access project data through new relationships
**Reporting Service**: Will use ProjectSprintMetrics for project-level analytics  
**JIRA Integration Service**: Will populate project metadata during sync operations
**Queue Generation Service**: Will consider project context in distribution algorithms

## TESTING REQUIREMENTS

1. **Model Tests**: Validate relationships, constraints, and business logic
2. **Migration Tests**: Verify data preservation and integrity during migration
3. **Performance Tests**: Confirm index effectiveness on project-based queries
4. **Integration Tests**: Ensure existing Sprint/SprintAnalysis functionality unaffected

## ARCHITECTURAL DECISIONS RATIONALE

1. **Many-to-Many Design**: Enables meta-board sprints with multiple projects
2. **Separate Metrics Model**: Allows temporal tracking and historical analysis
3. **JSON Breakdowns**: Provides flexibility for varying project structures
4. **Existing Pattern Reuse**: Minimizes learning curve and maintains consistency
5. **Migration Strategy**: Preserves existing data while enabling new functionality

This architectural specification provides a complete blueprint for implementation while maintaining full compliance with existing ADRs and architectural patterns.

## IMPLEMENTATION COMPLETE ✅

### DELIVERABLES COMPLETED

**New Models Created:**
1. **ProjectWorkstream Model** (`/backend/app/models/project.py`)
   - Represents project sources within meta-board sprints
   - Fields: project_key, project_name, jira_board_id, workstream_type, etc.
   - Enums: WorkstreamType (standard, epic, initiative)
   - Validation: project key/name uniqueness, required fields

2. **ProjectSprintAssociation Model** (`/backend/app/models/project.py`)
   - Many-to-many relationship between Sprint and ProjectWorkstream
   - Fields: association_type, project_priority, expected/actual story points
   - Enums: AssociationType (primary, secondary, dependency)
   - Constraints: unique sprint-project combinations, non-negative points

3. **ProjectSprintMetrics Model** (`/backend/app/models/project.py`)
   - Project-level metrics tracking within sprints
   - Comprehensive metrics: issues, story points, completion %, velocity, etc.
   - JSON breakdowns: issue_breakdown, team_breakdown, timeline_breakdown
   - Validation: logical constraints (completed ≤ total), percentage ranges

**Extended Existing Models:**
1. **Sprint Model** (`/backend/app/models/sprint.py`)
   - Added project_associations relationship
   - Added project_workstreams property
   - Added project_aggregation_metadata property for meta-board support

2. **SprintAnalysis Model** (`/backend/app/models/sprint.py`)
   - Added project_key and project_name fields
   - Enhanced with project_breakdown property
   - Added get_project_metrics() method
   - New indexes: idx_analysis_project_key, idx_analysis_sprint_project

**Database Implementation:**
1. **Migration Script** (`/backend/alembic/versions/012_add_project_organization_models.py`)
   - Complete Alembic migration with all tables, indexes, and constraints
   - PostgreSQL enums: WorkstreamType, AssociationType
   - Comprehensive indexes for performance optimization
   - Full rollback capability

2. **Data Migration Script** (`/backend/scripts/migrate_project_data.py`)
   - Automated script to populate project data from existing sprint records
   - 4-phase migration: workstreams → associations → analyses → metrics
   - Dry-run capability and comprehensive logging
   - Statistics tracking and error handling

3. **Model Integration** (`/backend/app/models/__init__.py`)
   - Updated imports to include all project-related models and enums
   - Maintains backward compatibility with existing models

### ARCHITECTURAL COMPLIANCE ✅

**ADR-002 Database Architecture Compliance:**
- Extends existing SQLAlchemy model foundation
- Uses existing Base model patterns (id, created_at, updated_at)
- Maintains current relationship and validation patterns
- Follows existing JSON column usage for flexible data
- Consistent index naming conventions

**Validation Constraints Added:**
- Project key uniqueness across active workstreams
- Logical metrics validation (completed ≤ total)
- Cross-model integrity (active associations required)
- Percentage range validations (0-100% completion)
- Non-negative numeric constraints throughout

### ACCEPTANCE CRITERIA STATUS ✅

- [x] Create ProjectWorkstream model to represent project sources within meta-board sprints
- [x] Extend Sprint model with project_workstreams relationship and aggregation metadata
- [x] Add project_key and project_name fields to existing sprint analysis models
- [x] Create ProjectSprintMetrics model to track project-level metrics within sprints
- [x] Implement database relationships between Sprint, ProjectWorkstream, and SprintAnalysis models
- [x] Add indexes for efficient project-based queries and reporting
- [x] Create migration scripts to populate project data from existing sprint records
- [x] Add validation constraints to ensure data integrity across project-sprint relationships

### FILES MODIFIED/CREATED

- `/backend/app/models/project.py` (NEW) - Complete project models
- `/backend/app/models/sprint.py` (EXTENDED) - Project relationships & properties
- `/backend/app/models/__init__.py` (UPDATED) - Model imports
- `/backend/alembic/versions/012_add_project_organization_models.py` (NEW) - Migration
- `/backend/scripts/migrate_project_data.py` (NEW) - Data migration script

### READY FOR TEST-ENGINEER VALIDATION

**Test Scenarios:**
1. Database migration execution (alembic upgrade head)
2. Model relationship queries and joins
3. Project data population from existing sprints
4. Validation constraint enforcement
5. Index performance on project-based queries
6. Meta-board sprint handling with multiple projects

**Migration Commands:**
```bash
# Database migration
alembic upgrade head

# Data migration (dry run first)
python scripts/migrate_project_data.py --dry-run
python scripts/migrate_project_data.py  # actual migration
```
## Phase 1: Requirements Analysis
1. Analyze task-079 acceptance criteria for project-based organization requirements
2. Review existing Sprint, SprintAnalysis, and related model structures
3. Identify extension points in current data model architecture
4. Map requirements to database schema changes and new model relationships

## Phase 2: Data Model Design  
1. Design ProjectWorkstream model for project source representation within meta-board sprints
2. Design project_workstreams relationship extension to Sprint model
3. Design project_key/project_name field additions to SprintAnalysis and related models
4. Design ProjectSprintMetrics model for project-level metrics tracking
5. Design database relationships between Sprint, ProjectWorkstream, and SprintAnalysis
6. Design efficient indexes for project-based queries and reporting

## Phase 3: Database Architecture Specification
1. Create detailed model specifications following existing Base model patterns
2. Specify foreign key relationships and cascade behaviors
3. Specify validation constraints and business rules
4. Create index specifications for optimal query performance
5. Design migration scripts to populate project data from existing records

## Phase 4: Implementation Specification
1. Document specific files to extend (following ADR-002 database patterns)
2. Create detailed migration strategy preserving existing data
3. Specify validation rules ensuring data integrity across relationships
4. Document integration points with existing Sprint and analysis workflows

## Phase 5: Handoff Documentation
1. Create comprehensive architectural specification for fullstack-engineer
2. Provide migration strategy and data preservation approach
3. Document validation and constraint requirements
4. Specify testing approach for new relationships and queries
