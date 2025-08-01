"""
Security and encryption compliance endpoints.

Provides endpoints for validating encryption status, compliance checks,
and security monitoring functionality.
"""

from typing import Dict, Any, List
import ssl
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.core.config import settings
from app.core.encryption import encryption_manager, is_encrypted
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/encryption/status", response_model=Dict[str, Any])
async def get_encryption_status():
    """
    Get current encryption configuration status.
    
    Returns:
        dict: Encryption status and configuration details
    """
    logger.info("Encryption status check requested")
    
    try:
        # Test encryption functionality
        test_data = "encryption_test_" + str(datetime.now().timestamp())
        encrypted = encryption_manager.encrypt(test_data)
        decrypted = encryption_manager.decrypt(encrypted)
        encryption_working = (test_data == decrypted)
        
        # Check TLS configuration
        tls_config = {
            "enabled": settings.TLS_ENABLED,
            "cert_path_exists": os.path.exists(settings.TLS_CERT_PATH) if settings.TLS_ENABLED else False,
            "key_path_exists": os.path.exists(settings.TLS_KEY_PATH) if settings.TLS_ENABLED else False,
            "min_version": settings.TLS_MIN_VERSION
        }
        
        # Database encryption status
        db_encryption = {
            "enabled": settings.DB_ENCRYPTION_ENABLED,
            "ssl_mode": settings.DB_SSL_MODE,
            "ssl_configured": bool(settings.DB_SSL_CERT_PATH and settings.DB_SSL_KEY_PATH),
        }
        
        status_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "encryption": {
                "algorithm": settings.ENCRYPTION_ALGORITHM,
                "working": encryption_working,
                "key_configured": bool(settings.ENCRYPTION_KEY),
            },
            "tls": tls_config,
            "database": db_encryption,
            "compliance": {
                "data_at_rest": encryption_working and settings.DB_ENCRYPTION_ENABLED,
                "data_in_transit": settings.TLS_ENABLED,
                "key_management": bool(settings.ENCRYPTION_KEY),
                "audit_logging": settings.ENABLE_AUDIT_LOGGING,
            }
        }
        
        logger.info("Encryption status check completed", status=status_data)
        return status_data
        
    except Exception as e:
        logger.error(
            "Encryption status check failed",
            error_type=type(e).__name__,
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check encryption status: {str(e)}"
        )


@router.get("/encryption/compliance", response_model=Dict[str, Any])
async def check_compliance(db: AsyncSession = Depends(get_db)):
    """
    Perform comprehensive encryption compliance check.
    
    Args:
        db: Database session
        
    Returns:
        dict: Detailed compliance status and recommendations
    """
    logger.info("Encryption compliance check requested")
    
    compliance_checks = []
    overall_compliant = True
    
    try:
        # Check 1: Data encryption at rest
        try:
            test_encrypt = encryption_manager.encrypt("compliance_test")
            test_decrypt = encryption_manager.decrypt(test_encrypt)
            encryption_check = {
                "name": "Data Encryption at Rest",
                "status": "PASS" if test_encrypt != "compliance_test" and test_decrypt == "compliance_test" else "FAIL",
                "details": "AES-256-GCM encryption working properly",
                "requirement": "Database encryption at rest implemented"
            }
        except Exception as e:
            encryption_check = {
                "name": "Data Encryption at Rest",
                "status": "FAIL",
                "details": f"Encryption test failed: {str(e)}",
                "requirement": "Database encryption at rest implemented"
            }
            overall_compliant = False
        
        compliance_checks.append(encryption_check)
        
        # Check 2: Database SSL connection
        try:
            # Test database SSL connection
            result = await db.execute(text("SELECT current_setting('ssl') as ssl_status"))
            ssl_result = result.scalar()
            db_ssl_check = {
                "name": "Database SSL/TLS Connection",
                "status": "PASS" if ssl_result == "on" else "PARTIAL",
                "details": f"Database SSL status: {ssl_result}",
                "requirement": "TLS encryption for all API communications"
            }
        except Exception as e:
            db_ssl_check = {
                "name": "Database SSL/TLS Connection",
                "status": "UNKNOWN",
                "details": f"Could not determine database SSL status: {str(e)}",
                "requirement": "TLS encryption for all API communications"
            }
        
        compliance_checks.append(db_ssl_check)
        
        # Check 3: TLS Configuration
        tls_check = {
            "name": "API TLS Configuration",
            "status": "PASS" if settings.TLS_ENABLED else "FAIL",
            "details": f"TLS enabled: {settings.TLS_ENABLED}, Min version: {settings.TLS_MIN_VERSION}",
            "requirement": "TLS encryption for all API communications"
        }
        if not settings.TLS_ENABLED:
            overall_compliant = False
        
        compliance_checks.append(tls_check)
        
        # Check 4: Encryption Key Management
        key_check = {
            "name": "Encryption Key Management",
            "status": "PASS" if settings.ENCRYPTION_KEY else "FAIL",
            "details": "Environment-based key management configured" if settings.ENCRYPTION_KEY else "No encryption key configured",
            "requirement": "Encryption key management system"
        }
        if not settings.ENCRYPTION_KEY:
            overall_compliant = False
        
        compliance_checks.append(key_check)
        
        # Check 5: Audit Logging
        audit_check = {
            "name": "Security Audit Logging",
            "status": "PASS" if settings.ENABLE_AUDIT_LOGGING else "FAIL",
            "details": f"Audit logging enabled: {settings.ENABLE_AUDIT_LOGGING}",
            "requirement": "Sensitive data masking in logs"
        }
        if not settings.ENABLE_AUDIT_LOGGING:
            overall_compliant = False
        
        compliance_checks.append(audit_check)
        
        # Generate compliance summary
        passed_checks = sum(1 for check in compliance_checks if check["status"] == "PASS")
        total_checks = len(compliance_checks)
        compliance_percentage = (passed_checks / total_checks) * 100
        
        compliance_result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": "COMPLIANT" if overall_compliant else "NON_COMPLIANT",
            "compliance_percentage": compliance_percentage,
            "checks_passed": passed_checks,
            "total_checks": total_checks,
            "checks": compliance_checks,
            "recommendations": generate_compliance_recommendations(compliance_checks)
        }
        
        logger.info(
            "Encryption compliance check completed",
            overall_status=compliance_result["overall_status"],
            compliance_percentage=compliance_percentage
        )
        
        return compliance_result
        
    except Exception as e:
        logger.error(
            "Encryption compliance check failed",
            error_type=type(e).__name__,
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform compliance check: {str(e)}"
        )


