# Sprint Reports v2 - Developer Onboarding Guide

Welcome to the Sprint Reports v2 development team! This guide will help you get up and running with the development environment quickly and efficiently.

## 🎯 Quick Start (5 Minutes)

### Prerequisites Check
Before starting, ensure you have:
- [ ] **Docker Desktop** installed and running
- [ ] **Git** configured with your credentials
- [ ] **Code editor** (VS Code recommended)
- [ ] Access to the project repository

### Immediate Setup
```bash
# 1. Clone and navigate to project
git clone <repository-url>
cd sprint-reports-v2

# 2. Start development environment
./docker-compose-local.sh start

# 3. Verify setup
curl http://localhost:3001/docs
```

That's it! Your development environment is ready. 🎉

## 📋 Detailed Onboarding Checklist

### Phase 1: Environment Setup
- [ ] Install Docker Desktop and verify it's running
- [ ] Clone the repository to your local machine
- [ ] Review the project structure (see [Architecture Overview](#architecture-overview))
- [ ] Run the automated development environment setup
- [ ] Access the API documentation at http://localhost:3001/docs
- [ ] Verify database connection and run initial migrations

### Phase 2: Development Workflow
- [ ] Create a feature branch: `git checkout -b feature/your-feature-name`
- [ ] Configure your IDE (see [IDE Setup](#ide-setup))
- [ ] Run the test suite to ensure everything works
- [ ] Make a small test change and verify hot reload works
- [ ] Review the [Development Standards](#development-standards)

### Phase 3: Integration
- [ ] Join the team Slack channels
- [ ] Set up JIRA access (if working on integrations)
- [ ] Review the [API Documentation](#api-documentation)
- [ ] Complete your first task (usually a small bug fix or documentation update)
- [ ] Submit your first pull request

## 🏗️ Architecture Overview

Sprint Reports v2 follows a modern, containerized microservices architecture:

### Technology Stack
- **Backend**: FastAPI + SQLAlchemy 2.0 + Pydantic v2
- **Database**: PostgreSQL 15 + Redis 7
- **Frontend**: React 18 + TypeScript (coming soon)
- **Infrastructure**: Docker + Docker Compose
- **Testing**: pytest + Jest
- **Monitoring**: OpenTelemetry + structured logging

### Project Structure
```
sprint-reports-v2/
├── backend/                     # FastAPI backend application
│   ├── app/
│   │   ├── core/               # Configuration, database, dependencies
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # Business logic layer
│   │   ├── api/                # REST API endpoints
│   │   └── main.py             # Application entry point
│   ├── tests/                  # Backend test suite
│   ├── alembic/                # Database migrations
│   ├── Dockerfile              # Production container
│   ├── docker-compose.yml      # Standard development environment
│   ├── docker-compose.local.yml # Isolated local development
│   └── requirements.txt        # Python dependencies
├── frontend/                   # React frontend (in development)
├── infrastructure/             # Deployment configurations
├── backlog/                    # Project management and documentation
└── docker-compose-local.sh    # Development environment manager
```

### Core Services
1. **Backend API** (Port 3001): FastAPI application with auto-generated docs
2. **PostgreSQL** (Port 5433): Primary database with persistent storage
3. **Redis** (Port 6380): Caching and background task queue
4. **Celery Worker**: Async background task processing

## 🛠️ Development Environment

### Available Development Environments

#### 1. Isolated Local Environment (Recommended)
```bash
# Start isolated environment (different ports to avoid conflicts)
./docker-compose-local.sh start

# Access services:
# - API: http://localhost:3001/docs
# - Database: localhost:5433
# - Redis: localhost:6380
```

#### 2. Standard Environment
```bash
# Standard Docker Compose (may conflict with other projects)
cd backend
docker-compose up -d

# Access services:
# - API: http://localhost:8000/docs
# - Database: localhost:5432
# - Redis: localhost:6379
```

#### 3. Development Tools (Optional)
```bash
# Start with additional GUI tools
./docker-compose-local.sh start --tools

# Additional tools available:
# - pgAdmin: http://localhost:8080 (PostgreSQL GUI)
# - Redis Commander: http://localhost:8081 (Redis GUI)
```

### Development Workflow Scripts

The `docker-compose-local.sh` script provides convenient commands:

```bash
# Environment management
./docker-compose-local.sh start          # Start all services
./docker-compose-local.sh stop           # Stop all services
./docker-compose-local.sh restart        # Restart all services
./docker-compose-local.sh status         # Show service status

# Development tasks
./docker-compose-local.sh test           # Run backend tests
./docker-compose-local.sh logs [service] # View logs
./docker-compose-local.sh shell [service] # Access container shell

# Database operations
./docker-compose-local.sh shell app      # Access backend container
# Then run: alembic upgrade head          # Apply migrations
# Or: alembic revision --autogenerate -m "description" # Create migration

# Cleanup
./docker-compose-local.sh clean          # Stop and remove all data
```

## 🔧 IDE Setup

### VS Code (Recommended)
Install these extensions for the best development experience:

#### Essential Extensions
- **Python** - Python language support
- **Pylance** - Advanced Python language server
- **Docker** - Docker container management
- **Thunder Client** - API testing (alternative to Postman)

#### Optional Extensions
- **GitLens** - Enhanced Git capabilities
- **Auto Docstring** - Automatic Python docstring generation
- **Python Test Explorer** - Visual test runner
- **REST Client** - HTTP request testing

### VS Code Settings
Create `.vscode/settings.json` in your project root:
```json
{
    "python.defaultInterpreterPath": "./backend/venv/bin/python",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "files.exclude": {
        "**/__pycache__": true,
        "**/.pytest_cache": true
    }
}
```

## 📚 Development Standards

### Code Quality
- **Type Hints**: All Python code must include type hints
- **Documentation**: Use docstrings for all functions and classes
- **Testing**: Maintain 80%+ test coverage
- **Formatting**: Code is automatically formatted with Black and isort

### Git Workflow
```bash
# Feature branch naming
git checkout -b feature/JIRA-123-add-user-authentication
git checkout -b bugfix/fix-database-connection-pool
git checkout -b docs/update-api-documentation

# Commit message format
git commit -m "feat(auth): add JWT token validation middleware

- Implement token validation decorator
- Add refresh token rotation
- Update API documentation
- Add comprehensive test coverage

Closes JIRA-123"
```

### API Development
- All endpoints must have Pydantic request/response schemas
- Include comprehensive OpenAPI documentation
- Add request validation and error handling
- Write integration tests for all endpoints

### Database Changes
```bash
# Create new migration
docker-compose -f backend/docker-compose.local.yml exec app alembic revision --autogenerate -m "add user table"

# Apply migrations
docker-compose -f backend/docker-compose.local.yml exec app alembic upgrade head

# Downgrade (if needed)
docker-compose -f backend/docker-compose.local.yml exec app alembic downgrade -1
```

## 🧪 Testing

### Backend Testing
```bash
# Run all tests
./docker-compose-local.sh test

# Run specific test file
./docker-compose-local.sh shell app
pytest tests/test_users.py -v

# Run with coverage
pytest --cov=app tests/

# Run integration tests only
pytest tests/integration/ -v
```

### Test Structure
```
backend/tests/
├── unit/                       # Unit tests
│   ├── test_models.py         # Model tests
│   ├── test_services.py       # Service layer tests
│   └── test_utils.py          # Utility function tests
├── integration/               # Integration tests
│   ├── test_api_endpoints.py  # API endpoint tests
│   └── test_database.py       # Database integration tests
└── conftest.py                # Pytest configuration and fixtures
```

## 📖 API Documentation

### Interactive Documentation
- **Swagger UI**: http://localhost:3001/docs
- **ReDoc**: http://localhost:3001/redoc
- **OpenAPI JSON**: http://localhost:3001/openapi.json

### API Testing
Use Thunder Client (VS Code) or curl to test endpoints:

```bash
# Health check
curl http://localhost:3001/health

# Get API version
curl http://localhost:3001/api/v1/version

# Test authentication (example)
curl -X POST http://localhost:3001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}'
```

## 🚀 Deployment

### Local Development → UAT → Production
The deployment follows a standard three-tier approach:

1. **Local Development**: Your local Docker environment
2. **UAT**: Staging environment on Synology NAS
3. **Production**: Production environment on Synology NAS

### Environment Configuration
Each environment has its own `.env` file:
- `.env.local` - Local development
- `.env.uat` - UAT environment
- `.env.production` - Production environment

## 🆘 Troubleshooting

### Common Issues

#### Docker Desktop Not Running
```bash
# Error: Cannot connect to the Docker daemon
# Solution: Start Docker Desktop application
```

#### Port Conflicts
```bash
# Error: Port 3001 already in use
# Solution: Stop other services or use different ports
./docker-compose-local.sh stop
lsof -ti:3001 | xargs kill -9  # Kill process using port 3001
```

#### Database Connection Issues
```bash
# Error: Database connection failed
# Solution: Check if PostgreSQL container is running
./docker-compose-local.sh status
./docker-compose-local.sh logs db
```

#### Migration Issues
```bash
# Error: Migration failed
# Solution: Reset database (WARNING: loses data)
./docker-compose-local.sh clean
./docker-compose-local.sh start
```

### Getting Help
1. **Check the logs**: `./docker-compose-local.sh logs [service]`
2. **Review the troubleshooting section** in this guide
3. **Ask on team Slack** channels
4. **Create an issue** in the project repository
5. **Contact the tech lead** for urgent issues

## 📞 Team Contacts

- **Tech Lead**: [Name] - [Slack: @username]
- **DevOps**: [Name] - [Slack: @username]
- **Product Owner**: [Name] - [Slack: @username]

## 📝 Additional Resources

- [Project README](README.md) - High-level project overview
- [API Documentation](http://localhost:3001/docs) - Interactive API docs
- [Architecture Decisions](backlog/decisions/) - Architectural decision records
- [Development Workflow](backlog/docs/Development/) - Detailed development process

---

**Welcome to the team!** 🎉 If you have any questions or run into issues, don't hesitate to reach out. We're here to help you be successful.

Happy coding! 💻