"""
Tests for audit service functionality.

Comprehensive tests for security audit logging, tamper detection,
compliance reporting, and retention policies.
"""

import pytest
import hashlib
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.audit_service import AuditService
from app.models.security import SecurityEvent, AuditLog, SecurityEventTypes, SecurityEventCategories
from app.models.user import User
from app.core.config import settings


class TestAuditService:
    """Test suite for AuditService."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def audit_service(self, mock_db):
        """Audit service instance with mocked database."""
        return AuditService(mock_db)
    
    @pytest.fixture
    def sample_user(self):
        """Sample user for testing."""
        return User(
            id=1,
            email="test@example.com",
            username="testuser",
            is_active=True
        )
    
    @pytest.fixture
    def sample_security_event(self):
        """Sample security event for testing."""
        return SecurityEvent(
            id=1,
            user_id=1,
            user_email="test@example.com",
            user_ip="192.168.1.1",
            event_type=SecurityEventTypes.LOGIN_SUCCESS,
            event_category=SecurityEventCategories.AUTHENTICATION,
            severity="INFO",
            success=True,
            description="User login successful",
            correlation_id="test-correlation-id",
            metadata={"test": "data"}
        )
    
    def test_create_security_event_success(self, audit_service, mock_db):
        """Test successful security event creation."""
        # Arrange
        mock_db.add = Mock()
        mock_db.flush = Mock()
        mock_db.commit = Mock()
        
        # Mock the get_last_event_checksum method
        with patch.object(audit_service, '_get_last_event_checksum', return_value="previous_checksum"):
            # Act
            event = audit_service.create_security_event(
                event_type=SecurityEventTypes.LOGIN_SUCCESS,
                event_category=SecurityEventCategories.AUTHENTICATION,
                description="Test login event",
                user_id=1,
                user_email="test@example.com",
                success=True
            )
        
        # Assert
        assert event is not None
        assert event.event_type == SecurityEventTypes.LOGIN_SUCCESS
        assert event.event_category == SecurityEventCategories.AUTHENTICATION
        assert event.user_id == 1
        assert event.success is True
        assert event.checksum is not None
        assert event.previous_checksum == "previous_checksum"
        
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_create_security_event_disabled(self, audit_service, mock_db):
        """Test security event creation when audit logging is disabled."""
        # Arrange
        audit_service.enabled = False
        
        # Act
        event = audit_service.create_security_event(
            event_type=SecurityEventTypes.LOGIN_SUCCESS,
            event_category=SecurityEventCategories.AUTHENTICATION,
            description="Test login event"
        )
        
        # Assert
        assert event is None
        mock_db.add.assert_not_called()
    
    def test_create_security_event_with_retention(self, audit_service, mock_db):
        """Test security event creation with retention policy."""
        # Arrange
        mock_db.add = Mock()
        mock_db.flush = Mock()
        mock_db.commit = Mock()
        
        # Act
        event = audit_service.create_security_event(
            event_type=SecurityEventTypes.DATA_ACCESS,
            event_category=SecurityEventCategories.DATA_ACCESS,
            description="Data access event",
            retention_days=90,
            compliance_tags=["GDPR", "SOC2"]
        )
        
        # Assert
        assert event is not None
        assert event.compliance_tags == ["GDPR", "SOC2"]
        assert event.retention_date is not None
    
    def test_verify_event_integrity_valid(self, audit_service, mock_db, sample_security_event):
        """Test event integrity verification for valid event."""
        # Arrange
        sample_security_event.checksum = sample_security_event.calculate_checksum()
        mock_db.query.return_value.filter.return_value.first.return_value = sample_security_event
        
        # Act
        result = audit_service.verify_event_integrity(1)
        
        # Assert
        assert result["valid"] is True
        assert result["event_id"] == 1
        assert result["checksum_valid"] is True
        assert result["chain_valid"] is True
    
    def test_verify_event_integrity_invalid_checksum(self, audit_service, mock_db, sample_security_event):
        """Test event integrity verification for tampered event."""
        # Arrange
        sample_security_event.checksum = "invalid_checksum"
        mock_db.query.return_value.filter.return_value.first.return_value = sample_security_event
        
        # Act
        result = audit_service.verify_event_integrity(1)
        
        # Assert
        assert result["valid"] is False
        assert result["checksum_valid"] is False
    
    def test_verify_event_integrity_not_found(self, audit_service, mock_db):
        """Test event integrity verification for non-existent event."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = audit_service.verify_event_integrity(999)
        
        # Assert
        assert result["valid"] is False
        assert "not found" in result["error"].lower()
    
    def test_verify_audit_chain_integrity_valid(self, audit_service, mock_db):
        """Test audit chain integrity verification for valid chain."""
        # Arrange
        events = []
        for i in range(3):
            event = SecurityEvent(
                id=i+1,
                event_type=SecurityEventTypes.LOGIN_SUCCESS,
                event_category=SecurityEventCategories.AUTHENTICATION,
                description=f"Event {i+1}",
                success=True
            )
            event.checksum = event.calculate_checksum()
            if i > 0:
                event.previous_checksum = events[i-1].checksum
            events.append(event)
        
        mock_db.query.return_value.order_by.return_value.all.return_value = events
        
        # Mock individual integrity verification
        with patch.object(audit_service, 'verify_event_integrity') as mock_verify:
            mock_verify.return_value = {"valid": True}
            
            # Act
            result = audit_service.verify_audit_chain_integrity()
        
        # Assert
        assert result["valid"] is True
        assert result["total_events"] == 3
        assert result["verified_events"] == 3
        assert len(result["invalid_events"]) == 0
        assert len(result["broken_chain_events"]) == 0
    
    def test_verify_audit_chain_integrity_broken_chain(self, audit_service, mock_db):
        """Test audit chain integrity verification with broken chain."""
        # Arrange
        event1 = SecurityEvent(id=1, checksum="checksum1")
        event2 = SecurityEvent(id=2, checksum="checksum2", previous_checksum="wrong_checksum")
        events = [event1, event2]
        
        mock_db.query.return_value.order_by.return_value.all.return_value = events
        
        # Mock individual integrity verification
        with patch.object(audit_service, 'verify_event_integrity') as mock_verify:
            mock_verify.return_value = {"valid": True}
            
            # Act
            result = audit_service.verify_audit_chain_integrity()
        
        # Assert
        assert result["valid"] is False
        assert len(result["broken_chain_events"]) == 1
        assert result["broken_chain_events"][0]["event_id"] == 2
    
    def test_get_security_events_with_filters(self, audit_service, mock_db):
        """Test getting security events with various filters."""
        # Arrange
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        # Act
        events = audit_service.get_security_events(
            user_id=1,
            event_type=SecurityEventTypes.LOGIN_SUCCESS,
            event_category=SecurityEventCategories.AUTHENTICATION,
            success=True,
            limit=50,
            offset=10
        )
        
        # Assert
        assert events == []
        assert mock_query.filter.call_count == 4  # user_id, event_type, event_category, success
        mock_query.offset.assert_called_once_with(10)
        mock_query.limit.assert_called_once_with(50)
    
    def test_generate_compliance_report(self, audit_service, mock_db):
        """Test compliance report generation."""
        # Arrange
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        sample_events = [
            SecurityEvent(
                id=1,
                event_type=SecurityEventTypes.LOGIN_SUCCESS,
                event_category=SecurityEventCategories.AUTHENTICATION,
                description="Login event",
                compliance_tags=["GDPR"],
                created_at=datetime(2024, 1, 15, tzinfo=timezone.utc)
            )
        ]
        
        mock_db.query.return_value.filter.return_value.all.return_value = sample_events
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        # Act
        report = audit_service.generate_compliance_report(
            compliance_framework="GDPR",
            start_date=start_date,
            end_date=end_date,
            include_statistics=True
        )
        
        # Assert
        assert report["compliance_framework"] == "GDPR"
        assert report["total_events"] == 1
        assert "statistics" in report
        assert len(report["events"]) == 1
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_apply_retention_policy_dry_run(self, audit_service, mock_db):
        """Test retention policy application in dry run mode."""
        # Arrange
        expired_events = [
            SecurityEvent(
                id=1,
                event_type=SecurityEventTypes.LOGIN_SUCCESS,
                created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
                retention_date=datetime(2021, 1, 1, tzinfo=timezone.utc)
            )
        ]
        
        mock_db.query.return_value.filter.return_value.all.return_value = expired_events
        
        # Act
        result = audit_service.apply_retention_policy(dry_run=True)
        
        # Assert
        assert result["dry_run"] is True
        assert result["expired_events_count"] == 1
        assert len(result["expired_events"]) == 1
        mock_db.delete.assert_not_called()
    
    def test_apply_retention_policy_execute(self, audit_service, mock_db):
        """Test retention policy application with actual deletion."""
        # Arrange
        expired_events = [
            SecurityEvent(
                id=1,
                event_type=SecurityEventTypes.LOGIN_SUCCESS,
                created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
                retention_date=datetime(2021, 1, 1, tzinfo=timezone.utc)
            )
        ]
        
        mock_db.query.return_value.filter.return_value.all.return_value = expired_events
        mock_db.delete = Mock()
        mock_db.commit = Mock()
        
        # Act
        result = audit_service.apply_retention_policy(dry_run=False)
        
        # Assert
        assert result["dry_run"] is False
        assert result["deleted_events_count"] == 1
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_calculate_event_statistics(self, audit_service):
        """Test event statistics calculation."""
        # Arrange
        events = [
            SecurityEvent(
                event_type=SecurityEventTypes.LOGIN_SUCCESS,
                event_category=SecurityEventCategories.AUTHENTICATION,
                severity="INFO",
                success=True
            ),
            SecurityEvent(
                event_type=SecurityEventTypes.LOGIN_FAILURE,
                event_category=SecurityEventCategories.AUTHENTICATION,
                severity="WARNING",
                success=False
            ),
            SecurityEvent(
                event_type=SecurityEventTypes.DATA_READ,
                event_category=SecurityEventCategories.DATA_ACCESS,
                severity="INFO",
                success=True
            )
        ]
        
        # Act
        stats = audit_service._calculate_event_statistics(events)
        
        # Assert
        assert stats["total_events"] == 3
        assert stats["success_count"] == 2
        assert stats["failure_count"] == 1
        assert stats["success_rate"] == 66.67
        assert stats["event_types"][SecurityEventTypes.LOGIN_SUCCESS] == 1
        assert stats["event_categories"][SecurityEventCategories.AUTHENTICATION] == 2
        assert stats["severity_distribution"]["INFO"] == 2
        assert stats["severity_distribution"]["WARNING"] == 1


