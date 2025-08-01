# Development Environment Setup & Contribution Guide

## Overview

This guide provides comprehensive instructions for setting up the Sprint Reports v2 development environment and contributing to the project. It covers local development setup, coding standards, testing procedures, and contribution workflows.

## Prerequisites

### System Requirements
- **Operating System**: macOS 10.15+, Ubuntu 20.04+, or Windows 10+ with WSL2
- **Memory**: Minimum 8GB RAM (16GB recommended)
- **Storage**: At least 10GB free space
- **Network**: Reliable internet connection for dependency downloads

### Required Software

#### Core Development Tools
```bash
# Python 3.11+
python --version  # Should be 3.11.0 or higher

# Node.js 18+ (for frontend development)
node --version    # Should be 18.0.0 or higher
npm --version     # Should be 9.0.0 or higher

# Git
git --version     # Should be 2.30.0 or higher

# Docker and Docker Compose
docker --version         # Should be 20.10.0 or higher
docker-compose --version # Should be 2.0.0 or higher
```

#### Database Tools
```bash
# PostgreSQL 15+ (local development)
psql --version    # Should be 15.0 or higher

# Redis 7+ (caching and sessions)
redis-server --version  # Should be 7.0.0 or higher

# Optional: pgAdmin or DBeaver for database management
```

#### Development Tools
```bash
# Code editor (recommended: VS Code with Python extension)
code --version

# Python package manager
pip --version     # Should be 22.0.0 or higher

# Optional but recommended
pipenv --version  # For virtual environment management
pre-commit --version  # For git hooks
```

## Quick Start

### 1. Repository Setup
```bash
# Clone the repository
git clone https://github.com/your-org/sprint-reports-v2.git
cd sprint-reports-v2

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
cd backend
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### 2. Environment Configuration
```bash
# Copy environment template
cp backend/.env.example backend/.env

# Edit configuration (see Environment Variables section)
nano backend/.env  # or your preferred editor
```

### 3. Database Setup

#### Option A: Docker Compose (Recommended)
```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Run database migrations
cd backend
alembic upgrade head

# Seed development data
python -c "
from app.core.database import get_db_session
from app.core.seed_data import seed_development_data
import asyncio

async def run_seed():
    db = await get_db_session()
    await seed_development_data(db)
    await db.close()

asyncio.run(run_seed())
"
```

#### Option B: Local Installation
```bash
# Install PostgreSQL
# macOS: brew install postgresql
# Ubuntu: sudo apt-get install postgresql postgresql-contrib

# Start PostgreSQL service
# macOS: brew services start postgresql
# Ubuntu: sudo systemctl start postgresql

# Create database and user
createuser -s sprint_reports
createdb -O sprint_reports sprint_reports_dev

# Install Redis
# macOS: brew install redis
# Ubuntu: sudo apt-get install redis-server

# Start Redis
# macOS: brew services start redis
# Ubuntu: sudo systemctl start redis-server
```

### 4. Run the Application
```bash
# Start the backend API
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, start the frontend (when available)
cd frontend
npm install
npm run dev

# Access the application
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Frontend: http://localhost:3000
```

## Environment Variables

### Backend Configuration
```bash
# backend/.env
# Database
DATABASE_URL=postgresql+asyncpg://sprint_reports:password@localhost:5432/sprint_reports_dev
POSTGRES_SERVER=localhost
POSTGRES_USER=sprint_reports
POSTGRES_PASSWORD=password
POSTGRES_DB=sprint_reports_dev

# Security
SECRET_KEY=your-super-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis
REDIS_URL=redis://localhost:6379/0

# JIRA Integration (get from your JIRA admin)
JIRA_URL=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token

# Confluence Integration
CONFLUENCE_URL=https://your-company.atlassian.net/wiki

# Development Settings
LOG_LEVEL=DEBUG
ENABLE_REAL_TIME_UPDATES=true
ENABLE_ML_INSIGHTS=false
ENABLE_AUDIT_LOGGING=true

