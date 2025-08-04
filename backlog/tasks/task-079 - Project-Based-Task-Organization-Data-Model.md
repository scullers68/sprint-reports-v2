---
id: task-079
title: Project-Based Task Organization Data Model
status: In Progress
assignee:
  - >-
    [ ] Create ProjectWorkstream model to represent project sources within
    meta-board sprints, [ ] Extend Sprint model with project_workstreams
    relationship and aggregation metadata, [ ] Add project_key and project_name
    fields to existing sprint analysis models, [ ] Create ProjectSprintMetrics
    model to track project-level metrics within sprints, [ ] Implement database
    relationships between Sprint, ProjectWorkstream, and SprintAnalysis models,
    [ ] Add indexes for efficient project-based queries and reporting, [ ]
    Create migration scripts to populate project data from existing sprint
    records, [ ] Add validation constraints to ensure data integrity across
    project-sprint relationships
created_date: '2025-08-04'
updated_date: '2025-08-04'
labels: []
dependencies: []
---

## Description

Enhance data models to support project-based organization of tasks within sprints, enabling tracking and reporting on multiple project workstreams within a single sprint context.

## Implementation Plan

ARCHITECTURAL ANALYSIS AND DESIGN PLAN


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
