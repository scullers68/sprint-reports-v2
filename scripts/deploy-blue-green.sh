#!/bin/bash
# Sprint Reports v2 - Blue-Green Deployment Script
# Implements zero-downtime deployment using existing Docker infrastructure

set -e

echo "🔵🟢 Starting Blue-Green Deployment for Sprint Reports v2"

# Configuration
PRODUCTION_HOST="${PRODUCTION_HOST:-localhost}"
BLUE_PORT="8000"
GREEN_PORT="8002"
HEALTH_CHECK_URL_BLUE="http://${PRODUCTION_HOST}:${BLUE_PORT}/health"
HEALTH_CHECK_URL_GREEN="http://${PRODUCTION_HOST}:${GREEN_PORT}/health"
DOCKER_IMAGE_TAG="${GITHUB_SHA:-latest}"

# Load environment variables
if [ -f ".env.production" ]; then
    echo "📄 Loading production environment variables..."
    export $(cat .env.production | xargs)
else
    echo "❌ Error: .env.production file not found"
    exit 1
fi

# Navigate to backend directory
cd backend

# Determine current active environment
determine_active_env() {
    if curl -f -s "$HEALTH_CHECK_URL_BLUE" > /dev/null; then
        echo "blue"
    elif curl -f -s "$HEALTH_CHECK_URL_GREEN" > /dev/null; then
        echo "green"
    else
        echo "none"
    fi
}

# Health check function
health_check() {
    local url=$1
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null; then
            return 0
        else
            echo "⏳ Health check attempt $attempt/$max_attempts..."
            sleep 10
            ((attempt++))
        fi
    done
    
    return 1
}

ACTIVE_ENV=$(determine_active_env)
echo "🔍 Current active environment: $ACTIVE_ENV"

# Determine target environment
if [ "$ACTIVE_ENV" = "blue" ] || [ "$ACTIVE_ENV" = "none" ]; then
    TARGET_ENV="green"
    TARGET_PORT=$GREEN_PORT
    TARGET_COMPOSE="docker-compose.green.yml"
    INACTIVE_ENV="blue"
    INACTIVE_COMPOSE="docker-compose.blue.yml"
else
    TARGET_ENV="blue"
    TARGET_PORT=$BLUE_PORT
    TARGET_COMPOSE="docker-compose.blue.yml"
    INACTIVE_ENV="green"
    INACTIVE_COMPOSE="docker-compose.green.yml"
fi

echo "🎯 Deploying to $TARGET_ENV environment (port $TARGET_PORT)"

# Create blue-green docker-compose files if they don't exist
create_blue_green_configs() {
    # Blue environment configuration
    cat > docker-compose.blue.yml << EOF
version: '3.8'

services:
  app-blue:
    build:
      context: .
      target: production
    ports:
      - "$BLUE_PORT:8000"
    environment:
      - DATABASE_URL=\${DATABASE_URL}
      - REDIS_URL=\${REDIS_URL}
      - SECRET_KEY=\${SECRET_KEY}
      - ALLOWED_HOSTS=\${ALLOWED_HOSTS}
      - CORS_ORIGINS=\${CORS_ORIGINS}
      - LOG_LEVEL=info
      - ENVIRONMENT=production-blue
    depends_on:
      - db
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - sprint-reports-prod

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=\${POSTGRES_USER}
      - POSTGRES_PASSWORD=\${POSTGRES_PASSWORD}
      - POSTGRES_DB=\${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - sprint-reports-prod

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - sprint-reports-prod

volumes:
  postgres_data:
  redis_data:

networks:
  sprint-reports-prod:
    external: true
EOF

    # Green environment configuration
    cat > docker-compose.green.yml << EOF
version: '3.8'

services:
  app-green:
    build:
      context: .
      target: production
    ports:
      - "$GREEN_PORT:8000"
    environment:
      - DATABASE_URL=\${DATABASE_URL}
      - REDIS_URL=\${REDIS_URL}
      - SECRET_KEY=\${SECRET_KEY}
      - ALLOWED_HOSTS=\${ALLOWED_HOSTS}
      - CORS_ORIGINS=\${CORS_ORIGINS}
      - LOG_LEVEL=info
      - ENVIRONMENT=production-green
    depends_on:
      - db
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - sprint-reports-prod

volumes:
  postgres_data:
  redis_data:

networks:
  sprint-reports-prod:
    external: true
EOF
}

echo "🔧 Creating blue-green configurations..."
create_blue_green_configs

# Ensure network exists
docker network create sprint-reports-prod 2>/dev/null || true

echo "🏗️  Building new image for $TARGET_ENV environment..."
docker-compose -f $TARGET_COMPOSE build --no-cache

echo "📊 Running database migrations..."
if [ "$ACTIVE_ENV" != "none" ]; then
    # Use existing environment for migrations to avoid downtime
    docker-compose -f docker-compose.$ACTIVE_ENV.yml run --rm app-$ACTIVE_ENV alembic upgrade head
else
    # First deployment - run migrations on target
    docker-compose -f $TARGET_COMPOSE run --rm app-$TARGET_ENV alembic upgrade head
fi

echo "🚀 Starting $TARGET_ENV environment..."
docker-compose -f $TARGET_COMPOSE up -d

echo "⏰ Performing health checks on $TARGET_ENV..."
if [ "$TARGET_ENV" = "blue" ]; then
    HEALTH_URL=$HEALTH_CHECK_URL_BLUE
else
    HEALTH_URL=$HEALTH_CHECK_URL_GREEN
fi

if health_check "$HEALTH_URL"; then
    echo "✅ $TARGET_ENV environment is healthy!"
else
    echo "❌ $TARGET_ENV environment failed health checks"
    echo "📜 Container logs:"
    docker-compose -f $TARGET_COMPOSE logs --tail=50 app-$TARGET_ENV
    
    echo "🛑 Rolling back - stopping $TARGET_ENV..."
    docker-compose -f $TARGET_COMPOSE down
    exit 1
fi

echo "🧪 Running smoke tests on $TARGET_ENV..."
if curl -f -s "http://${PRODUCTION_HOST}:${TARGET_PORT}/api/v1" > /dev/null; then
    echo "✅ Smoke tests passed"
else
    echo "❌ Smoke tests failed"
    echo "🛑 Rolling back - stopping $TARGET_ENV..."
    docker-compose -f $TARGET_COMPOSE down
    exit 1
fi

echo "🔄 Deployment successful! Both environments are now running:"
echo "   🔵 Blue:  http://${PRODUCTION_HOST}:${BLUE_PORT}"
echo "   🟢 Green: http://${PRODUCTION_HOST}:${GREEN_PORT}"
echo ""
echo "🎯 New deployment is on $TARGET_ENV environment (port $TARGET_PORT)"

if [ "$ACTIVE_ENV" != "none" ]; then
    echo ""
    echo "⚠️  Manual step required:"
    echo "   1. Verify the new deployment at: http://${PRODUCTION_HOST}:${TARGET_PORT}"
    echo "   2. Update load balancer/proxy to point to port $TARGET_PORT"
    echo "   3. Run the following command to stop the old environment:"
    echo "      docker-compose -f docker-compose.$INACTIVE_ENV.yml down"
    echo ""
    echo "   Or run the cutover script:"
    echo "      ./scripts/cutover-blue-green.sh $TARGET_ENV"
else
    echo "🎉 First deployment completed successfully!"
fi

echo "📊 Current status:"
docker-compose -f $TARGET_COMPOSE ps