# CORS (for frontend development)
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000
```

### Development Secrets
```bash
# Generate a secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Get JIRA API token
# 1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
# 2. Create API token
# 3. Copy the token to JIRA_API_TOKEN
```

## Development Workflows

### 1. Feature Development Workflow
```bash
# 1. Create feature branch
git checkout -b feature/sprint-queue-optimization

# 2. Make changes following coding standards
# 3. Run tests locally
pytest tests/ -v

# 4. Run code quality checks
black .
isort .
flake8 .
mypy .

# 5. Commit changes (pre-commit hooks will run)
git add .
git commit -m "feat(queue): optimize sprint queue generation algorithm"

# 6. Push and create pull request
git push origin feature/sprint-queue-optimization
# Create PR via GitHub web interface
```

### 2. Testing Workflow
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only
pytest tests/api/          # API tests only

# Run tests with debugging
pytest -v -s tests/test_specific.py::test_function

# Performance testing
pytest tests/performance/ --benchmark-only
```

### 3. Database Development
```bash
# Create new migration
alembic revision --autogenerate -m "add user authentication fields"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Check migration status
alembic current
alembic history

# Seed test data
python scripts/seed_test_data.py
```

## Coding Standards

### 1. Python Code Style

#### Formatting
```python
# Use Black for code formatting (88 character line length)
# Use isort for import sorting
# Follow PEP 8 with Black modifications

# Example well-formatted code
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.sprint import Sprint
from app.schemas.sprint import SprintCreate, SprintRead
from app.services.sprint_service import SprintService


class SprintManager:
    """
    Manages sprint operations including CRUD and analysis.
    
    This class provides a clean interface for sprint management
    operations while maintaining separation of concerns.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.service = SprintService(db)
    
    async def create_sprint(
        self, 
        sprint_data: SprintCreate
    ) -> SprintRead:
        """
        Create a new sprint with validation.
        
        Args:
            sprint_data: Sprint creation data
            
        Returns:
            Created sprint data
            
        Raises:
            HTTPException: If sprint creation fails
        """
        try:
            sprint = await self.service.create_sprint(sprint_data)
            return SprintRead.from_orm(sprint)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
```

#### Type Hints
```python
# Always use type hints
from typing import List, Dict, Optional, Union, Any
from datetime import datetime

# Function signatures
async def get_sprint_analysis(
    sprint_id: int,
    analysis_type: str = "discipline_team",
    include_details: bool = False
) -> Optional[Dict[str, Any]]:
    """Get sprint analysis with proper typing."""
    pass

# Class attributes
class SprintAnalysis:
    total_issues: int
    total_story_points: float
    team_breakdown: Dict[str, Dict[str, Union[int, float]]]
    created_at: datetime
```

#### Error Handling
```python
# Use specific exception types
from app.core.exceptions import (
    NotFoundError, 
    ValidationError, 
    ExternalServiceError
)

async def get_sprint_by_id(sprint_id: int) -> Sprint:
    """Get sprint with proper error handling."""
    try:
        sprint = await self.service.get_sprint(sprint_id)
        if not sprint:
            raise NotFoundError("Sprint", sprint_id)
        return sprint
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise ExternalServiceError("Database", str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
```

### 2. API Design Standards

#### Endpoint Design
```python
# RESTful endpoint patterns
@router.get("/sprints", response_model=List[SprintRead])
async def list_sprints(
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    state: Optional[str] = Query(None, regex="^(future|active|closed)$"),
    db: AsyncSession = Depends(get_db)
):
    """List sprints with filtering and pagination."""
    pass

@router.post("/sprints", response_model=SprintRead, status_code=201)
async def create_sprint(
    sprint_data: SprintCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new sprint."""
    pass

@router.get("/sprints/{sprint_id}", response_model=SprintRead)
async def get_sprint(
    sprint_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific sprint."""
    pass
```

