---
id: task-078
title: Meta-Board Detection and Configuration
status: To Do
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
labels: []
dependencies: []
---

## Description

Create system capability to detect and configure Board 259 as a meta-board that aggregates tasks from multiple projects, enabling specialized reporting for single-team multi-project sprints.
