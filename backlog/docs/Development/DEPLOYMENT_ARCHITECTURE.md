# Deployment Architecture & CI/CD Pipeline

## Overview

This document defines the deployment architecture, CI/CD pipeline, and infrastructure patterns for Sprint Reports v2. The deployment strategy follows cloud-native principles with containerization, automated testing, and blue-green deployment patterns.

## CI/CD Pipeline Architecture

### Pipeline Stages

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Source    │───►│   Build     │───►│    Test     │───►│   Deploy    │
│   Control   │    │   Stage     │    │   Stage     │    │   Stage     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │                   │
       │                   │                   │                   │
   Git Push           Build Images        Run Tests          Deploy to
   Pull Request       Code Quality        Security Scan      Environment
   Merge to Main      Dependency Audit    Performance Test   Health Checks
```

### 1. Source Control Stage

#### Git Workflow
```yaml
# Branching Strategy
main                 # Production-ready code
├── develop         # Integration branch
├── feature/*       # Feature development
├── hotfix/*        # Emergency fixes
└── release/*       # Release preparation
```

#### Commit Standards
```bash
# Conventional Commits
feat(auth): add JWT token refresh mechanism
fix(database): resolve connection pool timeout
docs(api): update OpenAPI schema documentation
test(sprints): add integration tests for queue generation
ci(deploy): update production deployment workflow
```

#### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3.11
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: ["--max-line-length=88", "--extend-ignore=E203,W503"]
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

### 2. Build Stage

#### Docker Build Strategy
```dockerfile
# Multi-stage build for optimization
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt requirements-dev.txt ./

# Development stage
FROM base as development
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production build stage
FROM base as builder
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Production stage
FROM python:3.11-slim as production
RUN apt-get update && apt-get install -y libpq5 && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app .

USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### Build Optimization
```yaml
# GitHub Actions Build Configuration
name: Build and Test
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11]
        
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
        cache: 'pip'
    
    - name: Install dependencies  
      run: |
        pip install --upgrade pip
        pip install -r requirements-dev.txt
    
    - name: Code quality checks
      run: |
        black --check .
        isort --check-only .
        flake8 .
        mypy .
    
    - name: Build Docker image
      run: |
        docker build -t sprint-reports:${{ github.sha }} .
        docker tag sprint-reports:${{ github.sha }} sprint-reports:latest
```

### 3. Test Stage

#### Testing Strategy
```python
# Test Configuration
# conftest.py
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.main import app
from app.core.database import get_db, Base

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/test_sprint_reports"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def test_session(test_engine):
    """Create test database session."""
    async with AsyncSession(test_engine) as session:
        yield session
        await session.rollback()

@pytest.fixture
async def test_client(test_session):
    """Create test HTTP client."""
    app.dependency_overrides[get_db] = lambda: test_session
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()
```

#### Test Categories
```yaml
# Testing Pipeline
test_stages:
  unit_tests:
    command: pytest tests/unit/ -v --cov=app --cov-report=xml
    coverage_threshold: 90%
    
  integration_tests:
    command: pytest tests/integration/ -v
    requires: [postgresql, redis]
    
  api_tests:
    command: pytest tests/api/ -v
    requires: [test_server]
    
  performance_tests:
    command: locust -f tests/performance/locustfile.py --headless -u 50 -r 10 -t 60s
    thresholds:
      avg_response_time: 500ms
      error_rate: 1%
      
  security_tests:
    command: bandit -r app/
    includes:
      - dependency_check: safety check
      - secret_scan: truffleHog
      - sast: semgrep
```

#### Quality Gates
```python
# Quality gate configuration
QUALITY_GATES = {
    'code_coverage': {
        'minimum': 90,
        'target': 95
    },
    'performance': {
        'api_response_time_p95': 500,  # milliseconds
        'database_query_time_p95': 100  # milliseconds
    },
    'security': {
        'high_vulnerabilities': 0,
        'medium_vulnerabilities': 5
    },
    'code_quality': {
        'maintainability_rating': 'A',
        'reliability_rating': 'A',
        'security_rating': 'A'
    }
}
```

### 4. Deploy Stage

#### Environment Strategy
```yaml
environments:
  development:
    cluster: dev-cluster
    namespace: sprint-reports-dev
    replicas: 1
    resources:
      cpu: 100m
      memory: 256Mi
    database: postgresql-dev
    
  staging:
    cluster: staging-cluster  
    namespace: sprint-reports-staging
    replicas: 2
    resources:
      cpu: 200m
      memory: 512Mi
    database: postgresql-staging
    
  production:
    cluster: prod-cluster
    namespace: sprint-reports-prod
    replicas: 3
    resources:
      cpu: 500m
      memory: 1Gi
    database: postgresql-prod-cluster
    auto_scaling:
      min_replicas: 3
      max_replicas: 10
      cpu_threshold: 70%
```

#### Blue-Green Deployment
```yaml
# Blue-Green Deployment Strategy
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sprint-reports-blue
  labels:
    app: sprint-reports
    version: blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sprint-reports
      version: blue
  template:
    metadata:
      labels:
        app: sprint-reports
        version: blue
    spec:
      containers:
      - name: api
        image: sprint-reports:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: sprint-reports-service
spec:
  selector:
    app: sprint-reports
    version: blue  # Switch to green during deployment
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

#### Deployment Pipeline
```yaml
# GitHub Actions Deployment
name: Deploy to Production
on:
  push:
    branches: [main]
    
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-west-2
    
    - name: Build and push Docker image
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        ECR_REPOSITORY: sprint-reports
        IMAGE_TAG: ${{ github.sha }}
      run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
    
    - name: Deploy to EKS
      run: |
        aws eks update-kubeconfig --name production-cluster
        
        # Update deployment with new image
        kubectl set image deployment/sprint-reports-green \
          api=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
        
        # Wait for rollout
        kubectl rollout status deployment/sprint-reports-green
        
        # Run smoke tests
        kubectl run smoke-test --image=curlimages/curl --rm -i --restart=Never \
          -- curl -f http://sprint-reports-service.sprint-reports-prod.svc.cluster.local/health
        
        # Switch traffic to green
        kubectl patch service sprint-reports-service \
          -p '{"spec":{"selector":{"version":"green"}}}'
        
        # Scale down blue deployment
        kubectl scale deployment sprint-reports-blue --replicas=0
```

## Infrastructure as Code

### Kubernetes Manifests
```yaml
# infrastructure/kubernetes/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: sprint-reports-prod
  labels:
    name: sprint-reports-prod

---
# infrastructure/kubernetes/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sprint-reports-config
  namespace: sprint-reports-prod
data:
  LOG_LEVEL: "INFO"
  CORS_ORIGINS: "https://sprintreports.company.com"
  REDIS_URL: "redis://redis-service:6379"

---
# infrastructure/kubernetes/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: sprint-reports-secrets
  namespace: sprint-reports-prod
type: Opaque
data:
  SECRET_KEY: <base64-encoded-secret>
  DATABASE_URL: <base64-encoded-db-url>
  JIRA_API_TOKEN: <base64-encoded-token>
```

### Terraform Infrastructure
```hcl
# infrastructure/terraform/main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# EKS Cluster
resource "aws_eks_cluster" "sprint_reports" {
  name     = "sprint-reports-cluster"
  role_arn = aws_iam_role.cluster.arn
  version  = "1.28"

  vpc_config {
    subnet_ids = [
      aws_subnet.private_1.id,
      aws_subnet.private_2.id,
      aws_subnet.public_1.id,
      aws_subnet.public_2.id,
    ]
    endpoint_private_access = true
    endpoint_public_access  = true
  }

  depends_on = [
    aws_iam_role_policy_attachment.cluster_AmazonEKSClusterPolicy,
  ]
}

# RDS Database
resource "aws_db_instance" "sprint_reports" {
  identifier = "sprint-reports-db"
  
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.medium"
  
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_encrypted     = true
  
  db_name  = "sprint_reports"
  username = "admin"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = false
  final_snapshot_identifier = "sprint-reports-final-snapshot"
  
  tags = {
    Name        = "sprint-reports-db"
    Environment = "production"
  }
}

# ElastiCache Redis
resource "aws_elasticache_replication_group" "sprint_reports" {
  replication_group_id         = "sprint-reports-redis"
  description                  = "Redis cluster for Sprint Reports"
  
  port                = 6379
  parameter_group_name = "default.redis7"
  node_type           = "cache.t3.micro"
  num_cache_clusters  = 2
  
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  
  tags = {
    Name        = "sprint-reports-redis"
    Environment = "production"
  }
}
```

## Monitoring and Observability

### Application Monitoring
```yaml
# Prometheus Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      
    scrape_configs:
    - job_name: 'sprint-reports-api'
      static_configs:
      - targets: ['sprint-reports-service:8000']
      metrics_path: /metrics
      scrape_interval: 10s
      
    - job_name: 'postgresql'
      static_configs:
      - targets: ['postgres-exporter:9187']
      
    - job_name: 'redis'
      static_configs:
      - targets: ['redis-exporter:9121']

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
  - static_configs:
    - targets:
      - alertmanager:9093
```

### Alerting Rules
```yaml
# Alert Rules
groups:
- name: sprint-reports-alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: High error rate detected
      description: "Error rate is {{ $value }} errors per second"
      
  - alert: DatabaseConnectionFailure
    expr: pg_up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: Database connection failure
      description: "PostgreSQL database is down"
      
  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: High response time
      description: "95th percentile response time is {{ $value }} seconds"
```

### Logging Strategy
```yaml
# Fluent Bit Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         1
        Log_Level     info
        Daemon        off
        Parsers_File  parsers.conf
        
    [INPUT]
        Name              tail
        Path              /var/log/containers/*sprint-reports*.log
        Parser            docker
        Tag               kube.sprint-reports.*
        Refresh_Interval  5
        
    [FILTER]
        Name                kubernetes
        Match               kube.sprint-reports.*
        Kube_URL            https://kubernetes.default.svc:443
        Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
        
    [OUTPUT]
        Name            es
        Match           kube.sprint-reports.*
        Host            elasticsearch.logging.svc.cluster.local
        Port            9200
        Index           sprint-reports-logs
        Type            _doc
```

## Implementation Guidelines for Subtasks

### Task 001.05 - CI/CD Pipeline Establishment
**Priority Actions**:
1. **GitHub Actions Setup**: Create workflows in `.github/workflows/`
2. **Docker Configuration**: Enhance existing Dockerfile with multi-stage builds
3. **Kubernetes Manifests**: Create deployment configs in `/infrastructure/kubernetes/`
4. **Monitoring Setup**: Configure Prometheus metrics and alerts
5. **Security Scanning**: Integrate security tools into pipeline

**Files to Create** (Only if necessary):
- `.github/workflows/ci.yml` - Continuous integration pipeline
- `.github/workflows/cd.yml` - Continuous deployment pipeline
- `infrastructure/kubernetes/` - Kubernetes deployment manifests
- `infrastructure/terraform/` - Infrastructure as code
- `docker-compose.prod.yml` - Production docker compose

### Performance Targets
- **Build Time**: <5 minutes for typical builds
- **Deployment Time**: <10 minutes for production deployment
- **Test Execution**: <15 minutes for full test suite
- **Zero Downtime**: Blue-green deployment with <1 second switchover

---

*This deployment architecture ensures reliable, scalable, and maintainable deployments with comprehensive monitoring and automated quality gates.*