#### Response Formatting
```python
# Use consistent response patterns
from app.core.responses import ResponseBuilder

@router.get("/sprints")
async def list_sprints(request: Request, db: AsyncSession = Depends(get_db)):
    """List sprints with standardized response."""
    builder = ResponseBuilder(request)
    
    sprints = await sprint_service.get_sprints()
    total = await sprint_service.count_sprints()
    
    return builder.list(
        items=sprints,
        total=total,
        page=1,
        per_page=25
    )
```

### 3. Testing Standards

#### Test Structure
```python
# tests/test_sprint_service.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sprint import Sprint
from app.schemas.sprint import SprintCreate
from app.services.sprint_service import SprintService


class TestSprintService:
    """Test cases for SprintService."""
    
    @pytest.fixture
    async def sprint_service(self, test_session: AsyncSession):
        """Create sprint service instance."""
        return SprintService(test_session)
    
    @pytest.fixture
    async def sample_sprint_data(self):
        """Create sample sprint data."""
        return SprintCreate(
            jira_sprint_id=1001,
            name="Test Sprint 2025.01",
            state="active",
            goal="Test sprint goal"
        )
    
    async def test_create_sprint(
        self, 
        sprint_service: SprintService,
        sample_sprint_data: SprintCreate
    ):
        """Test creating a new sprint."""
        # Act
        sprint = await sprint_service.create_sprint(sample_sprint_data)
        
        # Assert
        assert sprint.id is not None
        assert sprint.name == sample_sprint_data.name
        assert sprint.state == sample_sprint_data.state
        assert sprint.jira_sprint_id == sample_sprint_data.jira_sprint_id
    
    async def test_get_nonexistent_sprint(self, sprint_service: SprintService):
        """Test getting a non-existent sprint."""
        # Act & Assert
        sprint = await sprint_service.get_sprint(99999)
        assert sprint is None
    
    @pytest.mark.parametrize("state,expected_count", [
        ("active", 1),
        ("future", 0),
        ("closed", 0)
    ])
    async def test_get_sprints_by_state(
        self,
        sprint_service: SprintService,
        sample_sprint_data: SprintCreate,
        state: str,
        expected_count: int
    ):
        """Test filtering sprints by state."""
        # Arrange
        await sprint_service.create_sprint(sample_sprint_data)
        
        # Act
        sprints = await sprint_service.get_sprints(state=state)
        
        # Assert
        assert len(sprints) == expected_count
```

#### API Testing
```python
# tests/api/test_sprints.py
async def test_create_sprint_api(test_client: AsyncClient):
    """Test sprint creation via API."""
    # Arrange
    sprint_data = {
        "jira_sprint_id": 1001,
        "name": "API Test Sprint",
        "state": "active",
        "goal": "Test goal"
    }
    
    # Act
    response = await test_client.post("/api/v1/sprints", json=sprint_data)
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["data"]["name"] == sprint_data["name"]
    assert "links" in data
    assert "self" in data["links"]

async def test_get_sprints_pagination(test_client: AsyncClient):
    """Test sprint list pagination."""
    # Act
    response = await test_client.get("/api/v1/sprints?page=1&per_page=10")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert "links" in data
    assert data["meta"]["page"] == 1
    assert data["meta"]["per_page"] == 10
```

## Debugging and Troubleshooting

### 1. Common Issues

#### Database Connection Issues
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Check database exists
psql -h localhost -U sprint_reports -l

# Test connection
psql -h localhost -U sprint_reports -d sprint_reports_dev -c "SELECT 1;"

# Reset database
dropdb sprint_reports_dev
createdb -O sprint_reports sprint_reports_dev
alembic upgrade head
```

#### Redis Connection Issues
```bash
# Check Redis is running
redis-cli ping  # Should return PONG

# Check Redis configuration
redis-cli info server

# Test connection
redis-cli -u redis://localhost:6379 ping
```

#### Python Environment Issues
```bash
# Check Python version
python --version

# Check virtual environment
which python
which pip

