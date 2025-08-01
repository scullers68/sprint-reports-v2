"""
Audit service for security event management and tamper detection.

Provides comprehensive audit logging, tamper detection, compliance reporting,
and log retention management extending existing database patterns.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_db
from app.core.logging import get_logger, LoggerMixin
from app.models.security import SecurityEvent, AuditLog, SecurityEventTypes, SecurityEventCategories
from app.models.user import User
from app.core.config import settings


class AuditService(LoggerMixin):
    """
    Service for managing security audit events and compliance reporting.
    
    Extends existing service patterns to provide comprehensive audit logging,
    tamper detection, and compliance reporting capabilities.
    """
    
    def __init__(self, db: AsyncSession):
        """Initialize audit service with database session."""
        self.db = db
        self.enabled = settings.ENABLE_AUDIT_LOGGING
    
    async def create_security_event(
        self,
        event_type: str,
        event_category: str,
        description: str,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
        user_ip: Optional[str] = None,
        success: bool = True,
        severity: str = "INFO",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        correlation_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        failure_reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        compliance_tags: Optional[List[str]] = None,
        retention_days: int = 2555  # 7 years default for compliance
    ) -> Optional[SecurityEvent]:
        """
        Create and persist a security audit event.
        
        Args:
            event_type: Type of security event
            event_category: Category of the event
            description: Human-readable description
            user_id: Optional user ID
            user_email: Optional user email
            user_ip: Optional user IP address
            success: Whether the event was successful
            severity: Severity level
            resource_type: Type of resource involved
            resource_id: ID of resource involved
            resource_name: Name of resource involved
            correlation_id: Request correlation ID
            user_agent: User agent string
            request_method: HTTP method
            request_path: Request path
            failure_reason: Reason for failure
            metadata: Additional metadata
            compliance_tags: Compliance framework tags
            retention_days: Number of days to retain the event
            
        Returns:
            SecurityEvent: Created security event or None if disabled
        """
        if not self.enabled:
            return None
            
        try:
            # Create security event
            event = SecurityEvent(
                user_id=user_id,
                user_email=user_email,
                user_ip=user_ip,
                event_type=event_type,
                event_category=event_category,
                severity=severity,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                success=success,
                failure_reason=failure_reason,
                description=description,
                correlation_id=correlation_id,
                user_agent=user_agent,
                request_method=request_method,
                request_path=request_path,
                metadata=metadata
            )
            
            # Set retention policy
            if retention_days > 0:
                event.set_retention_policy(retention_days, compliance_tags)
            
            # Add to database session
            self.db.add(event)
            self.db.flush()  # Get the ID without committing
            
            # Calculate and set tamper detection checksum
            event.checksum = event.calculate_checksum()
            
            # Set chain integrity (link to previous event)
            previous_event = self._get_last_event_checksum()
            if previous_event:
                event.previous_checksum = previous_event
            
            # Commit the transaction
            self.db.commit()
            
            self.logger.info(
                "Security event created",
                event_id=event.id,
                event_type=event_type,
                user_id=user_id,
                success=success
            )
            
            return event
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(
                "Failed to create security event",
                event_type=event_type,
                error=str(e)
            )
            raise
    
    def verify_event_integrity(self, event_id: int) -> Dict[str, Any]:
        """
        Verify the integrity of a security event.
        
        Args:
            event_id: ID of the event to verify
            
        Returns:
            Dict containing verification results
        """
        try:
            event = self.db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
            
            if not event:
                return {
                    "valid": False,
                    "error": "Event not found",
                    "event_id": event_id
                }
            
            # Verify checksum
            calculated_checksum = event.calculate_checksum()
            checksum_valid = calculated_checksum == event.checksum
            
            # Verify chain integrity
            chain_valid = True
            chain_error = None
            
            if event.previous_checksum:
                # Find the previous event
                previous_event = (
                    self.db.query(SecurityEvent)
                    .filter(
                        and_(
                            SecurityEvent.id < event.id,
                            SecurityEvent.checksum == event.previous_checksum
                        )
                    )
                    .order_by(desc(SecurityEvent.id))
                    .first()
                )
                
                if not previous_event:
                    chain_valid = False
                    chain_error = "Previous event not found in chain"
            
            return {
                "valid": checksum_valid and chain_valid,
                "event_id": event.id,
                "checksum_valid": checksum_valid,
                "chain_valid": chain_valid,
                "chain_error": chain_error,
                "calculated_checksum": calculated_checksum,
                "stored_checksum": event.checksum,
                "previous_checksum": event.previous_checksum
            }
            
        except SQLAlchemyError as e:
            self.logger.error(
                "Failed to verify event integrity",
                event_id=event_id,
                error=str(e)
            )
            return {
                "valid": False,
                "error": str(e),
                "event_id": event_id
            }
    
    def verify_audit_chain_integrity(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Verify the integrity of the entire audit chain.
        
        Args:
            start_date: Optional start date for verification
            end_date: Optional end date for verification
            
        Returns:
            Dict containing chain verification results
        """
        try:
            query = self.db.query(SecurityEvent).order_by(SecurityEvent.id)
            
            if start_date:
                query = query.filter(SecurityEvent.created_at >= start_date)
            if end_date:
                query = query.filter(SecurityEvent.created_at <= end_date)
            
            events = query.all()
            
            if not events:
                return {
                    "valid": True,
                    "total_events": 0,
                    "verified_events": 0,
                    "invalid_events": [],
                    "broken_chain_events": []
                }
            
            verified_count = 0
            invalid_events = []
            broken_chain_events = []
            previous_checksum = None
            
            for event in events:
                # Verify individual event integrity
                verification = self.verify_event_integrity(event.id)
                
                if verification["valid"]:
                    verified_count += 1
                else:
                    invalid_events.append({
                        "event_id": event.id,
                        "error": verification.get("error", "Unknown error")
                    })
                
                # Verify chain linkage
                if previous_checksum and event.previous_checksum != previous_checksum:
                    broken_chain_events.append({
                        "event_id": event.id,
                        "expected_previous": previous_checksum,
                        "actual_previous": event.previous_checksum
                    })
                
                previous_checksum = event.checksum
            
            return {
                "valid": len(invalid_events) == 0 and len(broken_chain_events) == 0,
                "total_events": len(events),
                "verified_events": verified_count,
                "invalid_events": invalid_events,
                "broken_chain_events": broken_chain_events,
                "verification_date": datetime.now(timezone.utc).isoformat()
            }
            
        except SQLAlchemyError as e:
            self.logger.error(
                "Failed to verify audit chain integrity",
                error=str(e)
            )
            return {
                "valid": False,
                "error": str(e),
                "verification_date": datetime.now(timezone.utc).isoformat()
            }
    
    def get_security_events(
        self,
        user_id: Optional[int] = None,
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        success: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[SecurityEvent]:
        """
        Retrieve security events with filtering.
        
        Args:
            user_id: Filter by user ID
            event_type: Filter by event type
            event_category: Filter by event category
            start_date: Filter by start date
            end_date: Filter by end date
            success: Filter by success status
            limit: Maximum number of events to return
            offset: Number of events to skip
            
        Returns:
            List of security events
        """
        try:
            query = self.db.query(SecurityEvent).order_by(desc(SecurityEvent.created_at))
            
            # Apply filters
            if user_id:
                query = query.filter(SecurityEvent.user_id == user_id)
            if event_type:
                query = query.filter(SecurityEvent.event_type == event_type)
            if event_category:
                query = query.filter(SecurityEvent.event_category == event_category)
            if start_date:
                query = query.filter(SecurityEvent.created_at >= start_date)
            if end_date:
                query = query.filter(SecurityEvent.created_at <= end_date)
            if success is not None:
                query = query.filter(SecurityEvent.success == success)
            
            # Apply pagination
            events = query.offset(offset).limit(limit).all()
            
            return events
            
        except SQLAlchemyError as e:
            self.logger.error(
                "Failed to retrieve security events",
                error=str(e)
            )
            return []
    
    def generate_compliance_report(
        self,
        compliance_framework: str,
        start_date: datetime,
        end_date: datetime,
        include_statistics: bool = True
    ) -> Dict[str, Any]:
        """
        Generate compliance report for audit events.
        
        Args:
            compliance_framework: Compliance framework (GDPR, SOC2, etc.)
            start_date: Report start date
            end_date: Report end date
            include_statistics: Whether to include statistics
            
        Returns:
            Dict containing compliance report data
        """
        try:
            # Query events with compliance tags
            events = self.db.query(SecurityEvent).filter(
                and_(
                    SecurityEvent.created_at >= start_date,
                    SecurityEvent.created_at <= end_date,
                    SecurityEvent.compliance_tags.contains([compliance_framework])
                )
            ).all()
            
            report = {
                "compliance_framework": compliance_framework,
                "report_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_events": len(events),
                "events": [event.to_audit_dict() for event in events]
            }
            
            if include_statistics:
                report["statistics"] = self._calculate_event_statistics(events)
            
            # Create audit log entry
            audit_log = AuditLog(
                log_type="compliance_report",
                log_level="INFO",
                start_time=start_date,
                end_time=end_date,
                event_count=len(events),
                compliance_period=f"{start_date.strftime('%Y-%m')}_to_{end_date.strftime('%Y-%m')}",
                compliance_framework=compliance_framework,
                summary=report,
                log_checksum=hashlib.sha256(
                    json.dumps(report, sort_keys=True, default=str).encode()
                ).hexdigest()
            )
            
            self.db.add(audit_log)
            self.db.commit()
            
            self.logger.info(
                "Compliance report generated",
                framework=compliance_framework,
                event_count=len(events),
                report_id=audit_log.id
            )
            
            return report
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(
                "Failed to generate compliance report",
                framework=compliance_framework,
                error=str(e)
            )
            raise
    
    def apply_retention_policy(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Apply log retention policies to audit events.
        
        Args:
            dry_run: If True, only count events without deleting
            
        Returns:
            Dict containing retention policy results
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            # Find events past their retention date
            expired_events = self.db.query(SecurityEvent).filter(
                and_(
                    SecurityEvent.retention_date.isnot(None),
                    SecurityEvent.retention_date <= current_time
                )
            ).all()
            
            if dry_run:
                return {
                    "dry_run": True,
                    "expired_events_count": len(expired_events),
                    "expired_events": [
                        {
                            "id": event.id,
                            "event_type": event.event_type,
                            "created_at": event.created_at.isoformat(),
                            "retention_date": event.retention_date.isoformat()
                        }
                        for event in expired_events
                    ]
                }
            
            # Delete expired events
            deleted_count = 0
            for event in expired_events:
                self.db.delete(event)
                deleted_count += 1
            
            self.db.commit()
            
            self.logger.info(
                "Retention policy applied",
                deleted_count=deleted_count
            )
            
            return {
                "dry_run": False,
                "deleted_events_count": deleted_count,
                "retention_applied_at": current_time.isoformat()
            }
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(
                "Failed to apply retention policy",
                error=str(e)
            )
            raise
    
    def _get_last_event_checksum(self) -> Optional[str]:
        """Get the checksum of the last security event for chain integrity."""
        last_event = (
            self.db.query(SecurityEvent)
            .order_by(desc(SecurityEvent.id))
            .first()
        )
        
        return last_event.checksum if last_event else None
    
    def _calculate_event_statistics(self, events: List[SecurityEvent]) -> Dict[str, Any]:
        """Calculate statistics for a list of events."""
        if not events:
            return {}
        
        # Group by event type
        event_types = {}
        event_categories = {}
        success_count = 0
        failure_count = 0
        severity_counts = {}
        
        for event in events:
            # Event types
            event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
            
            # Event categories
            event_categories[event.event_category] = event_categories.get(event.event_category, 0) + 1
            
            # Success/failure
            if event.success:
                success_count += 1
            else:
                failure_count += 1
            
            # Severity
            severity_counts[event.severity] = severity_counts.get(event.severity, 0) + 1
        
        return {
            "total_events": len(events),
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": round(success_count / len(events) * 100, 2),
            "event_types": event_types,
            "event_categories": event_categories,
            "severity_distribution": severity_counts
        }


def get_audit_service(db: AsyncSession = None) -> AuditService:
    """
    Get audit service instance.
    
    Args:
        db: Optional database session
        
    Returns:
        AuditService: Configured audit service
    """
    if db is None:
        db = next(get_db())
    
    return AuditService(db)