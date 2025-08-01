"""
Data encryption utilities for secure data handling.

Provides AES-256-GCM encryption for sensitive data fields,
key management, and secure data handling utilities.
"""

import os
import base64
import hashlib
from typing import Optional, Union, Dict, Any
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class EncryptionManager:
    """
    Manages data encryption and decryption using AES-256-GCM.
    
    Provides secure encryption for sensitive data fields with
    key derivation and secure random nonce generation.
    """
    
    def __init__(self):
        """Initialize encryption manager with derived key."""
        self._key = self._derive_key()
        self._cipher = AESGCM(self._key)
    
    def _derive_key(self) -> bytes:
        """
        Derive encryption key from master key using PBKDF2.
        
        Returns:
            bytes: Derived 256-bit encryption key
        """
        # Use a fixed salt for consistent key derivation
        # In production, consider using per-field salts stored with data
        salt = hashlib.sha256(b"sprint-reports-v2-encryption-salt").digest()[:16]
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=salt,
            iterations=settings.KEY_DERIVATION_ITERATIONS,
            backend=default_backend()
        )
        
        key = kdf.derive(settings.ENCRYPTION_KEY.encode())
        return key
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext data using AES-256-GCM.
        
        Args:
            plaintext: Data to encrypt
            
        Returns:
            str: Base64-encoded encrypted data with nonce
            
        Raises:
            ValueError: If encryption fails
        """
        if not plaintext:
            return plaintext
        
        try:
            # Generate random nonce
            nonce = os.urandom(12)  # 96-bit nonce for GCM
            
            # Encrypt data
            ciphertext = self._cipher.encrypt(nonce, plaintext.encode('utf-8'), None)
            
            # Combine nonce and ciphertext, then base64 encode
            encrypted_data = nonce + ciphertext
            encoded_data = base64.b64encode(encrypted_data).decode('utf-8')
            
            logger.debug(
                "Data encrypted successfully",
                data_length=len(plaintext),
                encrypted_length=len(encoded_data)
            )
            
            return encoded_data
            
        except Exception as e:
            logger.error(
                "Encryption failed",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise ValueError(f"Encryption failed: {str(e)}")
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt encrypted data using AES-256-GCM.
        
        Args:
            encrypted_data: Base64-encoded encrypted data with nonce
            
        Returns:
            str: Decrypted plaintext data
            
        Raises:
            ValueError: If decryption fails
        """
        if not encrypted_data:
            return encrypted_data
        
        try:
            # Base64 decode
            decoded_data = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Extract nonce and ciphertext
            nonce = decoded_data[:12]  # First 12 bytes are nonce
            ciphertext = decoded_data[12:]  # Rest is ciphertext
            
            # Decrypt data
            plaintext_bytes = self._cipher.decrypt(nonce, ciphertext, None)
            plaintext = plaintext_bytes.decode('utf-8')
            
            logger.debug(
                "Data decrypted successfully",
                encrypted_length=len(encrypted_data),
                decrypted_length=len(plaintext)
            )
            
            return plaintext
            
        except Exception as e:
            logger.error(
                "Decryption failed",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def encrypt_dict(self, data: Dict[str, Any], fields_to_encrypt: list) -> Dict[str, Any]:
        """
        Encrypt specified fields in a dictionary.
        
        Args:
            data: Dictionary containing data to encrypt
            fields_to_encrypt: List of field names to encrypt
            
        Returns:
            Dict: Dictionary with specified fields encrypted
        """
        result = data.copy()
        
        for field in fields_to_encrypt:
            if field in result and result[field] is not None:
                if isinstance(result[field], str):
                    result[field] = self.encrypt(result[field])
                else:
                    # Convert to string first
                    result[field] = self.encrypt(str(result[field]))
        
        return result
    
    def decrypt_dict(self, data: Dict[str, Any], fields_to_decrypt: list) -> Dict[str, Any]:
        """
        Decrypt specified fields in a dictionary.
        
        Args:
            data: Dictionary containing encrypted data
            fields_to_decrypt: List of field names to decrypt
            
        Returns:
            Dict: Dictionary with specified fields decrypted
        """
        result = data.copy()
        
        for field in fields_to_decrypt:
            if field in result and result[field] is not None:
                result[field] = self.decrypt(result[field])
        
        return result


# Global encryption manager instance
encryption_manager = EncryptionManager()


def encrypt_sensitive_field(value: Optional[str]) -> Optional[str]:
    """
    Convenience function to encrypt a sensitive field.
    
    Args:
        value: Value to encrypt
        
    Returns:
        str: Encrypted value or None if input was None
    """
    if value is None:
        return None
    return encryption_manager.encrypt(value)


def decrypt_sensitive_field(encrypted_value: Optional[str]) -> Optional[str]:
    """
    Convenience function to decrypt a sensitive field.
    
    Args:
        encrypted_value: Encrypted value to decrypt
        
    Returns:
        str: Decrypted value or None if input was None
    """
    if encrypted_value is None:
        return None
    return encryption_manager.decrypt(encrypted_value)


def is_encrypted(value: str) -> bool:
    """
    Check if a value appears to be encrypted (base64 format).
    
    Args:
        value: Value to check
        
    Returns:
        bool: True if value appears encrypted
    """
    if not value:
        return False
    
    try:
        # Try to decode as base64
        decoded = base64.b64decode(value.encode('utf-8'))
        # Encrypted data should be at least 12 bytes (nonce) + some ciphertext
        return len(decoded) >= 13
    except Exception:
        return False


# List of sensitive fields that should always be encrypted
SENSITIVE_FIELDS = [
    'password',
    'api_token',
    'api_key',
    'secret',
    'private_key',
    'email',  # Consider PII
    'phone',  # Consider PII
    'ssn',
    'credit_card',
    'personal_data'
]


def should_encrypt_field(field_name: str) -> bool:
    """
    Determine if a field should be encrypted based on its name.
    
    Args:
        field_name: Name of the field to check
        
    Returns:
        bool: True if field should be encrypted
    """
    field_lower = field_name.lower()
    return any(sensitive in field_lower for sensitive in SENSITIVE_FIELDS)