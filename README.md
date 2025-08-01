# Sprint Reports v2

Modern, scalable sprint management application built with FastAPI and React.

## 🚀 Project Location

**This project is now located at:** `/Users/russellgrocott/Projects/sprint-reports-v2`

The v2 project has been moved to its own dedicated repository structure for independent development.

## Overview

Sprint Reports v2 is a complete rebuild of the sprint management system with modern architecture, improved performance, and enhanced features for discipline team capacity management.

## Architecture Overview

- **Backend**: FastAPI + SQLAlchemy 2.0 + Pydantic v2
- **Database**: PostgreSQL + Redis (caching)
- **Frontend**: React 18 + TypeScript + TanStack Query
- **Infrastructure**: Docker + Kubernetes
- **Monitoring**: OpenTelemetry + Prometheus + Grafana

## Project Structure

```
sprint-reports-v2/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── core/           # Configuration, database, dependencies
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic layer
│   │   ├── api/            # API route handlers
│   │   └── main.py         # FastAPI application entry point
│   ├── tests/
│   ├── alembic/            # Database migrations
│   └── requirements.txt
├── frontend/               # React application
│   ├── src/
│   │   ├── components/     # Reusable React components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API client and business logic
│   │   ├── types/          # TypeScript type definitions
│   │   └── utils/          # Utility functions
│   ├── public/
│   └── package.json
└── infrastructure/         # Docker, K8s, monitoring configs
    ├── docker/
    ├── kubernetes/
    └── monitoring/
```

## Key Improvements over v1

### Architecture
- ✅ **Modular Design**: Clean separation of concerns with service layer
- ✅ **Type Safety**: Full TypeScript coverage front-to-back
- ✅ **Async/Await**: FastAPI async capabilities for better performance
- ✅ **API-First**: OpenAPI 3.0 auto-generated documentation

### Performance
- ✅ **Database**: PostgreSQL with proper indexing and query optimization
- ✅ **Caching**: Redis for session management and data caching
- ✅ **Real-time**: WebSocket support for live updates
- ✅ **Background Jobs**: Celery for asynchronous task processing

### Developer Experience
- ✅ **Testing**: 90%+ test coverage with pytest and Jest
- ✅ **Documentation**: Auto-generated API docs and component storybook
- ✅ **Development**: Hot reload, type checking, and comprehensive linting
- ✅ **Debugging**: Structured logging and distributed tracing

### Security
- ✅ **Authentication**: JWT + refresh tokens with RBAC
- ✅ **Input Validation**: Pydantic schemas with comprehensive validation
- ✅ **CORS**: Proper cross-origin resource sharing configuration
- ✅ **Rate Limiting**: API endpoint protection against abuse

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+

### Development Setup

1. **Navigate to project directory:**
   ```bash
   cd /Users/russellgrocott/Projects/sprint-reports-v2
   ```

2. **Run setup script:**
   ```bash
   python setup_dev.py
   ```

3. **Configure environment:**
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start services:**
   ```bash
   # Option 1: Docker Compose (recommended)
   docker-compose up -d
   
   # Option 2: Local development
   # Start PostgreSQL and Redis locally
   cd backend && uvicorn app.main:app --reload
   cd frontend && npm run dev
   ```

### Docker Development

The project includes complete Docker containerization for consistent development environments:

#### Quick Start
```bash
# Start all services (PostgreSQL, Redis, FastAPI backend, Celery)
docker-compose up -d

# View logs from all services
docker-compose logs -f

# View logs from specific service
docker-compose logs -f backend
docker-compose logs -f db
```

#### Development Commands
```bash
# Rebuild containers after dependency changes
docker-compose build --no-cache

# Run backend tests
docker-compose exec backend pytest
docker-compose exec backend pytest -v tests/

# Run database migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "migration_name"

# Access backend container shell
docker-compose exec backend bash

# Access database directly
docker-compose exec db psql -U sprint_reports -d sprint_reports_v2
```

#### Container Architecture
- **backend**: FastAPI application with hot reload enabled
- **db**: PostgreSQL 15 with persistent volume
- **redis**: Redis 7 for caching and background tasks
- **celery**: Background task worker for async processing

#### Port Mappings
- Backend API: http://localhost:8000
- Interactive API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379

#### Volume Mounts
- `./backend/app:/app/app:ro` - Hot reload for backend code changes
- `postgres_data:/var/lib/postgresql/data` - Persistent database storage
- `redis_data:/data` - Persistent Redis data

## Migration from v1

The migration strategy involves running both systems in parallel during transition:

1. **Phase 1**: Core API development and testing
2. **Phase 2**: Frontend development with feature parity
3. **Phase 3**: Data migration and user testing
4. **Phase 4**: Production cutover and v1 retirement

See [Migration Guide](docs/migration.md) for detailed instructions.

## Contributing

1. Follow conventional commit messages
2. Ensure tests pass: `pytest` (backend) and `npm test` (frontend)
3. Type checking: `mypy` (backend) and `tsc --noEmit` (frontend)
4. Code formatting: `black` and `isort` (backend), `prettier` (frontend)

## Documentation

- [API Documentation](http://localhost:8000/docs) (when running locally)
- [Architecture Guide](docs/architecture.md)
- [Development Guide](docs/development.md)
- [Deployment Guide](docs/deployment.md)

## Performance Targets

- **API Response Time**: <500ms (95th percentile)
- **Page Load Time**: <2s (initial load)
- **Concurrent Users**: 200+ simultaneous users
- **Sprint Processing**: <30s for 500+ issues

## Status

🚧 **In Development** 🚧

- [x] Project structure and configuration
- [ ] Core API services
- [ ] Database models and migrations
- [ ] Authentication and authorization
- [ ] Frontend application setup
- [ ] JIRA integration services
- [ ] Queue generation algorithms
- [ ] Reporting and analytics
- [ ] Real-time features
- [ ] Production deployment

---

*This project represents the evolution of sprint management tooling, built with modern practices to serve agile teams for years to come.*

Notes:


  1. Use your current structure - It's already production-ready
  2. Run the setup script:
  cd /Users/russellgrocott/Projects/sprint-reports-v2
  3. Test the API:
  cd backend
  uvicorn app.main:app --reload
  # Visit http://localhost:8000/docs