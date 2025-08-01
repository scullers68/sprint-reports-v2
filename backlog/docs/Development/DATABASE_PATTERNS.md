# Database Patterns and Migration Standards

## Overview

This document establishes database design patterns, migration strategies, and best practices for Sprint Reports v2. All database implementations should follow these standards to ensure consistency, performance, and maintainability.

## Database Design Principles

### 1. Schema Design Standards

#### Table Naming Conventions
- Use plural nouns for table names: `users`, `sprints`, `sprint_analyses`
- Use snake_case for all table and column names
- Avoid reserved keywords and database-specific names
- Keep names descriptive but concise

#### Column Standards
```sql
-- Standard columns for all tables
id SERIAL PRIMARY KEY,
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

-- Foreign key naming
user_id INTEGER REFERENCES users(id),
sprint_id INTEGER REFERENCES sprints(id)

-- Boolean columns should be prefixed with is_, has_, or can_
is_active BOOLEAN NOT NULL DEFAULT TRUE,
has_capacity BOOLEAN NOT NULL DEFAULT FALSE,
can_edit BOOLEAN NOT NULL DEFAULT FALSE
```

#### Data Types Best Practices
```sql
-- Use appropriate precision
DECIMAL(10,2) for monetary values
DECIMAL(5,2) for percentages/ratios

-- Use TIMESTAMPTZ for all timestamps
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

-- Use TEXT for unlimited text, VARCHAR(n) for limited
description TEXT,
name VARCHAR(200) NOT NULL,
email VARCHAR(255) UNIQUE NOT NULL

-- Use JSONB for structured data (PostgreSQL)
settings JSONB,
metadata JSONB
```

### 2. Indexing Strategy

#### Primary Indexes
- Every table MUST have a primary key
- Use SERIAL/BIGSERIAL for auto-incrementing IDs
- Consider UUIDs for distributed systems or public APIs

#### Performance Indexes
```sql
-- Foreign key columns
CREATE INDEX idx_sprint_analyses_sprint_id ON sprint_analyses(sprint_id);
CREATE INDEX idx_sprint_queues_sprint_id ON sprint_queues(sprint_id);

-- Query performance indexes
CREATE INDEX idx_sprints_state ON sprints(state);
CREATE INDEX idx_sprints_name ON sprints(name);
CREATE INDEX idx_users_email ON users(email);

-- Composite indexes for complex queries
CREATE INDEX idx_sprints_state_dates ON sprints(state, start_date, end_date);
CREATE INDEX idx_analyses_sprint_type ON sprint_analyses(sprint_id, analysis_type);

-- Partial indexes for filtered queries
CREATE INDEX idx_active_users ON users(email) WHERE is_active = TRUE;
CREATE INDEX idx_active_sprints ON sprints(name) WHERE state = 'active';
```

#### JSON Indexing (PostgreSQL JSONB)
```sql
-- Index JSONB columns for performance
CREATE INDEX idx_sprint_analyses_breakdown ON sprint_analyses USING GIN (discipline_breakdown);
CREATE INDEX idx_user_settings ON users USING GIN (settings);

-- Functional indexes for JSON keys
CREATE INDEX idx_breakdown_team_count ON sprint_analyses 
  USING btree ((discipline_breakdown->>'team_count')::int);
```

### 3. Constraints and Data Integrity

#### Check Constraints
```sql
-- Validate enum-like values
ALTER TABLE sprints ADD CONSTRAINT chk_sprint_state 
  CHECK (state IN ('future', 'active', 'closed'));

-- Range validation
ALTER TABLE sprint_analyses ADD CONSTRAINT chk_positive_story_points 
  CHECK (total_story_points >= 0);

-- Date validation
ALTER TABLE sprints ADD CONSTRAINT chk_end_after_start 
  CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date);
```

#### Foreign Key Constraints
```sql
-- Cascade rules based on business logic
ALTER TABLE sprint_analyses 
  ADD CONSTRAINT fk_analyses_sprint 
  FOREIGN KEY (sprint_id) REFERENCES sprints(id) 
  ON DELETE CASCADE ON UPDATE CASCADE;

-- Prevent deletion with soft delete pattern
ALTER TABLE sprint_queues 
  ADD CONSTRAINT fk_queues_sprint 
  FOREIGN KEY (sprint_id) REFERENCES sprints(id) 
  ON DELETE RESTRICT ON UPDATE CASCADE;
```

## Migration Patterns

### 1. Migration File Structure

