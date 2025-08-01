# Database Operations Guide

## Overview

This document provides operational procedures for managing the Sprint Reports v2 PostgreSQL database, including backup, recovery, monitoring, and maintenance tasks.

## Database Configuration

### Connection Settings
- **Engine**: PostgreSQL with asyncpg driver
- **Connection Pool**: QueuePool with 20 connections max
- **Pool Recycle**: 3600 seconds (1 hour)
- **Health Checks**: Pre-ping enabled

### Performance Settings
- JIT compilation disabled for faster connection times
- Connection pooling optimized for async operations
- Automatic pool connection validation

## Backup Procedures

### 1. Automated Daily Backups

```bash
# Create backup script
#!/bin/bash
BACKUP_DIR="/volume1/docker/projects/sprint-reports-v2/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="sprint_reports_v2"

# Create backup with compression
pg_dump -h localhost -U postgres -d $DB_NAME \
  --verbose --format=custom --compress=9 \
  --file="$BACKUP_DIR/sprint_reports_backup_$DATE.dump"

# Keep only last 30 days of backups
find $BACKUP_DIR -name "sprint_reports_backup_*.dump" -mtime +30 -delete
```

### 2. Pre-Deployment Backups

Before any schema changes or major deployments:

```bash
# Schema-only backup
pg_dump -h localhost -U postgres -d sprint_reports_v2 \
  --schema-only --verbose \
  --file="backups/schema_backup_$(date +%Y%m%d_%H%M%S).sql"

# Full backup with data
pg_dump -h localhost -U postgres -d sprint_reports_v2 \
  --verbose --format=custom --compress=9 \
  --file="backups/full_backup_$(date +%Y%m%d_%H%M%S).dump"
```

## Recovery Procedures

### 1. Full Database Recovery

```bash
# Stop the application
docker-compose down

# Drop and recreate database (WARNING: This will delete all data)
psql -h localhost -U postgres -c "DROP DATABASE sprint_reports_v2;"
psql -h localhost -U postgres -c "CREATE DATABASE sprint_reports_v2;"

# Restore from backup
pg_restore -h localhost -U postgres -d sprint_reports_v2 \
  --verbose --clean --if-exists \
  backups/sprint_reports_backup_YYYYMMDD_HHMMSS.dump

# Restart application
docker-compose up -d
```

### 2. Point-in-Time Recovery

For point-in-time recovery, ensure WAL archiving is enabled:

```sql
-- Enable WAL archiving (requires PostgreSQL configuration)
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET archive_mode = on;
ALTER SYSTEM SET archive_command = 'cp %p /volume1/docker/projects/sprint-reports-v2/wal_archive/%f';
```

### 3. Selective Table Recovery

```bash
# Restore specific tables only
pg_restore -h localhost -U postgres -d sprint_reports_v2 \
  --verbose --table=users --table=sprints \
  backups/sprint_reports_backup_YYYYMMDD_HHMMSS.dump
```

## Migration Management

### 1. Database Migrations with Alembic

```bash
# Check current migration status
alembic current

# Upgrade to latest migration
alembic upgrade head

# Downgrade one revision
alembic downgrade -1

# Generate new migration
alembic revision --autogenerate -m "Description of changes"
```

### 2. Migration Safety Checklist

Before running migrations in production:

- [ ] Full database backup completed
- [ ] Migration tested in development environment
- [ ] Migration tested with production data subset
- [ ] Rollback plan prepared
- [ ] Application maintenance window scheduled
- [ ] Team notification sent

## Monitoring and Health Checks

### 1. Database Health Monitoring

```python
# Use the built-in health check function
from app.core.database import check_database_health, get_pool_status

# Check basic connectivity
health_status = await check_database_health()

# Monitor connection pool
pool_stats = await get_pool_status()
print(f"Pool size: {pool_stats['size']}")
print(f"Active connections: {pool_stats['checked_out']}")
```

### 2. Performance Monitoring Queries

```sql
-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_tup_read DESC;

-- Check slow queries
SELECT 
    query,
    mean_time,
    calls,
    total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

## Maintenance Tasks

### 1. Regular Maintenance

```sql
-- Update table statistics (run weekly)
ANALYZE;

-- Vacuum tables (run as needed)
VACUUM ANALYZE;

-- Reindex (run monthly or as needed)
REINDEX DATABASE sprint_reports_v2;
```

### 2. Cleanup Procedures

```sql
-- Clean up old report snapshots (older than 6 months)
DELETE FROM report_snapshots 
WHERE created_at < NOW() - INTERVAL '6 months'
  AND is_baseline = false;

-- Archive old sprint data (older than 2 years)
-- Consider moving to archive tables instead of deletion
```

## Security Considerations

### 1. Access Control

- Database users have minimum required permissions
- Application uses dedicated database user with limited privileges
- Backup files are encrypted and stored securely
- Connection strings use environment variables

### 2. Audit Logging

```sql
-- Enable audit logging for sensitive operations
CREATE EXTENSION IF NOT EXISTS pgaudit;
ALTER SYSTEM SET pgaudit.log = 'ddl,write';
ALTER SYSTEM SET pgaudit.log_catalog = off;
```

## Troubleshooting

### 1. Connection Issues

```python
# Check connection pool status
from app.core.database import get_pool_status
pool_stats = await get_pool_status()

# If pool is exhausted, consider:
# - Increasing pool_size in settings
# - Checking for connection leaks in application code
# - Analyzing slow queries that hold connections
```

### 2. Performance Issues

```sql
-- Check for locks
SELECT 
    pg_stat_activity.pid,
    pg_stat_activity.query,
    pg_locks.mode,
    pg_locks.granted
FROM pg_stat_activity
JOIN pg_locks ON pg_stat_activity.pid = pg_locks.pid
WHERE NOT pg_locks.granted;

-- Check table bloat
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_stat_user_tables.n_dead_tup
FROM pg_tables
JOIN pg_stat_user_tables ON pg_tables.tablename = pg_stat_user_tables.relname
WHERE schemaname = 'public'
ORDER BY pg_stat_user_tables.n_dead_tup DESC;
```

## Emergency Contacts

- **Database Administrator**: [Contact Information]
- **DevOps Team**: [Contact Information]
- **Application Team Lead**: [Contact Information]

## Recovery Time Objectives

- **RTO (Recovery Time Objective)**: 4 hours
- **RPO (Recovery Point Objective)**: 24 hours
- **Critical System Recovery**: 2 hours
- **Full System Recovery**: 8 hours