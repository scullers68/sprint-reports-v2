#!/bin/bash
# Sprint Reports v2 - Staging Deployment Script
# Extends existing Docker infrastructure for automated staging deployment

set -e

echo "🚀 Starting Sprint Reports v2 Staging Deployment"

# Configuration
STAGING_HOST="${STAGING_HOST:-localhost}"
STAGING_PORT="${STAGING_PORT:-8001}"
DOCKER_IMAGE_TAG="${GITHUB_SHA:-latest}"
COMPOSE_FILE="docker-compose.staging.yml"

# Load environment variables
if [ -f ".env.staging" ]; then
    echo "📄 Loading staging environment variables..."
    export $(cat .env.staging | xargs)
else
    echo "⚠️  Warning: .env.staging file not found"
fi

# Navigate to backend directory (where existing docker-compose files are)
cd backend

echo "🛑 Stopping existing staging services..."
docker-compose -f $COMPOSE_FILE down || true

echo "🧹 Cleaning up old containers and images..."
docker system prune -f || true

echo "🏗️  Building staging image..."
docker-compose -f $COMPOSE_FILE build --no-cache

echo "📊 Running database migrations..."
docker-compose -f $COMPOSE_FILE run --rm app alembic upgrade head

echo "🚀 Starting staging services..."
docker-compose -f $COMPOSE_FILE up -d

echo "⏰ Waiting for services to be ready..."
sleep 30

echo "🔍 Running health checks..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -f -s "http://${STAGING_HOST}:${STAGING_PORT}/health" > /dev/null; then
        echo "✅ Staging deployment successful!"
        echo "🌐 Application available at: http://${STAGING_HOST}:${STAGING_PORT}"
        echo "📖 API docs available at: http://${STAGING_HOST}:${STAGING_PORT}/docs"
        break
    else
        echo "⏳ Attempt $attempt/$max_attempts - Service not ready yet..."
        sleep 10
        ((attempt++))
    fi
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ Staging deployment failed - health check timeout"
    echo "📜 Container logs:"
    docker-compose -f $COMPOSE_FILE logs --tail=50 app
    exit 1
fi

echo "🧪 Running smoke tests..."
# Basic smoke tests
if curl -f -s "http://${STAGING_HOST}:${STAGING_PORT}/api/v1" > /dev/null; then
    echo "✅ API endpoints accessible"
else
    echo "❌ API endpoints not accessible"
    exit 1
fi

echo "📊 Deployment summary:"
docker-compose -f $COMPOSE_FILE ps

echo "🎉 Staging deployment completed successfully!"
echo "🔗 Staging URL: http://${STAGING_HOST}:${STAGING_PORT}"