#### File Naming Convention
```
YYYY_MM_DD_HHMMSS_descriptive_name.py
2025_01_08_143000_add_user_authentication.py
2025_01_08_143001_create_sprint_analysis_table.py
```

#### Migration Template
```python
"""Add user authentication fields

Revision ID: abc123def456
Revises: previous_revision_id
Create Date: 2025-01-08 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'abc123def456'
down_revision = 'previous_revision_id' 
branch_labels = None
depends_on = None

def upgrade():
    """Apply the migration."""
    # Create table
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_token', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                 server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                 server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes
    op.create_index('idx_user_sessions_token', 'user_sessions', ['session_token'])
    op.create_index('idx_user_sessions_user_id', 'user_sessions', ['user_id'])
    
    # Add foreign key
    op.create_foreign_key(
        'fk_user_sessions_user_id', 'user_sessions', 'users',
        ['user_id'], ['id'], ondelete='CASCADE'
    )

def downgrade():
    """Rollback the migration."""
    op.drop_table('user_sessions')
```

### 2. Safe Migration Practices

#### Backwards Compatible Changes
```python
# ✅ Safe operations (can run on live database)
def upgrade():
    # Add nullable columns
    op.add_column('users', sa.Column('middle_name', sa.String(100), nullable=True))
    
    # Add indexes
    op.create_index('idx_users_middle_name', 'users', ['middle_name'])
    
    # Add check constraints (non-validating)
    op.execute("""
        ALTER TABLE users ADD CONSTRAINT chk_email_format 
        CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$') 
        NOT VALID
    """)
```

#### Breaking Changes (Require Maintenance Window)
```python
# ⚠️ Breaking operations (require careful planning)
def upgrade():
    # Rename columns (requires application deployment coordination)
    op.alter_column('users', 'username', new_column_name='user_name')
    
    # Drop columns (ensure no application code uses them)
    op.drop_column('users', 'legacy_field')
    
    # Change column types (requires data migration)
    op.alter_column('users', 'age', type_=sa.SmallInteger())
```

#### Data Migration Pattern
```python
def upgrade():
    # Create new column
    op.add_column('users', sa.Column('full_name', sa.String(255), nullable=True))
    
    # Migrate data
    connection = op.get_bind()
    connection.execute("""
        UPDATE users 
        SET full_name = CONCAT(first_name, ' ', last_name)
        WHERE first_name IS NOT NULL AND last_name IS NOT NULL
    """)
    
    # Make column not null after data migration
    op.alter_column('users', 'full_name', nullable=False)
    
    # Drop old columns after ensuring application compatibility
    # op.drop_column('users', 'first_name')
    # op.drop_column('users', 'last_name')
```

### 3. Migration Testing Strategy

#### Pre-Migration Validation
```python
def validate_migration():
    """Validate migration against production-like data."""
    connection = op.get_bind()
    
    # Check data integrity before migration
    result = connection.execute("""
        SELECT COUNT(*) FROM users WHERE email IS NULL OR email = ''
    """)
    
    if result.scalar() > 0:
        raise Exception("Found users with invalid email addresses")
    
    # Validate expected data state
    result = connection.execute("SELECT COUNT(*) FROM sprints")
    sprint_count = result.scalar()
    
    if sprint_count == 0:
        print("Warning: No sprints found in database")
```

## Database Seeding Patterns

### 1. Development Seed Data
```python
# backend/app/core/seed_data.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.sprint import Sprint
from app.core.security import get_password_hash

async def seed_development_data(db: AsyncSession):
    """Seed database with development data."""
    
    # Create admin user
    admin_user = User(
        email="admin@sprintreports.dev",
        username="admin",
        full_name="System Administrator",
        hashed_password=get_password_hash("admin123"),
        is_superuser=True
    )
    db.add(admin_user)
    
    # Create sample sprints
    sprints = [
        Sprint(
            jira_sprint_id=1001,
            name="Sprint 2025.01 - Foundation",
            state="active",
            goal="Establish technical foundation"
        ),
        Sprint(
            jira_sprint_id=1002,
            name="Sprint 2025.02 - Core Features",
            state="future",
            goal="Implement core sprint management features"
        )
    ]
    
    for sprint in sprints:
        db.add(sprint)
    
    await db.commit()
```

