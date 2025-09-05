# Liquid Hive Production-Grade Makefile

.DEFAULT_GOAL := help
.PHONY: help install dev test lint format clean build docker deploy health

# Configuration
PYTHON := python3
PIP := pip
YARN := yarn
IMAGE_TAG ?= latest

help: ## Show this help message
	@echo "Liquid Hive Development Commands"
	@echo "================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation & Setup
install: ## Install all dependencies
	@echo "📦 Installing Python dependencies..."
	$(PIP) install -r requirements.txt
	@echo "📦 Installing frontend dependencies..."
	cd frontend && $(YARN) install --frozen-lockfile
	@echo "✅ All dependencies installed!"

install-dev: ## Install development dependencies
	@echo "📦 Installing development dependencies..."
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-cov ruff bandit safety mypy
	cd frontend && $(YARN) install --frozen-lockfile
	@echo "✅ Development setup complete!"

# Development Environment
dev: ## Start complete development stack
	@echo "🚀 Starting development environment..."
	docker compose up --build
	@echo "🌐 Services available:"
	@echo "  API:        http://localhost:8080"
	@echo "  Frontend:   http://localhost:5173"
	@echo "  Grafana:    http://localhost:3000"
	@echo "  Prometheus: http://localhost:9090"

dev-api: ## Start API in development mode
	@echo "🔧 Starting API in development mode..."
	cd apps/api && uvicorn main:app --reload --host 0.0.0.0 --port 8080

dev-frontend: ## Start frontend in development mode
	@echo "🔧 Starting frontend in development mode..."
	cd frontend && $(YARN) dev

# Testing
test: ## Run complete test suite
	@echo "🧪 Running backend tests..."
	pytest tests/ --maxfail=1 --disable-warnings -q --cov=src --cov=apps --cov-report=xml
	@echo "🧪 Running frontend tests..."
	cd frontend && $(YARN) test --coverage --watchAll=false
	@echo "✅ All tests passed!"

test-unit: ## Run unit tests only
	@echo "🧪 Running unit tests..."
	pytest tests/unit/ -v

test-integration: ## Run integration tests only
	@echo "🧪 Running integration tests..."
	pytest tests/integration/ -v

test-performance: ## Run performance tests
	@echo "🏃 Running performance tests..."
	k6 run tests/performance/k6_smoke.js

# Code Quality
lint: ## Run all linters
	@echo "🔍 Linting Python code..."
	ruff check src apps
	ruff format --check src apps
	@echo "🔍 Linting frontend code..."
	cd frontend && $(YARN) lint
	@echo "✅ All linting passed!"

format: ## Format all code
	@echo "💅 Formatting Python code..."
	ruff format src apps
	@echo "💅 Formatting frontend code..."
	cd frontend && $(YARN) format
	@echo "✅ Code formatted!"

security: ## Run security checks
	@echo "🔒 Running security checks..."
	bandit -r src apps
	safety check
	@echo "✅ Security checks passed!"

# Docker Operations
build: ## Build all Docker images
	@echo "🐳 Building Docker images..."
	docker compose build

build-prod: ## Build production Docker images
	@echo "🐳 Building production images..."
	docker build -t liquid-hive-api:$(IMAGE_TAG) -f apps/api/Dockerfile .
	docker build -t liquid-hive-frontend:$(IMAGE_TAG) -f frontend/Dockerfile .

# Docker Compose Operations
up: compose-up ## Alias for compose-up
down: compose-down ## Alias for compose-down

compose-up: ## Start all services in background
	@echo "⬆️  Starting services..."
	docker compose up -d

compose-down: ## Stop all services and remove volumes
	@echo "⬇️  Stopping services..."
	docker compose down -v

logs: ## Show logs for all services
	@echo "📋 Showing service logs..."
	docker compose logs -f

logs-api: ## Show API logs only
	docker compose logs -f api

logs-frontend: ## Show frontend logs only  
	docker compose logs -f frontend

# Database Operations
db-reset: ## Reset database (if using one)
	@echo "🗄️  Resetting database..."
	docker compose down postgres || true
	docker volume rm liquid-hive_postgres_data || true
	docker compose up -d postgres

# Kubernetes Deployment
helm-apply: ## Deploy using Helm (development)
	@echo "☸️  Deploying to Kubernetes (development)..."
	helm upgrade --install liquid-hive \
		infra/helm/liquid-hive \
		-f infra/helm/liquid-hive/values-dev.yaml \
		--wait --timeout=10m
	@echo "✅ Deployment complete!"

helm-prod: ## Deploy to production
	@echo "☸️  Deploying to production..."
	helm upgrade --install liquid-hive \
		infra/helm/liquid-hive \
		-f infra/helm/liquid-hive/values-prod.yaml \
		--set image.tag=$(IMAGE_TAG) \
		--wait --timeout=10m
	@echo "✅ Production deployment complete!"

deploy: helm-apply ## Alias for helm-apply

# Health Checks
health: ## Check service health
	@echo "❤️  Checking service health..."
	@curl -s http://localhost:8080/health || echo "❌ API not responding"
	@curl -s http://localhost:5173/ || echo "❌ Frontend not responding"
	@echo "✅ Health check complete!"

# Cleanup
clean: ## Clean temporary files and caches
	@echo "🧹 Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type d -name ".mypy_cache" -delete
	find . -type d -name ".ruff_cache" -delete
	find . -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -name "coverage.xml" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	cd frontend && $(YARN) clean 2>/dev/null || true
	@echo "✅ Cleanup complete!"

clean-docker: ## Clean Docker resources
	@echo "🧹 Cleaning Docker resources..."
	docker compose down -v
	docker system prune -f
	docker volume prune -f
	@echo "✅ Docker cleanup complete!"

# CI Pipeline (local)
ci: install-dev lint test security ## Run complete CI pipeline locally
	@echo "🎉 CI pipeline completed successfully!"

# Development Workflow
dev-setup: install-dev ## Complete development setup
	@echo "⚡ Development setup complete!"
	@echo "Run 'make dev' to start the development environment"

# Documentation
docs: ## Generate API documentation
	@echo "📚 Generating documentation..."
	cd apps/api && $(PYTHON) -m pydoc -w .
	@echo "✅ Documentation generated!"

# Release Management  
release: ## Create a new release (requires version tag)
	@echo "🚀 Creating release..."
	@read -p "Enter version (e.g., v1.0.0): " version; \
	git tag -a $$version -m "Release $$version"; \
	git push origin $$version
	@echo "✅ Release $$version created!"

# Environment Templates
env-example: ## Show environment variables example
	@echo "📋 Environment variables needed:"
	@cat .env.example

# Quick Status
status: ## Show current system status
	@echo "📊 System Status:"
	@echo "  Python: $$(python --version 2>&1 || echo 'Not installed')"
	@echo "  Node:   $$(node --version 2>&1 || echo 'Not installed')" 
	@echo "  Yarn:   $$(yarn --version 2>&1 || echo 'Not installed')"
	@echo "  Docker: $$(docker --version 2>&1 || echo 'Not installed')"
	@echo "  Helm:   $$(helm version --short 2>&1 || echo 'Not installed')"
	@echo "  K6:     $$(k6 version 2>&1 || echo 'Not installed')"