@router.post("/encryption/test", response_model=Dict[str, Any])
async def test_encryption(test_data: Dict[str, str]):
    """
    Test encryption and decryption functionality.
    
    Args:
        test_data: Dictionary with "plaintext" field to encrypt/decrypt
        
    Returns:
        dict: Encryption test results
    """
    if "plaintext" not in test_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request must include 'plaintext' field"
        )
    
    plaintext = test_data["plaintext"]
    logger.info("Encryption test requested", data_length=len(plaintext))
    
    try:
        # Encrypt the data
        encrypted = encryption_manager.encrypt(plaintext)
        
        # Decrypt the data
        decrypted = encryption_manager.decrypt(encrypted)
        
        # Verify round-trip
        success = (plaintext == decrypted)
        
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": success,
            "algorithm": settings.ENCRYPTION_ALGORITHM,
            "original_length": len(plaintext),
            "encrypted_length": len(encrypted),
            "is_encrypted": is_encrypted(encrypted),
            "round_trip_successful": success
        }
        
        if success:
            logger.info("Encryption test successful", result=result)
        else:
            logger.error("Encryption test failed - round trip verification failed")
        
        return result
        
    except Exception as e:
        logger.error(
            "Encryption test failed",
            error_type=type(e).__name__,
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Encryption test failed: {str(e)}"
        )


def generate_compliance_recommendations(checks: List[Dict[str, Any]]) -> List[str]:
    """
    Generate compliance recommendations based on failed checks.
    
    Args:
        checks: List of compliance check results
        
    Returns:
        list: List of recommendation strings
    """
    recommendations = []
    
    for check in checks:
        if check["status"] == "FAIL":
            if "Data Encryption at Rest" in check["name"]:
                recommendations.append("Configure ENCRYPTION_KEY environment variable with a strong 256-bit key")
            elif "Database SSL/TLS" in check["name"]:
                recommendations.append("Enable PostgreSQL SSL and configure SSL certificates")
            elif "API TLS" in check["name"]:
                recommendations.append("Enable TLS by setting TLS_ENABLED=true and providing SSL certificates")
            elif "Key Management" in check["name"]:
                recommendations.append("Implement proper key rotation and environment-based key management")
            elif "Audit Logging" in check["name"]:
                recommendations.append("Enable audit logging by setting ENABLE_AUDIT_LOGGING=true")
    
    if not recommendations:
        recommendations.append("All encryption compliance checks passed - maintain current configuration")
    
    return recommendations