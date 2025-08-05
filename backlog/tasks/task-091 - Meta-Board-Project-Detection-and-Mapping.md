---
id: task-091
title: Meta-Board Project Detection and Mapping
status: In Progress
assignee: []
created_date: '2025-08-05'
updated_date: '2025-08-05'
labels: []
dependencies: []
---

## Description

Implement logic to detect and map which JIRA projects contribute to Board 259 meta-board aggregation

## Acceptance Criteria

- [ ] Create ProjectMappingService to manage project-to-meta-board relationships
- [ ] Implement project detection algorithm to identify Board 259 contributors
- [ ] Store project mapping configuration in database with validation
- [ ] Handle project addition/removal from meta-board scope
- [ ] Track project dependencies and relationships
- [ ] Provide API endpoints for project mapping management
- [ ] Support both automatic detection and manual configuration

## Implementation Plan

# Meta-Board Project Detection and Mapping Implementation Plan

## Architectural Analysis Summary
Based on ADR-001 (microservices), ADR-002 (database), and ADR-003 (API patterns), this task requires:

### 1. Create ProjectMappingService (extends existing service patterns)
- Location: /backend/app/services/project_mapping_service.py  
- Follows existing service architecture in /backend/app/services/
- Integrates with existing ProjectWorkstream and ProjectSprintAssociation models
- Implements Board 259 meta-board project detection algorithms

### 2. Extend existing models for project-to-meta-board relationships
- Leverage existing ProjectWorkstream model in /backend/app/models/project.py
- Extend ProjectSprintAssociation for meta-board mapping
- Add meta-board detection fields to ProjectWorkstream

### 3. Database integration using existing patterns
- Build on existing SQLAlchemy async patterns from /backend/app/core/database.py
- Store project mapping configuration with validation
- Use existing Base model patterns for audit trails

### 4. API endpoints extending current structure
- Extend /backend/app/api/v1/endpoints/meta_boards.py 
- Follow existing FastAPI router patterns from /backend/app/api/v1/router.py
- Use existing Pydantic schema patterns

### 5. Integration with JiraService
- Extend existing JiraService class in /backend/app/services/jira_service.py
- Add Board 259 project discovery methods
- Implement automatic project mapping detection

## Implementation Steps:
1. Extend ProjectWorkstream model with meta-board mapping fields
2. Create ProjectMappingService following existing service patterns
3. Implement Board 259 detection algorithm in ProjectMappingService
4. Add project mapping API endpoints to meta_boards.py
5. Extend JiraService with Board 259 project discovery
6. Add validation and dependency tracking
7. Implement automatic detection and manual configuration support
