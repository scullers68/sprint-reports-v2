# ADR-002: Database Architecture and Data Management

## Status
Accepted

## Context
The application needs to migrate from SQLite to PostgreSQL while maintaining the existing SQLAlchemy model structure defined in `/backend/app/models/`. The current models show good separation of concerns with proper relationships.

## Decision
We will implement a PostgreSQL-based architecture that extends the existing SQLAlchemy model foundation.

### Database Strategy:
1. **Single Database with Schema Separation**: Extend existing models in `/backend/app/models/`
2. **Async SQLAlchemy**: Leverage existing async database setup in `/backend/app/core/database.py`
3. **Migration Strategy**: Build upon existing model relationships (Sprint, SprintAnalysis, User, etc.)

### Data Architecture:
- **Core Tables**: Extend existing models (`sprint.py`, `user.py`, `report.py`, `queue.py`, `capacity.py`)
- **JSONB Fields**: Utilize existing JSON columns for flexible data (discipline_breakdown, issue_details)
- **Indexing Strategy**: Build upon existing indexes defined in models
- **Audit Trail**: Extend existing Base model timestamp patterns

### Service Data Patterns:
- **Sprint Service**: Use existing Sprint and SprintAnalysis models
- **JIRA Service**: Extend existing issue data patterns in JSON fields  
- **Reporting Service**: Build on existing Report model relationships
- **Queue Service**: Leverage existing queue models and capacity relationships

## Consequences

### Positive:
- Maintains existing model relationships and patterns
- Leverages current async SQLAlchemy setup
- Preserves existing data structure and business logic
- JSONB provides flexibility for integration data

### Negative:
- Single database may become bottleneck at scale
- Complex migration from existing SQLite data
- Cross-service transaction management complexity

## Implementation Notes
- Extend models in `/backend/app/models/` rather than creating new schemas
- Build upon existing database configuration in `/backend/app/core/database.py`
- Maintain current relationship patterns between Sprint, User, Report, Queue models
- Use existing Base model patterns for common fields (id, created_at, updated_at)

## References
- PRD Section: Technical Requirements - Database Requirements
- Existing models: `/backend/app/models/` directory
- Current database setup: `/backend/app/core/database.py`
- Configuration: `/backend/app/core/config.py` database settings