"""
Audit management endpoints.

Provides API endpoints for security audit event management, integrity verification,
compliance reporting, and retention policy management.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.services.audit_service import AuditService, get_audit_service
from app.models.security import SecurityEvent, SecurityEventTypes, SecurityEventCategories
from app.models.user import User
from pydantic import BaseModel, Field

# Initialize router and security
router = APIRouter()
security = HTTPBearer()


# Pydantic schemas for request/response
class SecurityEventResponse(BaseModel):
    """Security event response schema."""
    id: int
    event_type: str
    event_category: str
    description: str
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    user_ip: Optional[str] = None
    success: bool
    severity: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    correlation_id: Optional[str] = None
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    compliance_tags: Optional[List[str]] = None
    
    class Config:
        from_attributes = True


class IntegrityVerificationResponse(BaseModel):
    """Integrity verification response schema."""
    valid: bool
    event_id: int
    checksum_valid: bool
    chain_valid: bool
    chain_error: Optional[str] = None
    calculated_checksum: str
    stored_checksum: str
    previous_checksum: Optional[str] = None


class ChainVerificationResponse(BaseModel):
    """Audit chain verification response schema."""
    valid: bool
    total_events: int
    verified_events: int
    invalid_events: List[Dict[str, Any]]
    broken_chain_events: List[Dict[str, Any]]
    verification_date: str


class ComplianceReportRequest(BaseModel):
    """Compliance report request schema."""
    compliance_framework: str = Field(..., description="Compliance framework (GDPR, SOC2, etc.)")
    start_date: datetime = Field(..., description="Report start date")
    end_date: datetime = Field(..., description="Report end date")
    include_statistics: bool = Field(True, description="Include event statistics")


class RetentionPolicyResponse(BaseModel):
    """Retention policy response schema."""
    dry_run: bool
    expired_events_count: int
    deleted_events_count: Optional[int] = None
    retention_applied_at: Optional[str] = None
    expired_events: Optional[List[Dict[str, Any]]] = None


# Dependency to get current user (placeholder - will be implemented with auth)
async def get_current_user(token: str = Depends(security)) -> User:
    """Get current authenticated user (placeholder implementation)."""
    # TODO: Implement JWT token validation and user extraction
    # For now, return a mock user for development
    return User(id=1, email="admin@example.com", username="admin", is_superuser=True)


# Dependency to check admin permissions
async def require_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Require admin user for sensitive audit operations."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Admin access required for audit operations"
        )
    return current_user


@router.get("/events", response_model=List[SecurityEventResponse])
async def get_security_events(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    event_category: Optional[str] = Query(None, description="Filter by event category"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    current_user: User = Depends(require_admin_user),
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Retrieve security audit events with filtering and pagination.
    
    Supports filtering by user, event type, date range, and success status.
    Requires admin permissions.
    """
    if not settings.ENABLE_AUDIT_LOGGING:
        raise HTTPException(
            status_code=503,
            detail="Audit logging is disabled"
        )
    
    try:
        events = audit_service.get_security_events(
            user_id=user_id,
            event_type=event_type,
            event_category=event_category,
            start_date=start_date,
            end_date=end_date,
            success=success,
            limit=limit,
            offset=offset
        )
        
        return events
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve security events: {str(e)}"
        )


@router.get("/events/{event_id}/verify", response_model=IntegrityVerificationResponse)
async def verify_event_integrity(
    event_id: int,
    current_user: User = Depends(require_admin_user),
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Verify the integrity of a specific security event.
    
    Checks the event's tamper detection checksum and chain integrity.
    Requires admin permissions.
    """
    if not settings.ENABLE_AUDIT_LOGGING:
        raise HTTPException(
            status_code=503,
            detail="Audit logging is disabled"
        )
    
    try:
        verification_result = audit_service.verify_event_integrity(event_id)
        
        if "error" in verification_result:
            raise HTTPException(
                status_code=404 if "not found" in verification_result["error"].lower() else 500,
                detail=verification_result["error"]
            )
        
        return verification_result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to verify event integrity: {str(e)}"
        )


@router.get("/chain/verify", response_model=ChainVerificationResponse)
async def verify_audit_chain(
    start_date: Optional[datetime] = Query(None, description="Start date for verification"),
    end_date: Optional[datetime] = Query(None, description="End date for verification"),
    current_user: User = Depends(require_admin_user),
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Verify the integrity of the entire audit chain.
    
    Checks all events in the specified date range for tampering and chain breaks.
    Requires admin permissions.
    """
    if not settings.ENABLE_AUDIT_LOGGING or not settings.AUDIT_CHAIN_VERIFICATION:
        raise HTTPException(
            status_code=503,
            detail="Audit chain verification is disabled"
        )
    
    try:
        verification_result = audit_service.verify_audit_chain_integrity(
            start_date=start_date,
            end_date=end_date
        )
        
        if "error" in verification_result:
            raise HTTPException(
                status_code=500,
                detail=verification_result["error"]
            )
        
        return verification_result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to verify audit chain: {str(e)}"
        )