### 2. Production Data Migration
```sql
-- Production data migration scripts
-- backend/scripts/migrate_legacy_data.sql

-- Migrate users from legacy system
INSERT INTO users (email, username, full_name, jira_account_id, created_at)
SELECT 
    email,
    username,
    display_name,
    jira_id,
    COALESCE(created_date, NOW())
FROM legacy_users
WHERE email IS NOT NULL
ON CONFLICT (email) DO UPDATE SET
    jira_account_id = EXCLUDED.jira_account_id,
    updated_at = NOW();

-- Migrate sprint data
INSERT INTO sprints (jira_sprint_id, name, state, start_date, end_date, goal)
SELECT 
    sprint_id,
    sprint_name,
    CASE 
        WHEN status = 'ACTIVE' THEN 'active'
        WHEN status = 'CLOSED' THEN 'closed'
        ELSE 'future'
    END,
    start_date,
    end_date,
    objective
FROM legacy_sprints
ON CONFLICT (jira_sprint_id) DO UPDATE SET
    name = EXCLUDED.name,
    state = EXCLUDED.state,
    updated_at = NOW();
```

## Performance Optimization Patterns

### 1. Query Optimization
```python
# Use proper SQLAlchemy patterns for performance
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import select

async def get_sprint_with_analyses(db: AsyncSession, sprint_id: int):
    """Efficiently load sprint with related data."""
    stmt = (
        select(Sprint)
        .options(
            selectinload(Sprint.analyses),  # Separate query for collections
            joinedload(Sprint.created_by_user)  # JOIN for single relationships
        )
        .where(Sprint.id == sprint_id)
    )
    
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
```

### 2. Connection Pool Configuration
```python
# backend/app/core/database.py
from sqlalchemy.pool import QueuePool

# Optimized connection pool for production
engine = create_async_engine(
    str(settings.DATABASE_URL),
    poolclass=QueuePool,
    pool_size=20,           # Base connections
    max_overflow=30,        # Additional connections under load
    pool_pre_ping=True,     # Validate connections
    pool_recycle=3600,      # Recycle connections every hour
    echo=settings.LOG_LEVEL == "DEBUG"
)
```

### 3. Caching Strategies
```python
# Use Redis for frequently accessed data
import redis.asyncio as redis
from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL)

async def get_cached_sprint_analysis(sprint_id: int):
    """Get sprint analysis from cache or database."""
    cache_key = f"sprint_analysis:{sprint_id}"
    
    # Try cache first
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Fallback to database
    analysis = await get_sprint_analysis_from_db(sprint_id)
    
    # Cache for 5 minutes
    await redis_client.setex(
        cache_key, 
        300, 
        json.dumps(analysis, default=str)
    )
    
    return analysis
```

## Monitoring and Maintenance

### 1. Database Health Monitoring
```sql
-- Monitor table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_total_relation_size(schemaname||'.'||tablename) as bytes
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY bytes DESC;

-- Monitor slow queries
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Monitor index usage
SELECT 
    indexrelname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

### 2. Automated Maintenance
```python
# backend/app/tasks/database_maintenance.py
from celery import Celery
from app.core.database import get_db_session

@celery.task
async def analyze_tables():
    """Update table statistics for query planner."""
    db = await get_db_session()
    await db.execute("ANALYZE;")
    await db.close()

@celery.task  
async def vacuum_tables():
    """Reclaim storage and update statistics."""
    db = await get_db_session()
    await db.execute("VACUUM ANALYZE;")
    await db.close()
```

## Implementation Guidelines for Subtasks

### Task 001.04 - Database Schema Implementation
**Priority Actions**:
1. **Review Existing Models**: Analyze current models in `/backend/app/models/` for compliance
2. **Enhance Base Model**: Extend `/backend/app/models/base.py` with additional patterns
3. **Create Migration Templates**: Establish standard migration patterns in `/backend/alembic/`
4. **Implement Indexing Strategy**: Add performance indexes to existing tables
5. **Database Seeding**: Create development and production seed data utilities

**Files to Extend**:
- `/backend/app/models/base.py` - Add audit fields, soft delete patterns
- `/backend/app/models/*.py` - Enhance existing models with indexes and constraints
- `/backend/alembic/env.py` - Configure migration environment
- `/backend/app/core/database.py` - Add connection pooling and monitoring

### Performance Targets
- **Query Performance**: 95% of queries <100ms
- **Migration Speed**: <5 minutes for typical schema changes
- **Index Effectiveness**: >90% index hit ratio
- **Connection Efficiency**: <50ms connection acquisition

---

*These patterns ensure consistent, performant, and maintainable database operations across all Sprint Reports v2 services.*