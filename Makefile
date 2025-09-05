# Liquid Hive Development Makefile

.PHONY: help install dev test lint format clean build docker up down logs shell

# Default target
help: ## Show this help message
	@echo "Liquid Hive Development Commands"
	@echo "================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install all dependencies
	@echo "Installing Python dependencies..."
	pip install -e .[dev,test,docs]
	@echo "Installing Node.js dependencies..."
	cd apps/dashboard && yarn install
	@echo "Installing pre-commit hooks..."
	pre-commit install

install-prod: ## Install production dependencies
	@echo "Installing production dependencies..."
	pip install -e .

# Development
dev: ## Start development environment
	@echo "Starting development environment..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "Development environment started!"
	@echo "API: http://localhost:8000"
	@echo "Dashboard: http://localhost:3000"
	@echo "Grafana: http://localhost:3001"

dev-api: ## Start API in development mode
	@echo "Starting API in development mode..."
	uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

dev-dashboard: ## Start dashboard in development mode
	@echo "Starting dashboard in development mode..."
	cd apps/dashboard && yarn dev

# Testing
test: ## Run all tests
	@echo "Running Python tests..."
	pytest tests/unit tests/integration -v --cov=libs --cov=apps --cov-report=html --cov-report=term-missing
	@echo "Running TypeScript tests..."
	cd apps/dashboard && yarn test --coverage --watchAll=false

test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	pytest tests/unit -v

test-integration: ## Run integration tests only
	@echo "Running integration tests..."
	pytest tests/integration -v

test-e2e: ## Run end-to-end tests
	@echo "Running E2E tests..."
	docker-compose -f docker-compose.yml -f docker-compose.test.yml up --build
	docker-compose -f docker-compose.yml -f docker-compose.test.yml exec api pytest tests/e2e -v
	docker-compose -f docker-compose.yml -f docker-compose.test.yml down -v

test-coverage: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	pytest tests/ --cov=libs --cov=apps --cov-report=html --cov-report=xml --cov-report=term-missing

# Code Quality
lint: ## Run all linters
	@echo "Running Python linters..."
	ruff check libs apps
	black --check libs apps
	isort --check-only libs apps
	mypy libs apps
	bandit -r libs apps
	safety check
	@echo "Running TypeScript linters..."
	cd apps/dashboard && yarn lint
	cd apps/dashboard && yarn type-check

format: ## Format all code
	@echo "Formatting Python code..."
	ruff format libs apps
	black libs apps
	isort libs apps
	@echo "Formatting TypeScript code..."
	cd apps/dashboard && yarn format

format-check: ## Check code formatting
	@echo "Checking Python formatting..."
	ruff format --check libs apps
	black --check libs apps
	isort --check-only libs apps
	@echo "Checking TypeScript formatting..."
	cd apps/dashboard && yarn format:check

# Docker
build: ## Build all Docker images
	@echo "Building Docker images..."
	docker-compose build

build-api: ## Build API Docker image
	@echo "Building API Docker image..."
	docker build -f infra/docker/Dockerfile.api -t liquid-hive-api .

build-dashboard: ## Build dashboard Docker image
	@echo "Building dashboard Docker image..."
	docker build -f infra/docker/Dockerfile.dashboard -t liquid-hive-dashboard .

# Docker Compose
up: ## Start all services
	@echo "Starting all services..."
	docker-compose up -d

up-dev: ## Start development services
	@echo "Starting development services..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

up-prod: ## Start production services
	@echo "Starting production services..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

down: ## Stop all services
	@echo "Stopping all services..."
	docker-compose down

down-volumes: ## Stop all services and remove volumes
	@echo "Stopping all services and removing volumes..."
	docker-compose down -v

logs: ## Show logs for all services
	@echo "Showing logs for all services..."
	docker-compose logs -f

logs-api: ## Show API logs
	@echo "Showing API logs..."
	docker-compose logs -f api

logs-dashboard: ## Show dashboard logs
	@echo "Showing dashboard logs..."
	docker-compose logs -f dashboard

# Database
db-migrate: ## Run database migrations
	@echo "Running database migrations..."
	alembic upgrade head

db-migration: ## Create new database migration
	@echo "Creating new database migration..."
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

db-reset: ## Reset database
	@echo "Resetting database..."
	docker-compose down postgres
	docker volume rm liquid-hive_postgres_data || true
	docker-compose up -d postgres
	sleep 5
	make db-migrate

# Shell access
shell-api: ## Access API container shell
	@echo "Accessing API container shell..."
	docker-compose exec api bash

shell-db: ## Access database shell
	@echo "Accessing database shell..."
	docker-compose exec postgres psql -U liquid_hive liquid_hive

shell-redis: ## Access Redis shell
	@echo "Accessing Redis shell..."
	docker-compose exec redis redis-cli

# Cleanup
clean: ## Clean up temporary files
	@echo "Cleaning up temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type d -name ".mypy_cache" -delete
	find . -type d -name ".ruff_cache" -delete
	find . -type d -name "htmlcov" -delete
	find . -type f -name "coverage.xml" -delete
	find . -type f -name ".coverage" -delete
	cd apps/dashboard && yarn clean || true

clean-docker: ## Clean up Docker resources
	@echo "Cleaning up Docker resources..."
	docker-compose down -v
	docker system prune -f
	docker volume prune -f

# Security
security: ## Run security checks
	@echo "Running security checks..."
	bandit -r libs apps -f json -o bandit-report.json
	bandit -r libs apps
	safety check --json --output safety-report.json
	safety check
	@echo "Security checks completed!"

# Documentation
docs: ## Generate documentation
	@echo "Generating documentation..."
	pdoc --html libs --output-dir docs/api
	@echo "Documentation generated in docs/api/"

docs-serve: ## Serve documentation locally
	@echo "Serving documentation..."
	cd docs && python -m http.server 8001

# Release
release: ## Create a new release
	@echo "Creating new release..."
	@read -p "Enter version (e.g., v1.0.0): " version; \
	git tag -a $$version -m "Release $$version"; \
	git push origin $$version

# Health checks
health: ## Check service health
	@echo "Checking service health..."
	@echo "API Health:"
	@curl -s http://localhost:8000/health | jq . || echo "API not responding"
	@echo "Dashboard Health:"
	@curl -s http://localhost:3000/health || echo "Dashboard not responding"
	@echo "Database Health:"
	@docker-compose exec postgres pg_isready -U liquid_hive || echo "Database not responding"
	@echo "Redis Health:"
	@docker-compose exec redis redis-cli ping || echo "Redis not responding"

# Development workflow
dev-setup: install dev ## Complete development setup
	@echo "Development setup complete!"
	@echo "Run 'make dev' to start the development environment"

ci: lint test security ## Run CI pipeline locally
	@echo "CI pipeline completed successfully!"

# Environment management
env-dev: ## Set development environment
	@echo "Setting development environment..."
	export APP_ENV=development
	export DEBUG=true
	export DATABASE_URL=sqlite:///./dev_liquid_hive.db
	export REDIS_URL=redis://localhost:6379/0

env-prod: ## Set production environment
	@echo "Setting production environment..."
	export APP_ENV=production
	export DEBUG=false
	export DATABASE_URL=postgresql://liquid_hive:password@localhost:5432/liquid_hive
	export REDIS_URL=redis://localhost:6379/0