@router.post("/reports/compliance")
async def generate_compliance_report(
    request: ComplianceReportRequest,
    current_user: User = Depends(require_admin_user),
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Generate compliance report for audit events.
    
    Creates a comprehensive report for the specified compliance framework
    and date range. Requires admin permissions.
    """
    if not settings.ENABLE_AUDIT_LOGGING:
        raise HTTPException(
            status_code=503,
            detail="Audit logging is disabled"
        )
    
    # Validate compliance framework
    if request.compliance_framework not in settings.AUDIT_COMPLIANCE_FRAMEWORKS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported compliance framework. Supported: {settings.AUDIT_COMPLIANCE_FRAMEWORKS}"
        )
    
    # Validate date range
    if request.start_date >= request.end_date:
        raise HTTPException(
            status_code=400,
            detail="Start date must be before end date"
        )
    
    # Limit report to reasonable time ranges (max 1 year)
    if (request.end_date - request.start_date).days > 365:
        raise HTTPException(
            status_code=400,
            detail="Report date range cannot exceed 365 days"
        )
    
    try:
        report = audit_service.generate_compliance_report(
            compliance_framework=request.compliance_framework,
            start_date=request.start_date,
            end_date=request.end_date,
            include_statistics=request.include_statistics
        )
        
        return report
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate compliance report: {str(e)}"
        )


@router.post("/retention/apply", response_model=RetentionPolicyResponse)
async def apply_retention_policy(
    dry_run: bool = Query(True, description="If true, only preview deletions without executing"),
    current_user: User = Depends(require_admin_user),
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Apply log retention policies to audit events.
    
    Deletes or previews deletion of audit events that have exceeded their
    retention period. Requires admin permissions.
    """
    if not settings.ENABLE_AUDIT_LOGGING:
        raise HTTPException(
            status_code=503,
            detail="Audit logging is disabled"
        )
    
    try:
        result = audit_service.apply_retention_policy(dry_run=dry_run)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply retention policy: {str(e)}"
        )


@router.get("/statistics")
async def get_audit_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(require_admin_user),
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Get audit statistics for the specified time period.
    
    Provides summary statistics on security events, success rates,
    and event type distributions. Requires admin permissions.
    """
    if not settings.ENABLE_AUDIT_LOGGING:
        raise HTTPException(
            status_code=503,
            detail="Audit logging is disabled"
        )
    
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        events = audit_service.get_security_events(
            start_date=start_date,
            end_date=end_date,
            limit=10000  # Large limit for statistics
        )
        
        statistics = audit_service._calculate_event_statistics(events)
        statistics["period_days"] = days
        statistics["start_date"] = start_date.isoformat()
        statistics["end_date"] = end_date.isoformat()
        
        return statistics
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get audit statistics: {str(e)}"
        )


@router.get("/event-types")
async def get_event_types():
    """
    Get available security event types and categories.
    
    Returns the complete list of supported event types and categories
    for filtering and reporting purposes.
    """
    return {
        "event_types": {
            "authentication": [
                SecurityEventTypes.LOGIN_SUCCESS,
                SecurityEventTypes.LOGIN_FAILURE,
                SecurityEventTypes.LOGOUT,
                SecurityEventTypes.TOKEN_REFRESH,
                SecurityEventTypes.TOKEN_REVOCATION,
                SecurityEventTypes.PASSWORD_CHANGE,
                SecurityEventTypes.PASSWORD_RESET,
                SecurityEventTypes.MFA_ENABLED,
                SecurityEventTypes.MFA_DISABLED,
                SecurityEventTypes.MFA_SUCCESS,
                SecurityEventTypes.MFA_FAILURE,
            ],
            "authorization": [
                SecurityEventTypes.ACCESS_GRANTED,
                SecurityEventTypes.ACCESS_DENIED,
                SecurityEventTypes.PERMISSION_ESCALATION,
                SecurityEventTypes.ROLE_ASSIGNED,
                SecurityEventTypes.ROLE_REVOKED,
            ],
            "data_access": [
                SecurityEventTypes.DATA_READ,
                SecurityEventTypes.DATA_CREATE,
                SecurityEventTypes.DATA_UPDATE,
                SecurityEventTypes.DATA_DELETE,
                SecurityEventTypes.DATA_EXPORT,
                SecurityEventTypes.DATA_IMPORT,
            ],
            "security_violations": [
                SecurityEventTypes.RATE_LIMIT_EXCEEDED,
                SecurityEventTypes.SUSPICIOUS_ACTIVITY,
                SecurityEventTypes.SECURITY_POLICY_VIOLATION,
                SecurityEventTypes.BRUTE_FORCE_ATTEMPT,
            ],
            "system": [
                SecurityEventTypes.CONFIGURATION_CHANGE,
                SecurityEventTypes.SECURITY_UPDATE,
                SecurityEventTypes.BACKUP_CREATED,
                SecurityEventTypes.BACKUP_RESTORED,
            ]
        },
        "event_categories": [
            SecurityEventCategories.AUTHENTICATION,
            SecurityEventCategories.AUTHORIZATION,
            SecurityEventCategories.DATA_ACCESS,
            SecurityEventCategories.SECURITY_VIOLATION,
            SecurityEventCategories.SYSTEM_SECURITY,
            SecurityEventCategories.COMPLIANCE,
        ],
        "severity_levels": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        "compliance_frameworks": settings.AUDIT_COMPLIANCE_FRAMEWORKS
    }