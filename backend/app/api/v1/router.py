"""
Main API router that combines all endpoint routers.

Provides centralized routing for all API v1 endpoints.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, sprints, queues, reports, capacity, users, security, admin, webhooks, field_mappings, audit, jira

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(sprints.router, prefix="/sprints", tags=["sprints"])
api_router.include_router(queues.router, prefix="/queues", tags=["queues"])
api_router.include_router(capacity.router, prefix="/capacity", tags=["capacity"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(security.router, prefix="/security", tags=["security"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(admin.router, prefix="/admin", tags=["administration"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(field_mappings.router, prefix="/field-mappings", tags=["field-mappings"])
api_router.include_router(jira.router, prefix="/jira", tags=["jira"])