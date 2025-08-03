"""
Application configuration using Pydantic Settings.

Provides type-safe configuration management with environment variable support.
"""

from typing import List, Optional

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    PROJECT_NAME: str = "Sprint Reports v2"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Core Security (Required)
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Data Encryption (Simplified - Optional for development)
    ENCRYPTION_KEY: str = Field(default="dev-encryption-key-change-in-production", env="ENCRYPTION_KEY")
    ENCRYPTION_ALGORITHM: str = "AES-256-GCM"
    KEY_DERIVATION_ITERATIONS: int = 100000
    
    # TLS Configuration (Optional for development)
    TLS_ENABLED: bool = Field(False, env="TLS_ENABLED")
    TLS_CERT_PATH: str = Field("/etc/ssl/certs/app.crt", env="TLS_CERT_PATH")
    TLS_KEY_PATH: str = Field("/etc/ssl/private/app.key", env="TLS_KEY_PATH")
    TLS_MIN_VERSION: str = "TLSv1.3"
    
    # Database Encryption (Optional for development)
    DB_ENCRYPTION_ENABLED: bool = Field(False, env="DB_ENCRYPTION_ENABLED")
    DB_SSL_MODE: str = Field("prefer", env="DB_SSL_MODE")
    DB_SSL_CERT_PATH: Optional[str] = Field(None, env="DB_SSL_CERT_PATH")
    DB_SSL_KEY_PATH: Optional[str] = Field(None, env="DB_SSL_KEY_PATH")
    DB_SSL_ROOT_CERT_PATH: Optional[str] = Field(None, env="DB_SSL_ROOT_CERT_PATH")
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # React dev server
        "http://localhost:3001",
        "http://localhost:3002",  # Additional frontend port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
    ]
    
    # Database
    POSTGRES_SERVER: str = Field(..., env="POSTGRES_SERVER")
    POSTGRES_USER: str = Field(..., env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(..., env="POSTGRES_DB")
    POSTGRES_PORT: int = Field(5432, env="POSTGRES_PORT")
    DATABASE_URL: Optional[PostgresDsn] = None
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info) -> str:
        """Build database URL from components."""
        if isinstance(v, str):
            return v
        values = info.data
        return str(PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            port=values.get("POSTGRES_PORT"),
            path=f"{values.get('POSTGRES_DB') or ''}",
        ))
    
    # Redis
    REDIS_URL: str = Field("redis://localhost:6379", env="REDIS_URL")
    
    # JIRA Integration (Optional for basic functionality)
    JIRA_URL: Optional[str] = Field(None, env="JIRA_URL")
    JIRA_EMAIL: Optional[str] = Field(None, env="JIRA_EMAIL") 
    JIRA_API_TOKEN: Optional[str] = Field(None, env="JIRA_API_TOKEN")
    
    # JIRA Webhook Configuration (Optional)
    JIRA_WEBHOOK_SECRET: Optional[str] = Field(None, env="JIRA_WEBHOOK_SECRET")
    JIRA_WEBHOOK_USER_AGENT: str = Field("Atlassian HttpClient", env="JIRA_WEBHOOK_USER_AGENT")
    WEBHOOK_MAX_BODY_SIZE: int = Field(10485760, env="WEBHOOK_MAX_BODY_SIZE")  # 10MB max payload
    
    # Confluence Integration (Optional)
    CONFLUENCE_URL: Optional[str] = Field(None, env="CONFLUENCE_URL")
    
    # Celery (Background Tasks)
    CELERY_BROKER_URL: str = Field("redis://localhost:6379/0", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field("redis://localhost:6379/0", env="CELERY_RESULT_BACKEND")
    
    # Logging
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    
    # Feature Flags
    ENABLE_REAL_TIME_UPDATES: bool = Field(True, env="ENABLE_REAL_TIME_UPDATES")
    ENABLE_ML_INSIGHTS: bool = Field(False, env="ENABLE_ML_INSIGHTS")
    ENABLE_AUDIT_LOGGING: bool = Field(True, env="ENABLE_AUDIT_LOGGING")
    
    # SSO Configuration (Completely Optional)
    SSO_ENABLED: bool = Field(False, env="SSO_ENABLED")
    SSO_AUTO_PROVISION_USERS: bool = Field(True, env="SSO_AUTO_PROVISION_USERS")
    SSO_DEFAULT_ROLE: str = Field("user", env="SSO_DEFAULT_ROLE")
    SSO_ALLOWED_DOMAINS: List[str] = Field(default=[], env="SSO_ALLOWED_DOMAINS")
    
    # Google OAuth 2.0 Configuration (Optional)
    GOOGLE_CLIENT_ID: Optional[str] = Field(None, env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(None, env="GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: Optional[str] = Field(None, env="GOOGLE_REDIRECT_URI")
    GOOGLE_DISCOVERY_URL: str = Field(
        "https://accounts.google.com/.well-known/openid_configuration",
        env="GOOGLE_DISCOVERY_URL"
    )
    
    # Microsoft Azure AD Configuration
    AZURE_CLIENT_ID: Optional[str] = Field(None, env="AZURE_CLIENT_ID")
    AZURE_CLIENT_SECRET: Optional[str] = Field(None, env="AZURE_CLIENT_SECRET")
    AZURE_TENANT_ID: Optional[str] = Field(None, env="AZURE_TENANT_ID")
    AZURE_REDIRECT_URI: Optional[str] = Field(None, env="AZURE_REDIRECT_URI")
    AZURE_AUTHORITY: Optional[str] = Field(None, env="AZURE_AUTHORITY")
    
    @field_validator("AZURE_AUTHORITY", mode="before")
    @classmethod
    def build_azure_authority(cls, v: Optional[str], info) -> Optional[str]:
        """Build Azure authority URL from tenant ID if not provided."""
        if v:
            return v
        values = info.data
        tenant_id = values.get("AZURE_TENANT_ID")
        if tenant_id:
            return f"https://login.microsoftonline.com/{tenant_id}"
        return None
    
    # Generic OAuth 2.0 Configuration (for backward compatibility)
    OAUTH_CLIENT_ID: Optional[str] = Field(None, env="OAUTH_CLIENT_ID")
    OAUTH_CLIENT_SECRET: Optional[str] = Field(None, env="OAUTH_CLIENT_SECRET")
    OAUTH_REDIRECT_URI: Optional[str] = Field(None, env="OAUTH_REDIRECT_URI")
    OAUTH_AUTHORIZATION_URL: Optional[str] = Field(None, env="OAUTH_AUTHORIZATION_URL")
    OAUTH_TOKEN_URL: Optional[str] = Field(None, env="OAUTH_TOKEN_URL")
    OAUTH_USERINFO_URL: Optional[str] = Field(None, env="OAUTH_USERINFO_URL")
    OAUTH_SCOPE: str = Field("openid email profile", env="OAUTH_SCOPE")
    
    # SAML Configuration
    SAML_IDP_ENTITY_ID: Optional[str] = Field(None, env="SAML_IDP_ENTITY_ID")
    SAML_IDP_SSO_URL: Optional[str] = Field(None, env="SAML_IDP_SSO_URL")
    SAML_IDP_X509_CERT: Optional[str] = Field(None, env="SAML_IDP_X509_CERT")
    SAML_SP_ENTITY_ID: Optional[str] = Field(None, env="SAML_SP_ENTITY_ID")
    SAML_SP_X509_CERT: Optional[str] = Field(None, env="SAML_SP_X509_CERT")
    SAML_SP_PRIVATE_KEY: Optional[str] = Field(None, env="SAML_SP_PRIVATE_KEY")
    SAML_METADATA_URL: Optional[str] = Field(None, env="SAML_METADATA_URL")
    
    # Audit Logging Configuration
    AUDIT_LOG_RETENTION_YEARS: int = Field(7, env="AUDIT_LOG_RETENTION_YEARS")  # 7 years for compliance
    AUDIT_CHAIN_VERIFICATION: bool = Field(True, env="AUDIT_CHAIN_VERIFICATION")
    AUDIT_COMPLIANCE_FRAMEWORKS: List[str] = Field(
        default=["GDPR", "SOC2", "ISO27001"], 
        env="AUDIT_COMPLIANCE_FRAMEWORKS"
    )
    AUDIT_SUSPICIOUS_USER_AGENTS: List[str] = Field(
        default=["curl", "wget", "python-requests", "bot", "crawler", "scanner"],
        env="AUDIT_SUSPICIOUS_USER_AGENTS"
    )
    AUDIT_SENSITIVE_PATHS: List[str] = Field(
        default=["/api/v1/auth/", "/api/v1/admin/", "/api/v1/users/"],
        env="AUDIT_SENSITIVE_PATHS"
    )
    AUDIT_MAX_METADATA_SIZE: int = Field(10240, env="AUDIT_MAX_METADATA_SIZE")  # 10KB max metadata
    
    # Performance
    MAX_CONNECTIONS_PER_POOL: int = 20
    MAX_OVERFLOW_CONNECTIONS: int = 0
    POOL_PRE_PING: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()