class TestSecurityEvent:
    """Test suite for SecurityEvent model."""
    
    @pytest.fixture
    def security_event(self):
        """Sample security event for testing."""
        return SecurityEvent(
            id=1,
            user_id=1,
            user_email="test@example.com",
            event_type=SecurityEventTypes.LOGIN_SUCCESS,
            event_category=SecurityEventCategories.AUTHENTICATION,
            description="Login successful",
            success=True,
            metadata={"ip": "192.168.1.1"}
        )
    
    def test_calculate_checksum(self, security_event):
        """Test checksum calculation for tamper detection."""
        # Act
        checksum = security_event.calculate_checksum()
        
        # Assert
        assert checksum is not None
        assert len(checksum) == 64  # SHA-256 hash length
        assert isinstance(checksum, str)
    
    def test_calculate_checksum_consistency(self, security_event):
        """Test that checksum calculation is consistent."""
        # Act
        checksum1 = security_event.calculate_checksum()
        checksum2 = security_event.calculate_checksum()
        
        # Assert
        assert checksum1 == checksum2
    
    def test_verify_integrity_valid(self, security_event):
        """Test integrity verification for valid event."""
        # Arrange
        security_event.checksum = security_event.calculate_checksum()
        
        # Act
        is_valid = security_event.verify_integrity()
        
        # Assert
        assert is_valid is True
    
    def test_verify_integrity_invalid(self, security_event):
        """Test integrity verification for tampered event."""
        # Arrange
        security_event.checksum = "invalid_checksum"
        
        # Act
        is_valid = security_event.verify_integrity()
        
        # Assert
        assert is_valid is False
    
    def test_set_retention_policy(self, security_event):
        """Test setting retention policy."""
        # Act
        security_event.set_retention_policy(365, ["GDPR", "SOC2"])
        
        # Assert
        assert security_event.retention_date is not None
        assert security_event.compliance_tags == ["GDPR", "SOC2"]
    
    def test_to_audit_dict(self, security_event):
        """Test conversion to audit dictionary."""
        # Act
        audit_dict = security_event.to_audit_dict()
        
        # Assert
        assert audit_dict["id"] == 1
        assert audit_dict["user_id"] == 1
        assert audit_dict["event_type"] == SecurityEventTypes.LOGIN_SUCCESS
        assert audit_dict["success"] is True
        assert audit_dict["metadata"] == {"ip": "192.168.1.1"}
    
    def test_validation_empty_event_type(self):
        """Test validation for empty event type."""
        with pytest.raises(ValueError):
            event = SecurityEvent(
                event_type="",
                event_category=SecurityEventCategories.AUTHENTICATION,
                description="Test event"
            )
            event.validate_required_fields("event_type", "")
    
    def test_validation_invalid_severity(self):
        """Test validation for invalid severity."""
        with pytest.raises(ValueError):
            event = SecurityEvent()
            event.validate_severity("severity", "INVALID")


if __name__ == "__main__":
    pytest.main([__file__])