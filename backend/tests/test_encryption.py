"""
Tests for encryption functionality and compliance.

Tests the encryption utilities, sensitive data masking,
and compliance validation features.
"""

import pytest
import base64
from unittest.mock import patch, MagicMock

from app.core.encryption import (
    EncryptionManager, 
    encrypt_sensitive_field, 
    decrypt_sensitive_field,
    is_encrypted,
    should_encrypt_field,
    SENSITIVE_FIELDS
)
from app.core.logging import mask_sensitive_data, SensitiveDataMaskingProcessor


class TestEncryptionManager:
    """Test the EncryptionManager class."""
    
    def test_encryption_roundtrip(self):
        """Test that encryption and decryption work correctly."""
        manager = EncryptionManager()
        original_text = "This is sensitive data that needs encryption"
        
        # Encrypt the data
        encrypted = manager.encrypt(original_text)
        
        # Verify it's different from original
        assert encrypted != original_text
        assert len(encrypted) > len(original_text)  # Base64 encoding adds overhead
        
        # Decrypt the data
        decrypted = manager.decrypt(encrypted)
        
        # Verify round-trip successful
        assert decrypted == original_text
    
    def test_empty_string_handling(self):
        """Test handling of empty strings."""
        manager = EncryptionManager()
        
        # Empty string should return empty string
        assert manager.encrypt("") == ""
        assert manager.decrypt("") == ""
        
        # None should be handled gracefully by convenience functions
        assert encrypt_sensitive_field(None) is None
        assert decrypt_sensitive_field(None) is None
    
    def test_encrypt_decrypt_dict(self):
        """Test dictionary field encryption/decryption."""
        manager = EncryptionManager()
        
        test_data = {
            "username": "testuser",
            "password": "secret123",
            "email": "user@example.com",
            "public_data": "not sensitive"
        }
        
        fields_to_encrypt = ["password", "email"]
        
        # Encrypt specified fields
        encrypted_data = manager.encrypt_dict(test_data, fields_to_encrypt)
        
        # Check that specified fields are encrypted
        assert encrypted_data["password"] != "secret123"
        assert encrypted_data["email"] != "user@example.com"
        # Check that other fields are unchanged
        assert encrypted_data["username"] == "testuser"
        assert encrypted_data["public_data"] == "not sensitive"
        
        # Decrypt specified fields
        decrypted_data = manager.decrypt_dict(encrypted_data, fields_to_encrypt)
        
        # Verify round-trip successful
        assert decrypted_data == test_data
    
    def test_encryption_produces_base64(self):
        """Test that encrypted data is valid base64."""
        manager = EncryptionManager()
        encrypted = manager.encrypt("test data")
        
        # Should be valid base64
        try:
            decoded = base64.b64decode(encrypted.encode('utf-8'))
            assert len(decoded) >= 13  # At least nonce (12) + some ciphertext
        except Exception:
            pytest.fail("Encrypted data is not valid base64")
    
    def test_is_encrypted_function(self):
        """Test the is_encrypted utility function."""
        manager = EncryptionManager()
        
        plaintext = "not encrypted"
        encrypted = manager.encrypt("some data")
        
        assert not is_encrypted(plaintext)
        assert is_encrypted(encrypted)
        assert not is_encrypted("")
        assert not is_encrypted("invalid base64!")


