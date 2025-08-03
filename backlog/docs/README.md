# Documentation Organization

This directory contains all project documentation organized into logical subdirectories.

## Directory Structure

### `/architecture/`
- System architecture documents
- Architecture Decision Records (ADRs)
- Design patterns and technical specifications

### `/Development/`
- Development guides and onboarding materials
- Database patterns and deployment architecture
- Legacy development documentation

### `/epics/`
- Epic-level documentation and summaries
- High-level feature descriptions

### `/guides/`
- How-to guides and reference materials
- Task numbering guide
- Process documentation

### `/health-checks/`
- System health reports
- Architecture compliance assessments

### `/misc/`
- Miscellaneous documentation
- Temporary or uncategorized documents

### `/requirements/`
- Product Requirements Documents (PRDs)
- Business requirements and specifications

### `/testing/`
- Test files, scripts, and validation documents
- Epic validation reports
- Test HTML pages and JavaScript files

### `/validation/`
- Epic validation reports
- Feature verification documents
- Acceptance criteria validation

## File Organization Rules

The `/tidy` slash command automatically organizes misplaced `.md` files based on these patterns:

- `epic-*-validation*.md` → `/validation/`
- `epic-*.md` → `/epics/`
- `test-*` or `test_*` → `/testing/`
- `report-*.md` → `/reports/`
- `*health*check*.md` → `/health-checks/`
- `*architecture*.md`, `*design*.md`, `adr-*.md` → `/architecture/`
- `*prd*.md`, `*requirements*.md` → `/requirements/`
- Other files → `/misc/`

## Usage

To organize misplaced documents, run:
```bash
/tidy
```

This will scan the project root and `/backlog` root for misplaced `.md` files and move them to appropriate subdirectories within `/backlog/docs/`.