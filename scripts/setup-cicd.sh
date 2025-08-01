#!/bin/bash
# Sprint Reports v2 - CI/CD Setup Script
# Sets up the complete CI/CD pipeline and development environment

set -e

echo "🚀 Setting up Sprint Reports v2 CI/CD Pipeline"

# Check prerequisites
check_prerequisites() {
    echo "🔍 Checking prerequisites..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo "❌ Docker is not running. Please start Docker."
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! docker compose version &> /dev/null && ! docker-compose --version &> /dev/null; then
        echo "❌ Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
    
    echo "✅ Prerequisites check passed"
}

# Setup environment files
setup_environment() {
    echo "📄 Setting up environment files..."
    
    if [ ! -f ".env" ]; then
        cp .env.example .env
        echo "✅ Created .env file from template"
        echo "⚠️  Please update .env with your actual configuration"
    else
        echo "ℹ️  .env file already exists"
    fi
    
    # Create staging and production environment templates
    if [ ! -f ".env.staging" ]; then
        cat > .env.staging << EOF
# Staging Environment Configuration
DATABASE_URL=postgresql+asyncpg://sprint_reports_staging:staging_password@localhost:5432/sprint_reports_v2_staging
POSTGRES_USER=sprint_reports_staging
POSTGRES_PASSWORD=staging_password
POSTGRES_DB=sprint_reports_v2_staging
REDIS_URL=redis://localhost:6379/1
SECRET_KEY=staging_secret_key_change_this_in_production
ALLOWED_HOSTS=staging.sprint-reports.com,localhost
CORS_ORIGINS=https://staging.sprint-reports.com,http://localhost:3000
ENVIRONMENT=staging
LOG_LEVEL=debug
STAGING_DB_PASSWORD=staging_password
STAGING_SECRET_KEY=staging_secret_key_change_this_in_production
EOF
        echo "✅ Created .env.staging template"
    fi
    
    if [ ! -f ".env.production" ]; then
        cat > .env.production << EOF
# Production Environment Configuration
DATABASE_URL=postgresql+asyncpg://sprint_reports:CHANGE_THIS_PASSWORD@localhost:5432/sprint_reports_v2
POSTGRES_USER=sprint_reports
POSTGRES_PASSWORD=CHANGE_THIS_PASSWORD
POSTGRES_DB=sprint_reports_v2
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=CHANGE_THIS_SECRET_KEY_MIN_32_CHARS
ALLOWED_HOSTS=your-domain.com,api.your-domain.com
CORS_ORIGINS=https://your-domain.com,https://app.your-domain.com
ENVIRONMENT=production
LOG_LEVEL=info
EOF
        echo "✅ Created .env.production template"
        echo "⚠️  IMPORTANT: Update .env.production with secure values!"
    fi
}

# Setup SonarQube for local development
setup_sonarqube() {
    echo "📊 Setting up SonarQube for local development..."
    
    cd backend
    if [ ! -f "docker-compose.sonar.yml" ]; then
        echo "❌ SonarQube configuration not found"
        return 1
    fi
    
    echo "🐳 Starting SonarQube services..."
    docker-compose -f docker-compose.sonar.yml up -d
    
    echo "⏰ Waiting for SonarQube to be ready..."
    sleep 30
    
    # Wait for SonarQube to be healthy
    max_attempts=30
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "http://localhost:9000/api/system/status" | grep -q "UP"; then
            echo "✅ SonarQube is ready at http://localhost:9000"
            echo "   Default credentials: admin/admin"
            break
        else
            echo "⏳ Waiting for SonarQube... ($attempt/$max_attempts)"
            sleep 10
            ((attempt++))
        fi
    done
    
    cd ..
}

# Install Python dependencies for local development
setup_python_env() {
    echo "🐍 Setting up Python environment..."
    
    cd backend
    
    if [ ! -d "venv" ]; then
        echo "📦 Creating Python virtual environment..."
        python -m venv venv
    fi
    
    echo "📥 Installing Python dependencies..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo "✅ Python environment ready"
    cd ..
}

# Run tests to verify setup
run_tests() {
    echo "🧪 Running tests to verify setup..."
    
    cd backend
    
    # Run basic test
    echo "🔍 Running basic API test..."
    python test_basic.py
    
    # Run security scans if dependencies are available
    if command -v bandit &> /dev/null; then
        echo "🔒 Running security scan..."
        bandit -r app/ -f json -o bandit-report.json || true
        echo "✅ Security scan completed"
    fi
    
    # Run code quality checks
    if source venv/bin/activate 2>/dev/null; then
        echo "🎨 Running code quality checks..."
        black --check app/ || echo "ℹ️  Run 'black app/' to format code"
        isort --check-only app/ || echo "ℹ️  Run 'isort app/' to sort imports"
        flake8 app/ || echo "ℹ️  Code style issues found"
        echo "✅ Code quality checks completed"
    fi
    
    cd ..
}

# Create GitHub Actions secrets template
create_secrets_template() {
    echo "🔐 Creating GitHub Actions secrets template..."
    
    cat > github-secrets-template.md << EOF
# GitHub Actions Secrets Setup

Add the following secrets to your GitHub repository:
Settings > Secrets and variables > Actions > New repository secret

## Required Secrets:

### SonarQube Integration
- \`SONAR_TOKEN\`: SonarQube authentication token
- \`SONAR_HOST_URL\`: SonarQube server URL (e.g., https://sonarcloud.io)

### Security Scanning
- \`SNYK_TOKEN\`: Snyk authentication token for vulnerability scanning

### Deployment (if using automated deployment)
- \`STAGING_HOST\`: Staging server hostname
- \`PRODUCTION_HOST\`: Production server hostname
- \`DEPLOY_SSH_KEY\`: SSH private key for deployment access
- \`STAGING_DB_PASSWORD\`: Staging database password
- \`PRODUCTION_DB_PASSWORD\`: Production database password
- \`PRODUCTION_SECRET_KEY\`: Production application secret key

## Optional Secrets:
- \`CODECOV_TOKEN\`: Codecov integration token
- \`SLACK_WEBHOOK\`: Slack webhook for deployment notifications

## Setup Instructions:
1. Generate tokens from respective services
2. Add them as GitHub repository secrets
3. Update .github/workflows/ci.yml if needed
4. Test the pipeline with a pull request

EOF
    
    echo "✅ Created github-secrets-template.md"
}

# Main execution
main() {
    echo "🎯 Sprint Reports v2 CI/CD Setup Starting..."
    echo ""
    
    check_prerequisites
    setup_environment
    setup_python_env
    setup_sonarqube
    run_tests
    create_secrets_template
    
    echo ""
    echo "🎉 CI/CD Pipeline setup completed successfully!"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Review and update environment variables in .env files"
    echo "2. Set up GitHub Actions secrets (see github-secrets-template.md)"
    echo "3. Push your code to trigger the first CI/CD pipeline run"
    echo "4. Access SonarQube at http://localhost:9000 (admin/admin)"
    echo "5. Run './scripts/deploy-staging.sh' to test staging deployment"
    echo ""
    echo "📚 Documentation:"
    echo "- CI/CD Pipeline: .github/workflows/ci.yml"
    echo "- Deployment Scripts: scripts/"
    echo "- Docker Configurations: backend/docker-compose.*.yml"
    echo ""
    echo "🔗 Useful Commands:"
    echo "- Test build: docker-compose -f backend/docker-compose.yml build"
    echo "- Run locally: docker-compose -f backend/docker-compose.yml up"
    echo "- View logs: docker-compose -f backend/docker-compose.yml logs -f"
}

# Run main function
main "$@"