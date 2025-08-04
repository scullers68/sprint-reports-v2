"""
Sprint Reports v2 - FastAPI Application Entry Point

Modern, scalable sprint management application built with FastAPI.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from datetime import datetime

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import create_db_and_tables, get_db
from app.core.middleware import add_custom_middleware
from app.core.exceptions import (
    sprint_reports_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
    SprintReportsException
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    # await create_db_and_tables()  # Database initialization temporarily disabled for testing
    
    # Start background tasks service
    from app.services.background_tasks import background_service
    await background_service.start()
    
    yield
    
    # Shutdown
    # Stop background tasks service
    await background_service.stop()


# Security scheme for OpenAPI
security = HTTPBearer()

app = FastAPI(
    title="Sprint Reports API",
    description="""
    Modern sprint management and analytics platform for agile teams.
    
    ## Features
    * Sprint planning and management
    * JIRA integration and synchronization
    * Team capacity management
    * Advanced reporting and analytics
    * Real-time collaboration
    
    ## Authentication
    This API uses Bearer token authentication. Include your token in the Authorization header:
    ```
    Authorization: Bearer <your-token>
    ```
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "authentication",
            "description": "User authentication and authorization endpoints"
        },
        {
            "name": "users",
            "description": "User management operations"
        },
        {
            "name": "sprints",
            "description": "Sprint planning and management"
        },
        {
            "name": "queues",
            "description": "Sprint queue generation and management"
        },
        {
            "name": "capacity",
            "description": "Team capacity planning and allocation"
        },
        {
            "name": "reports",
            "description": "Analytics and reporting functionality"
        },
        {
            "name": "webhooks",
            "description": "JIRA webhook integration and real-time event processing"
        },
        {
            "name": "health",
            "description": "System health and monitoring endpoints"
        }
    ]
)

# Add custom middleware
add_custom_middleware(app)

# Add exception handlers
app.add_exception_handler(SprintReportsException, sprint_reports_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=settings.ALLOWED_HOSTS
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Sprint Reports API v2",
        "version": "2.0.0",
        "docs": "/docs",
        "status": "operational"
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Basic health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "sprint-reports-api"
    }


@app.get("/health/ready", tags=["health"])
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness check endpoint with database connectivity validation.
    
    This endpoint verifies that the application is ready to serve requests
    by checking database connectivity and other critical dependencies.
    """
    health_status = {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "sprint-reports-api",
        "checks": {}
    }
    
    # Database connectivity check
    try:
        # Simple query to test database connection
        from sqlalchemy import text
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
    
    # Configuration check
    try:
        # Verify critical configuration is present
        if settings.SECRET_KEY and settings.DATABASE_URL:
            health_status["checks"]["configuration"] = {
                "status": "healthy",
                "message": "Configuration is valid"
            }
        else:
            health_status["status"] = "unhealthy"
            health_status["checks"]["configuration"] = {
                "status": "unhealthy",
                "message": "Missing critical configuration"
            }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["configuration"] = {
            "status": "unhealthy",
            "message": f"Configuration error: {str(e)}"
        }
    
    # Webhook configuration check
    try:
        if hasattr(settings, 'JIRA_WEBHOOK_SECRET') and settings.JIRA_WEBHOOK_SECRET:
            health_status["checks"]["webhook_config"] = {
                "status": "healthy",
                "message": "Webhook configuration is present"
            }
        else:
            health_status["checks"]["webhook_config"] = {
                "status": "warning",
                "message": "Webhook secret not configured"
            }
    except Exception as e:
        health_status["checks"]["webhook_config"] = {
            "status": "unhealthy", 
            "message": f"Webhook configuration error: {str(e)}"
        }
    
    # Redis connectivity check for webhook processing
    try:
        import redis.asyncio as redis
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        await redis_client.close()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful"
        }
    except Exception as e:
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }
    
    # Return appropriate HTTP status code
    if health_status["status"] == "unhealthy":
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status
        )
    
    return health_status


@app.get("/health/live", tags=["health"])
async def liveness_check():
    """
    Liveness check endpoint for container orchestration.
    
    This endpoint indicates whether the application process is alive
    and not deadlocked or hanging.
    """
    return {
        "status": "alive",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "sprint-reports-api"
    }


if __name__ == "__main__":
    import uvicorn
    import ssl
    
    # Configure SSL context for TLS
    ssl_context = None
    if settings.TLS_ENABLED:
        try:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(settings.TLS_CERT_PATH, settings.TLS_KEY_PATH)
            ssl_context.minimum_version = ssl.TLSVersion.TLSv1_3
            ssl_context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
            print(f"TLS enabled with certificates from {settings.TLS_CERT_PATH}")
        except Exception as e:
            print(f"Warning: TLS configuration failed: {e}")
            print("Running in HTTP mode")
            ssl_context = None
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        ssl_certfile=settings.TLS_CERT_PATH if settings.TLS_ENABLED and ssl_context else None,
        ssl_keyfile=settings.TLS_KEY_PATH if settings.TLS_ENABLED and ssl_context else None,
        ssl_version=ssl.PROTOCOL_TLS_SERVER if ssl_context else None
    )