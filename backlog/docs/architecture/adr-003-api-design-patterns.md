# ADR-003: API Design Patterns and Contracts

## Status
Accepted

## Context
The application needs comprehensive API contracts that build upon the existing FastAPI router structure in `/backend/app/api/v1/`. The current endpoint organization shows good separation by domain (auth, sprints, queues, reports, capacity, users).

## Decision
We will extend the existing FastAPI router architecture with OpenAPI 3.0 specifications, building upon the current endpoint structure.

### API Architecture:
1. **Versioned APIs**: Extend existing `/api/v1/` pattern in `/backend/app/api/v1/router.py`
2. **Domain-Based Routing**: Build upon existing endpoint separation (auth, sprints, queues, reports, capacity, users)
3. **OpenAPI Documentation**: Enhance existing FastAPI docs with comprehensive schemas
4. **Pydantic Schemas**: Extend existing schema patterns for request/response validation

### API Contract Extensions:
- **Authentication**: Build on existing `/auth` endpoints with OAuth 2.0 and SAML
- **Sprint Management**: Extend existing `/sprints` endpoints with advanced features
- **Queue Generation**: Enhance existing `/queues` endpoints with ML-powered algorithms
- **Reporting**: Extend existing `/reports` endpoints with real-time analytics
- **Capacity Management**: Build on existing `/capacity` endpoints with predictive features
- **User Management**: Extend existing `/users` endpoints with role-based access

### Service Integration Patterns:
- **JIRA Service**: Extend existing `JiraService` class patterns
- **Service Layer**: Build upon existing service architecture in `/backend/app/services/`
- **Error Handling**: Enhance existing FastAPI error handling patterns
- **Authentication**: Extend existing security patterns

## Consequences

### Positive:
- Leverages existing FastAPI infrastructure and router patterns
- Maintains consistency with current endpoint organization
- Strong typing with Pydantic schemas
- Automatic OpenAPI documentation generation

### Negative:
- API versioning complexity across services
- Breaking change management
- Cross-service contract synchronization

## Implementation Notes
- Extend existing router structure in `/backend/app/api/v1/endpoints/`
- Build upon existing service patterns in `/backend/app/services/`
- Enhance existing schema patterns for comprehensive validation
- Maintain current authentication and security patterns
- Use existing configuration patterns for service endpoints

## API Contract Examples

### Sprint Management Service
```python
# Extends existing /backend/app/api/v1/endpoints/sprints.py
POST /api/v1/sprints/{sprint_id}/analyze
GET /api/v1/sprints/{sprint_id}/capacity
```

### Queue Generation Service  
```python
# Extends existing /backend/app/api/v1/endpoints/queues.py
POST /api/v1/queues/generate
GET /api/v1/queues/{queue_id}/conflicts
```

## References
- PRD Section: Technical Requirements - API-First Design
- Existing API structure: `/backend/app/api/v1/router.py`
- Current endpoints: `/backend/app/api/v1/endpoints/` directory
- Service patterns: `/backend/app/services/` directory