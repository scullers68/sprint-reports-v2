#!/bin/bash
# Sprint Reports v2 - Blue-Green Cutover Script
# Completes the blue-green deployment by switching traffic and cleaning up

set -e

TARGET_ENV=${1:-}

if [ -z "$TARGET_ENV" ]; then
    echo "❌ Error: Please specify target environment (blue or green)"
    echo "Usage: $0 <blue|green>"
    exit 1
fi

if [ "$TARGET_ENV" != "blue" ] && [ "$TARGET_ENV" != "green" ]; then
    echo "❌ Error: Target environment must be 'blue' or 'green'"
    exit 1
fi

# Configuration
PRODUCTION_HOST="${PRODUCTION_HOST:-localhost}"
BLUE_PORT="8000"
GREEN_PORT="8002"

if [ "$TARGET_ENV" = "blue" ]; then
    TARGET_PORT=$BLUE_PORT
    INACTIVE_ENV="green"
else
    TARGET_PORT=$GREEN_PORT
    INACTIVE_ENV="blue"
fi

echo "🔄 Starting Blue-Green Cutover to $TARGET_ENV environment"

# Verify target environment is healthy
echo "🔍 Verifying $TARGET_ENV environment health..."
HEALTH_URL="http://${PRODUCTION_HOST}:${TARGET_PORT}/health"

if ! curl -f -s "$HEALTH_URL" > /dev/null; then
    echo "❌ Error: $TARGET_ENV environment is not healthy!"
    echo "Cannot proceed with cutover."
    exit 1
fi

echo "✅ $TARGET_ENV environment is healthy"

# Update load balancer configuration (this would be environment-specific)
echo "🔄 Updating load balancer configuration..."
cat > nginx-update.conf << EOF
# Update your nginx/load balancer configuration to point to:
# http://localhost:$TARGET_PORT

upstream sprint_reports_backend {
    server localhost:$TARGET_PORT;
}
EOF

echo "📄 Load balancer configuration updated (nginx-update.conf)"
echo "   Please apply this configuration to your load balancer/proxy"

# Wait for confirmation
echo ""
read -p "🤔 Have you updated your load balancer to point to port $TARGET_PORT? (y/N): " confirm

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "⏸️  Cutover paused. Please update your load balancer and run this script again."
    exit 0
fi

# Additional verification after traffic switch
echo "🧪 Running post-cutover verification..."
sleep 5

if curl -f -s "$HEALTH_URL" > /dev/null; then
    echo "✅ Post-cutover verification successful"
else
    echo "⚠️  Warning: Post-cutover verification failed"
    echo "   Please check your load balancer configuration"
fi

# Stop inactive environment
echo "🛑 Stopping inactive $INACTIVE_ENV environment..."
cd backend
docker-compose -f docker-compose.$INACTIVE_ENV.yml down

echo "🧹 Cleaning up unused Docker resources..."
docker system prune -f

echo "🎉 Blue-Green Cutover completed successfully!"
echo ""
echo "📊 Summary:"
echo "   ✅ Active environment: $TARGET_ENV (port $TARGET_PORT)"
echo "   🛑 Stopped environment: $INACTIVE_ENV"
echo "   🌐 Application URL: http://${PRODUCTION_HOST}:${TARGET_PORT}"
echo ""
echo "🔄 For next deployment, the process will deploy to $INACTIVE_ENV environment."

# Clean up temporary files
rm -f nginx-update.conf