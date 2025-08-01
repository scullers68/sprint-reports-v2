---
id: task-044
title: Extend Sprint Model with JIRA Metadata
status: To Do
assignee: []
created_date: '2025-08-01'
labels: []
dependencies: []
---

## Description

Add the missing JIRA sync fields to the Sprint model as specified in the architecture. These fields are required for proper JIRA integration tracking and sync status management.

## Acceptance Criteria

- [ ] Add jira_last_updated field as DateTime with timezone to Sprint model
- [ ] Add sync_status field with default pending value
- [ ] Add sync_conflicts field as JSON type for conflict tracking
- [ ] Add jira_board_name field as String(200)
- [ ] Add jira_project_key field as String(50) with index
- [ ] Add jira_version field as String(20) for compatibility tracking
- [ ] Create database migration to add new fields to sprints table
- [ ] Ensure all new fields have appropriate default values for existing records
- [ ] Update Sprint model relationships and constraints
