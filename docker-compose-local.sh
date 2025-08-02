#!/bin/bash

# Sprint Reports v2 - Local Development Environment Manager
# This script manages the local development environment using Docker Compose

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="backend/docker-compose.local.yml"
PROJECT_NAME="sprint_reports_v2_local"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop and try again."
        exit 1
    fi
}

# Function to stop existing containers
stop_containers() {
    print_status "Stopping existing containers..."
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down --remove-orphans 2>/dev/null || true
    print_success "Containers stopped"
}

# Function to start services
start_services() {
    print_status "Starting Sprint Reports v2 local development environment..."
    
    # Build and start services
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d --build
    
    print_success "Services started successfully!"
    print_status "Waiting for services to be ready..."
    
    # Wait for database to be ready
    timeout=60
    while ! docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec -T db pg_isready -U sprint_reports >/dev/null 2>&1; do
        timeout=$((timeout - 1))
        if [ $timeout -eq 0 ]; then
            print_error "Database failed to start within 60 seconds"
            exit 1
        fi
        sleep 1
    done
    
    # Run database migrations (temporarily disabled for testing)
    # print_status "Running database migrations..."
    # docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec -T app alembic upgrade head
    
    print_success "Development environment is ready!"
    echo
    echo "🚀 Sprint Reports v2 Local Development Environment"
    echo "=================================================="
    echo "📖 API Documentation: http://localhost:3001/docs"
    echo "🔌 Backend API:       http://localhost:3001"
    echo "🗄️  PostgreSQL:       localhost:5433"
    echo "⚡ Redis:             localhost:6380"
    echo
    echo "Optional Tools (use --tools flag):"
    echo "🔧 pgAdmin:           http://localhost:8080"
    echo "🔧 Redis Commander:   http://localhost:8081"
    echo
    echo "💡 Use 'docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f' to view logs"
    echo "💡 Use '$0 stop' to stop all services"
}

# Function to show logs
show_logs() {
    if [ -n "$2" ]; then
        docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f "$2"
    else
        docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f
    fi
}

# Function to show status
show_status() {
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME ps
}

# Function to run tests
run_tests() {
    print_status "Running backend tests..."
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec app pytest -v
}

# Function to access shell
access_shell() {
    service=${2:-app}
    print_status "Accessing $service shell..."
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME exec $service bash
}

# Function to show help
show_help() {
    echo "Sprint Reports v2 - Local Development Environment Manager"
    echo
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo
    echo "Commands:"
    echo "  start         Start the development environment"
    echo "  stop          Stop all services"
    echo "  restart       Restart all services"
    echo "  status        Show service status"
    echo "  logs [svc]    Show logs (optionally for specific service)"
    echo "  test          Run backend tests"
    echo "  shell [svc]   Access service shell (default: app)"
    echo "  clean         Stop services and remove volumes"
    echo "  help          Show this help message"
    echo
    echo "Options:"
    echo "  --tools       Include optional development tools (pgAdmin, Redis Commander)"
    echo
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 start --tools"
    echo "  $0 logs app"
    echo "  $0 shell db"
    echo "  $0 test"
}

# Main script logic
case "${1:-start}" in
    start)
        check_docker
        stop_containers
        
        # Check for tools flag
        if [[ "$*" == *"--tools"* ]]; then
            export COMPOSE_PROFILES="tools"
        fi
        
        start_services
        ;;
    stop)
        check_docker
        stop_containers
        ;;
    restart)
        check_docker
        stop_containers
        start_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$@"
        ;;
    test)
        run_tests
        ;;
    shell)
        access_shell "$@"
        ;;
    clean)
        check_docker
        print_warning "This will stop all services and remove all data volumes."
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down -v --remove-orphans
            print_success "Environment cleaned"
        else
            print_status "Operation cancelled"
        fi
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac