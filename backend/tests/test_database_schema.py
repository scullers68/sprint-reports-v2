"""
Test database schema constraints and validation.

Validates that all database constraints, indexes, and validation rules work correctly.
"""

import pytest
from sqlalchemy.exc import IntegrityError, CheckViolation
from sqlalchemy import text

from app.core.database import get_db_session, check_database_health
from app.models import User, Sprint, DisciplineTeamCapacity, SprintAnalysis


class TestDatabaseConstraints:
    """Test database-level constraints and validation."""

    async def test_database_health_check(self):
        """Test database connectivity health check."""
        health_status = await check_database_health()
        assert health_status is True

    async def test_user_email_constraint(self):
        """Test user email format validation constraint."""
        async with get_db_session() as session:
            # Test invalid email format
            user = User(
                email="invalid-email",
                username="testuser",
                hashed_password="hashed123",
                is_active=True,
                is_superuser=False
            )
            session.add(user)
            
            with pytest.raises((IntegrityError, CheckViolation)):
                await session.commit()

    async def test_user_username_not_empty(self):
        """Test username cannot be empty constraint."""
        async with get_db_session() as session:
            user = User(
                email="test@example.com",
                username="   ",  # Only whitespace
                hashed_password="hashed123",
                is_active=True,
                is_superuser=False
            )
            session.add(user)
            
            with pytest.raises((IntegrityError, CheckViolation)):
                await session.commit()

    async def test_sprint_state_constraint(self):
        """Test sprint state validation constraint."""
        async with get_db_session() as session:
            sprint = Sprint(
                jira_sprint_id=12345,
                name="Test Sprint",
                state="invalid_state"  # Invalid state
            )
            session.add(sprint)
            
            with pytest.raises((IntegrityError, CheckViolation)):
                await session.commit()

    async def test_sprint_date_logic_constraint(self):
        """Test sprint date logic constraints."""
        from datetime import datetime, timezone
        
        async with get_db_session() as session:
            sprint = Sprint(
                jira_sprint_id=12346,
                name="Test Sprint",
                state="active",
                start_date=datetime(2025, 8, 10, tzinfo=timezone.utc),
                end_date=datetime(2025, 8, 5, tzinfo=timezone.utc)  # End before start
            )
            session.add(sprint)
            
            with pytest.raises((IntegrityError, CheckViolation)):
                await session.commit()

    async def test_sprint_sync_status_constraint(self):
        """Test sprint sync status validation constraint."""
        async with get_db_session() as session:
            sprint = Sprint(
                jira_sprint_id=12350,
                name="Test Sprint",
                state="active",
                sync_status="invalid_sync_status"  # Invalid sync status
            )
            session.add(sprint)
            
            with pytest.raises((IntegrityError, CheckViolation)):
                await session.commit()

    async def test_capacity_non_negative_constraint(self):
        """Test capacity non-negative value constraints."""
        async with get_db_session() as session:
            # First create a valid sprint
            sprint = Sprint(
                jira_sprint_id=12347,
                name="Test Sprint",
                state="active"
            )
            session.add(sprint)
            await session.flush()  # Get the sprint ID
            
            capacity = DisciplineTeamCapacity(
                sprint_id=sprint.id,
                discipline_team="Test Team",
                capacity_points=-10.0,  # Negative capacity
                capacity_type="story_points"
            )
            session.add(capacity)
            
            with pytest.raises((IntegrityError, CheckViolation)):
                await session.commit()

    async def test_capacity_utilization_range_constraint(self):
        """Test capacity utilization percentage range constraint."""
        async with get_db_session() as session:
            # First create a valid sprint
            sprint = Sprint(
                jira_sprint_id=12348,
                name="Test Sprint",
                state="active"
            )
            session.add(sprint)
            await session.flush()
            
            capacity = DisciplineTeamCapacity(
                sprint_id=sprint.id,
                discipline_team="Test Team",
                capacity_points=100.0,
                utilization_percentage=250.0,  # Over 200% limit
                capacity_type="story_points"
            )
            session.add(capacity)
            
            with pytest.raises((IntegrityError, CheckViolation)):
                await session.commit()

    async def test_analysis_non_negative_constraint(self):
        """Test sprint analysis non-negative value constraints."""
        async with get_db_session() as session:
            # First create a valid sprint
            sprint = Sprint(
                jira_sprint_id=12349,
                name="Test Sprint",
                state="active"
            )
            session.add(sprint)
            await session.flush()
            
            analysis = SprintAnalysis(
                sprint_id=sprint.id,
                analysis_type="discipline_team",
                total_issues=-5,  # Negative issues count
                total_story_points=100.0
            )
            session.add(analysis)
            
            with pytest.raises((IntegrityError, CheckViolation)):
                await session.commit()


class TestDatabaseIndexes:
    """Test database indexes are created and functional."""

    async def test_user_indexes_exist(self):
        """Test that user indexes are created."""
        async with get_db_session() as session:
            # Check if indexes exist
            result = await session.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'users' 
                AND indexname IN ('idx_user_jira_lookup', 'idx_user_department_role')
            """))
            indexes = [row[0] for row in result.fetchall()]
            
            assert 'idx_user_jira_lookup' in indexes
            assert 'idx_user_department_role' in indexes

    async def test_sprint_indexes_exist(self):
        """Test that sprint indexes are created."""
        async with get_db_session() as session:
            result = await session.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'sprints' 
                AND indexname IN ('idx_sprint_jira_state', 'idx_sprint_dates', 'idx_sprint_board', 'idx_sprint_sync_status', 'idx_sprint_project_key')
            """))
            indexes = [row[0] for row in result.fetchall()]
            
            assert 'idx_sprint_jira_state' in indexes
            assert 'idx_sprint_dates' in indexes
            assert 'idx_sprint_board' in indexes
            assert 'idx_sprint_sync_status' in indexes
            assert 'idx_sprint_project_key' in indexes


class TestModelValidation:
    """Test SQLAlchemy model-level validation."""

    def test_user_email_validation(self):
        """Test user email validation at model level."""
        user = User(
            email="invalid-email",
            username="testuser",
            hashed_password="hashed123"
        )
        
        with pytest.raises(ValueError):
            user.validate_email('email', 'invalid-email')

    def test_user_username_validation(self):
        """Test username validation at model level."""
        user = User()
        
        with pytest.raises(ValueError):
            user.validate_username('username', 'ab')  # Too short

    def test_sprint_state_validation(self):
        """Test sprint state validation at model level."""
        sprint = Sprint()
        
        with pytest.raises(ValueError):
            sprint.validate_state('state', 'invalid_state')

    def test_sprint_sync_status_validation(self):
        """Test sprint sync status validation at model level."""
        sprint = Sprint()
        
        with pytest.raises(ValueError):
            sprint.validate_sync_status('sync_status', 'invalid_sync_status')

    def test_capacity_validation(self):
        """Test capacity validation at model level."""
        capacity = DisciplineTeamCapacity()
        
        with pytest.raises(ValueError):
            capacity.validate_non_negative_capacity('capacity_points', -10.0)
        
        with pytest.raises(ValueError):
            capacity.validate_utilization('utilization_percentage', 250.0)