# Reinstall dependencies
pip install --upgrade pip
pip install -r requirements-dev.txt --force-reinstall

# Clear Python cache
find . -type d -name __pycache__ -delete
find . -name "*.pyc" -delete
```

### 2. Debugging Tools

#### VS Code Configuration
```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug FastAPI",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/backend/app/main.py",
            "args": [],
            "console": "integratedTerminal",
            "envFile": "${workspaceFolder}/backend/.env",
            "cwd": "${workspaceFolder}/backend"
        },
        {
            "name": "Debug Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": [
                "tests/",
                "-v",
                "-s"
            ],
            "console": "integratedTerminal",
            "envFile": "${workspaceFolder}/backend/.env.test",
            "cwd": "${workspaceFolder}/backend"
        }
    ]
}
```

#### Logging Configuration
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Database query logging
# In .env: LOG_LEVEL=DEBUG
# SQLAlchemy will log all queries

# Custom debug logging
import logging
logger = logging.getLogger(__name__)

async def debug_function():
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
```

## Performance Optimization

### 1. Database Performance
```python
# Use proper SQLAlchemy patterns
from sqlalchemy.orm import selectinload, joinedload

# Efficient loading
sprint = await db.execute(
    select(Sprint)
    .options(
        selectinload(Sprint.analyses),
        joinedload(Sprint.created_by_user)
    )
    .where(Sprint.id == sprint_id)
)

# Batch operations
await db.execute(
    insert(Sprint).values([
        {"name": "Sprint 1", "state": "active"},
        {"name": "Sprint 2", "state": "future"},
    ])
)

# Use indexes effectively
# See DATABASE_PATTERNS.md for indexing strategies
```

### 2. API Performance
```python
# Use async/await properly
async def efficient_function():
    # Good: concurrent operations
    results = await asyncio.gather(
        get_sprint_data(1),
        get_sprint_data(2),
        get_sprint_data(3)
    )
    
    # Bad: sequential operations
    # results = []
    # for i in [1, 2, 3]:
    #     result = await get_sprint_data(i)
    #     results.append(result)

# Cache frequently accessed data
from functools import lru_cache

@lru_cache(maxsize=128)
def get_configuration(key: str) -> str:
    # Expensive operation
    return compute_config_value(key)
```

## Contributing Guidelines

### 1. Pull Request Process
1. **Fork the repository** and create a feature branch
2. **Follow naming conventions**: `feature/description`, `fix/description`, `docs/description`
3. **Write comprehensive tests** for new functionality
4. **Update documentation** as needed
5. **Follow coding standards** and run quality checks
6. **Create detailed PR description** with context and testing notes
7. **Request review** from appropriate team members
8. **Address feedback** promptly and thoroughly

### 2. Code Review Checklist
- [ ] Code follows style guidelines and standards
- [ ] All tests pass and coverage is maintained
- [ ] New features have appropriate tests
- [ ] Documentation is updated
- [ ] No security vulnerabilities introduced
- [ ] Performance impact is acceptable
- [ ] Breaking changes are properly documented
- [ ] Database migrations are safe and reversible

### 3. Release Process
1. **Feature branches** merge to `develop`
2. **Release branches** created from `develop`
3. **Testing and bug fixes** happen on release branch
4. **Release branch** merges to `main` and tagged
5. **Hotfixes** can be applied directly to `main`

## Additional Resources

### Documentation
- [Architecture Overview](./ARCHITECTURE.md)
- [Database Patterns](./DATABASE_PATTERNS.md)
- [Deployment Guide](./DEPLOYMENT_ARCHITECTURE.md)
- [API Documentation](http://localhost:8000/docs) (when running locally)

### External Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Documentation](https://docs.docker.com/)

### Community
- **Slack Channel**: #sprint-reports-dev
- **GitHub Discussions**: Use for questions and ideas
- **Issues**: Report bugs and request features
- **Wiki**: Additional documentation and guides

---

*This development guide ensures consistent development practices and smooth onboarding for all contributors to Sprint Reports v2.*