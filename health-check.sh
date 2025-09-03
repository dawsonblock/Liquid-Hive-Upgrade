#!/bin/bash

# Liquid-Hive Health Check Script
# Verifies that all services are running and healthy

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BASE_URL="http://localhost:8000"

# Function to print colored output
print_info() {
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

# Function to check HTTP endpoint
check_http() {
    local url=$1
    local service_name=$2
    local timeout=${3:-10}

    if curl -s --max-time $timeout "$url" > /dev/null 2>&1; then
        print_success "$service_name is accessible at $url"
        return 0
    else
        print_error "$service_name is not accessible at $url"
        return 1
    fi
}

# Function to check API health
check_api_health() {
    print_info "Checking API health..."

    # Main health endpoint
    if ! check_http "$BASE_URL/health" "API Health"; then
        return 1
    fi

    # Detailed health checks
    if check_http "$BASE_URL/health/redis" "Redis Health" 5; then
        print_success "Redis connection is healthy"
    else
        print_warning "Redis health check failed (may not be critical)"
    fi

    if check_http "$BASE_URL/health/qdrant" "Qdrant Health" 5; then
        print_success "Qdrant connection is healthy"
    else
        print_warning "Qdrant health check failed (may not be critical)"
    fi

    return 0
}

# Function to check services
check_services() {
    print_info "Checking individual services..."

    # Grafana
    check_http "http://localhost:3000" "Grafana" 5

    # Prometheus
    check_http "http://localhost:9090" "Prometheus" 5

    # Redis (if available)
    if command -v redis-cli >/dev/null 2>&1; then
        if redis-cli -h localhost ping >/dev/null 2>&1; then
            print_success "Redis is accessible"
        else
            print_warning "Redis is not accessible"
        fi
    fi
}

# Function to check Docker services
check_docker_services() {
    if command -v docker-compose >/dev/null 2>&1; then
        print_info "Checking Docker Compose services..."

        if docker-compose ps | grep -q "Up"; then
            print_success "Docker Compose services are running"
            docker-compose ps
        else
            print_warning "No Docker Compose services appear to be running"
            return 1
        fi
    fi
}

# Function to check frontend
check_frontend() {
    print_info "Checking frontend..."

    # Check if the frontend is being served by the API
    if curl -s "$BASE_URL" | grep -q "Liquid-Hive"; then
        print_success "Frontend is being served correctly"
    else
        print_warning "Frontend may not be loading correctly"
    fi
}

# Main function
main() {
    echo "========================================"
    echo "    Liquid-Hive Health Check"
    echo "========================================"
    echo

    local all_healthy=true

    # Check Docker services first
    if ! check_docker_services; then
        all_healthy=false
    fi

    # Check API
    if ! check_api_health; then
        all_healthy=false
    fi

    # Check frontend
    if ! check_frontend; then
        all_healthy=false
    fi

    # Check other services
    check_services

    echo
    if [ "$all_healthy" = true ]; then
        print_success "🎉 All critical services are healthy!"
        echo
        print_info "Access your Liquid-Hive instance at: $BASE_URL"
        print_info "Grafana dashboards: http://localhost:3000"
        print_info "Prometheus metrics: http://localhost:9090"
    else
        print_warning "⚠️  Some services may not be fully operational"
        echo
        print_info "Check the logs for more details:"
        print_info "  docker-compose logs"
        print_info "  docker-compose logs api"
    fi

    echo
}

# Run main function
main "$@"
