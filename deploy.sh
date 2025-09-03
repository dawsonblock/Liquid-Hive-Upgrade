#!/bin/bash

# Liquid-Hive Deployment Script
# This script provides various deployment options for the Liquid-Hive project

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."

    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command_exists docker-compose; then
        print_warning "Docker Compose is not installed. Some features may not work."
    fi

    print_success "Prerequisites check passed."
}

# Function to setup environment
setup_environment() {
    print_info "Setting up environment..."

    # Create necessary directories
    mkdir -p data/qdrant_storage
    mkdir -p data/ingest
    mkdir -p data/rag_index

    # Check if .env exists
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating template..."
        cat > .env << EOF
# Liquid-Hive Environment Configuration

# API Keys (Required)
DEEPSEEK_API_KEY=your_deepseek_api_key_here
HUGGING_FACE_HUB_TOKEN=your_huggingface_token_here

# Redis Configuration
REDIS_URL=redis://redis:6379
REDIS_API_TOKEN=your_redis_token_here

# Database Configuration
NEO4J_USER=neo4j
NEO4J_PASSWORD=change_this_password

# Logging
LOG_LEVEL=INFO
LOG_JSON=1

# Optional: External Services
VLLM_ENDPOINT=http://vllm:8000
GRAFANA_SMTP_HOST=
GRAFANA_SMTP_USER=
GRAFANA_SMTP_PASSWORD=
GRAFANA_SMTP_FROM=
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url
EOF
        print_warning "Please edit .env file with your actual API keys and configuration."
        print_warning "Press Enter to continue or Ctrl+C to exit."
        read -r
    fi

    print_success "Environment setup completed."
}

# Function to deploy with Docker Compose
deploy_docker_compose() {
    print_info "Deploying with Docker Compose..."

    # Check if GPU is available
    if command_exists nvidia-smi; then
        print_info "GPU detected. Enabling GPU profile..."
        docker-compose --profile gpu up -d
    else
        print_info "No GPU detected. Running CPU-only deployment..."
        docker-compose up -d
    fi

    print_success "Docker Compose deployment completed."
    print_info "Services should be available at:"
    print_info "  - API: http://localhost:8000"
    print_info "  - Grafana: http://localhost:3000 (admin/admin)"
    print_info "  - Prometheus: http://localhost:9090"
    print_info "  - Redis: localhost:6379"
    print_info "  - Neo4j: localhost:7687"
    print_info "  - Qdrant: localhost:6333"
}

# Function to deploy with Kubernetes
deploy_kubernetes() {
    print_info "Deploying to Kubernetes..."

    if ! command_exists kubectl; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi

    if ! command_exists helm; then
        print_error "Helm is not installed. Please install Helm first."
        exit 1
    fi

    # Check if we're in a Kubernetes cluster
    if ! kubectl cluster-info >/dev/null 2>&1; then
        print_error "Not connected to a Kubernetes cluster."
        exit 1
    fi

    # Create namespace
    kubectl create namespace liquid-hive --dry-run=client -o yaml | kubectl apply -f -

    # Deploy with Helm
    helm upgrade --install liquid-hive ./helm/liquid-hive \
        --namespace liquid-hive \
        --values ./helm/liquid-hive/values-dev.yaml \
        --wait

    print_success "Kubernetes deployment completed."
    print_info "Get service URL:"
    print_info "  kubectl get svc -n liquid-hive"
}

# Function to build Docker image
build_docker() {
    print_info "Building Docker image..."

    # Build the image
    docker build -t liquid-hive:latest .

    print_success "Docker image built successfully."
}

# Function to run tests
run_tests() {
    print_info "Running tests..."

    # Backend tests
    if [ -f "requirements.txt" ]; then
        print_info "Running backend tests..."
        python -m pytest tests/ -v
    fi

    # Frontend tests
    if [ -d "frontend" ]; then
        print_info "Running frontend tests..."
        cd frontend
        npm test -- --watchAll=false
        cd ..
    fi

    print_success "Tests completed."
}

# Function to show status
show_status() {
    print_info "Checking deployment status..."

    if command_exists docker-compose; then
        print_info "Docker Compose services:"
        docker-compose ps
    fi

    if command_exists kubectl; then
        print_info "Kubernetes pods:"
        kubectl get pods -n liquid-hive 2>/dev/null || true
    fi
}

# Function to cleanup
cleanup() {
    print_info "Cleaning up deployment..."

    if command_exists docker-compose; then
        docker-compose down -v
    fi

    if command_exists kubectl; then
        helm uninstall liquid-hive -n liquid-hive 2>/dev/null || true
        kubectl delete namespace liquid-hive 2>/dev/null || true
    fi

    print_success "Cleanup completed."
}

# Main menu
show_menu() {
    echo
    echo "========================================"
    echo "    Liquid-Hive Deployment Script"
    echo "========================================"
    echo
    echo "Available options:"
    echo "  1) Setup Environment"
    echo "  2) Build Docker Image"
    echo "  3) Deploy with Docker Compose"
    echo "  4) Deploy to Kubernetes"
    echo "  5) Run Tests"
    echo "  6) Show Status"
    echo "  7) Cleanup"
    echo "  8) Exit"
    echo
    read -p "Choose an option (1-8): " choice
    echo
}

# Main script
main() {
    check_prerequisites

    while true; do
        show_menu

        case $choice in
            1)
                setup_environment
                ;;
            2)
                build_docker
                ;;
            3)
                deploy_docker_compose
                ;;
            4)
                deploy_kubernetes
                ;;
            5)
                run_tests
                ;;
            6)
                show_status
                ;;
            7)
                cleanup
                ;;
            8)
                print_info "Goodbye!"
                exit 0
                ;;
            *)
                print_error "Invalid option. Please choose 1-8."
                ;;
        esac

        echo
        read -p "Press Enter to continue..."
    done
}

# Run main function
main "$@"