class TestSensitiveDataMasking:
    """Test sensitive data masking functionality."""
    
    def test_mask_string_with_patterns(self):
        """Test masking of strings with sensitive patterns."""
        test_data = 'User login with {"password": "secret123", "token": "abc123xyz"}'
        
        masked = mask_sensitive_data(test_data)
        
        assert "secret123" not in masked
        assert "abc123xyz" not in masked
        assert "***" in masked
    
    def test_mask_dictionary(self):
        """Test masking of dictionary with sensitive keys."""
        test_data = {
            "username": "testuser",
            "password": "secret123",
            "api_key": "key123",
            "public_info": "not sensitive",
            "nested": {
                "secret": "hidden",
                "normal": "visible"
            }
        }
        
        masked = mask_sensitive_data(test_data)
        
        # Sensitive fields should be masked
        assert masked["password"] == "***"
        assert masked["api_key"] == "***"
        assert masked["nested"]["secret"] == "***"
        
        # Non-sensitive fields should remain
        assert masked["username"] == "testuser"
        assert masked["public_info"] == "not sensitive"
        assert masked["nested"]["normal"] == "visible"
    
    def test_mask_list_and_tuple(self):
        """Test masking of lists and tuples."""
        test_list = ["normal", {"password": "secret"}, "other"]
        test_tuple = ("normal", {"token": "secret"}, "other")
        
        masked_list = mask_sensitive_data(test_list)
        masked_tuple = mask_sensitive_data(test_tuple)
        
        assert masked_list[0] == "normal"
        assert masked_list[1]["password"] == "***"
        assert masked_list[2] == "other"
        
        assert masked_tuple[0] == "normal"
        assert masked_tuple[1]["token"] == "***"
        assert masked_tuple[2] == "other"
    
    def test_sensitive_data_processor(self):
        """Test the SensitiveDataMaskingProcessor."""
        processor = SensitiveDataMaskingProcessor()
        
        event_dict = {
            "message": "User authentication",
            "password": "secret123",
            "user_data": {
                "api_key": "key123",
                "name": "John Doe"
            }
        }
        
        processed = processor(None, None, event_dict)
        
        assert processed["password"] == "***"
        assert processed["user_data"]["api_key"] == "***"
        assert processed["user_data"]["name"] == "John Doe"
        assert processed["message"] == "User authentication"


class TestFieldDetection:
    """Test sensitive field detection."""
    
    def test_should_encrypt_field(self):
        """Test field name detection for encryption."""
        # Should encrypt
        assert should_encrypt_field("password")
        assert should_encrypt_field("user_password")
        assert should_encrypt_field("API_KEY")
        assert should_encrypt_field("secret_token")
        assert should_encrypt_field("email")
        
        # Should not encrypt
        assert not should_encrypt_field("username")
        assert not should_encrypt_field("public_data")
        assert not should_encrypt_field("id")
        assert not should_encrypt_field("created_at")
    
    def test_sensitive_fields_coverage(self):
        """Test that all important sensitive field types are covered."""
        required_patterns = [
            'password', 'api_token', 'api_key', 'secret', 
            'private_key', 'email', 'phone', 'ssn', 'credit_card'
        ]
        
        for pattern in required_patterns:
            assert pattern in SENSITIVE_FIELDS, f"Missing sensitive field pattern: {pattern}"


class TestComplianceValidation:
    """Test encryption compliance validation."""
    
    @pytest.mark.asyncio
    async def test_encryption_status_endpoint(self):
        """Test the encryption status endpoint."""
        # This would require a full FastAPI test client
        # For now, we'll test the underlying functionality
        from app.core.encryption import encryption_manager
        
        # Test that encryption manager can encrypt/decrypt
        test_data = "compliance_test_data"
        encrypted = encryption_manager.encrypt(test_data)
        decrypted = encryption_manager.decrypt(encrypted)
        
        assert encrypted != test_data
        assert decrypted == test_data
    
    def test_encryption_algorithm_configuration(self):
        """Test that encryption uses the configured algorithm."""
        from app.core.config import settings
        
        # Should be using AES-256-GCM
        assert settings.ENCRYPTION_ALGORITHM == "AES-256-GCM"
    
    def test_key_derivation_parameters(self):
        """Test key derivation parameters for security."""
        from app.core.config import settings
        
        # Should use sufficient iterations for PBKDF2
        assert settings.KEY_DERIVATION_ITERATIONS >= 100000


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    return MagicMock(
        ENCRYPTION_KEY="test_key_for_encryption_testing_32bytes",
        ENCRYPTION_ALGORITHM="AES-256-GCM",
        KEY_DERIVATION_ITERATIONS=100000,
        TLS_ENABLED=True,
        DB_ENCRYPTION_ENABLED=True,
        ENABLE_AUDIT_LOGGING=True
    )


class TestErrorHandling:
    """Test encryption error handling."""
    
    def test_invalid_encrypted_data(self):
        """Test handling of invalid encrypted data."""
        manager = EncryptionManager()
        
        with pytest.raises(ValueError):
            manager.decrypt("invalid_encrypted_data")
        
        with pytest.raises(ValueError):
            manager.decrypt("not_base64!")
    
    def test_encryption_with_invalid_key(self):
        """Test behavior with invalid encryption key."""
        # This would require mocking the key derivation
        # The actual implementation should handle key errors gracefully
        pass


if __name__ == "__main__":
    pytest.main([__file__])