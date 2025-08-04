---
id: task-078
title: Meta-Board Detection and Configuration
status: In Progress
assignee:
  - >-
    [ ] Extend Sprint model to include meta_board_type field and project_source
    tracking, [ ] Add meta-board configuration table to store aggregation rules
    and project mappings, [ ] Create API endpoint to configure a board as
    meta-board with project source definitions, [ ] Implement detection logic in
    JIRA service to identify when Board 259 contains tasks from multiple
    projects, [ ] Add validation to ensure meta-board configuration is
    consistent with actual board content, [ ] Update existing sprint
    synchronization to capture project source information for meta-board tasks,
    [ ] Create database migration to support new meta-board fields without
    breaking existing functionality
created_date: '2025-08-04'
updated_date: '2025-08-04'
labels: []
dependencies: []
---

## Description

Create system capability to detect and configure Board 259 as a meta-board that aggregates tasks from multiple projects, enabling specialized reporting for single-team multi-project sprints.

## Implementation Plan

## Architectural Analysis Plan for Meta-Board Detection and Configuration

### Phase 1: Requirements Analysis ✓
- Analyzed task-078 requirements for Board 259 meta-board capability
- Reviewed existing architecture documentation (ADR-001, ADR-002, ADR-003)
- Confirmed compliance with microservices architecture and database patterns
- Identified extension points in Sprint model and JIRA service

### Phase 2: Technical Specification
1. **Sprint Model Extensions**
   - Add meta_board_type enum field (single_project, multi_project, meta_board)
   - Add project_source JSON field for tracking task origins
   - Maintain backward compatibility with existing Sprint relationships

2. **Meta-Board Configuration Model**
   - Create MetaBoardConfiguration table with aggregation rules
   - Define project mappings and filtering criteria
   - Include validation rules for board-project consistency

3. **API Endpoint Design**
   - Extend existing /api/v1/sprints endpoints following ADR-003 patterns
   - Create /api/v1/meta-boards configuration endpoints
   - Integrate with existing JIRA service architecture

4. **JIRA Service Enhancement**
   - Extend JiraService.get_sprint_issues() for multi-project detection
   - Add project source tracking in sprint synchronization
   - Implement Board 259 specific detection logic

5. **Database Migration Strategy**
   - Create Alembic migration extending existing sprint schema
   - Ensure zero-downtime deployment compatibility
   - Preserve existing Sprint model relationships

### Phase 3: Implementation Handoff Notes
- All extensions follow existing architectural patterns from ADR documents
- Prioritizes code reuse over new file creation per CLAUDE.md rules
- Maintains microservices boundaries and database architecture compliance
- Ready for fullstack-engineer implementation with detailed specifications
