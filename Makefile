# =============================================================================
# Liquid-Hive-Upgrade Makefile
# Comprehensive development and operations targets
# =============================================================================

.PHONY: help install test lint format build clean docker helm docs deploy

# Default target
.DEFAULT_GOAL := help

# Configuration
PYTHON_VERSION := 3.11
PROJECT_NAME := liquid-hive-upgrade
DOCKER_REGISTRY := ghcr.io/liquid-hive
DOCKER_IMAGE := $(DOCKER_REGISTRY)/$(PROJECT_NAME)
HELM_NAMESPACE := liquid-hive

# Colors for output
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
BLUE := \033[34m
RESET := \033[0m

# =============================================================================
# Help Target
# =============================================================================
help: ## Show this help message
	@echo "$(BLUE)Liquid-Hive-Upgrade Development Commands$(RESET)"
	@echo "=============================================="
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*?##/ { printf "$(GREEN)%-20s$(RESET) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# =============================================================================
# Development Setup
# =============================================================================
install: ## Install development dependencies
	@echo "$(YELLOW)Installing Python dependencies...$(RESET)"
	pip install --upgrade pip setuptools wheel
	pip install -r requirements.txt
	@echo "$(YELLOW)Installing pre-commit hooks...$(RESET)"
	pre-commit install
	@echo "$(YELLOW)Installing frontend dependencies...$(RESET)"
	cd frontend && yarn install --frozen-lockfile
	@echo "$(GREEN)Development setup complete!$(RESET)"

install-dev: ## Install additional development tools
	@echo "$(YELLOW)Installing development tools...$(RESET)"
	pip install black ruff mypy bandit vulture radon
	@echo "$(GREEN)Development tools installed!$(RESET)"

# =============================================================================
# Code Quality
# =============================================================================
lint: ## Run all linting checks
	@echo "$(YELLOW)Running Python linting...$(RESET)"
	ruff check src/ tests/ --output-format=github
	@echo "$(YELLOW)Running MyPy type checking...$(RESET)"
	mypy src/ --ignore-missing-imports --show-error-codes
	@echo "$(YELLOW)Running frontend linting...$(RESET)"
	cd frontend && yarn lint
	@echo "$(GREEN)Linting complete!$(RESET)"

format: ## Format code with ruff and prettier
	@echo "$(YELLOW)Formatting Python code...$(RESET)"
	ruff format src/ tests/
	ruff check src/ tests/ --fix
	@echo "$(YELLOW)Formatting frontend code...$(RESET)"
	cd frontend && yarn format
	@echo "$(GREEN)Code formatting complete!$(RESET)"

security: ## Run security analysis
	@echo "$(YELLOW)Running Bandit security analysis...$(RESET)"
	bandit -r src/ -f json -o bandit-report.json || true
	@echo "$(YELLOW)Running secrets detection...$(RESET)"
	detect-secrets scan --baseline .secrets.baseline || true
	@echo "$(GREEN)Security analysis complete!$(RESET)"

complexity: ## Analyze code complexity
	@echo "$(YELLOW)Analyzing code complexity...$(RESET)"
	radon cc src/ -a -nb
	radon mi src/ -s
	vulture src/ --min-confidence 80
	@echo "$(GREEN)Complexity analysis complete!$(RESET)"

# =============================================================================
# Testing
# =============================================================================
test: ## Run all tests
	@echo "$(YELLOW)Running Python tests...$(RESET)"
	pytest -v --cov=src --cov-report=term-missing --cov-report=html tests/
	@echo "$(YELLOW)Running frontend tests...$(RESET)"
	cd frontend && yarn test --coverage --watchAll=false
	@echo "$(GREEN)All tests complete!$(RESET)"

test-unit: ## Run unit tests only
	@echo "$(YELLOW)Running unit tests...$(RESET)"
	pytest -v -m "not integration" tests/
	@echo "$(GREEN)Unit tests complete!$(RESET)"

test-integration: ## Run integration tests only
	@echo "$(YELLOW)Running integration tests...$(RESET)"
	pytest -v -m integration tests/
	@echo "$(GREEN)Integration tests complete!$(RESET)"

test-parallel: ## Run tests in parallel
	@echo "$(YELLOW)Running tests in parallel...$(RESET)"
	pytest -v -n auto --cov=src tests/
	@echo "$(GREEN)Parallel tests complete!$(RESET)"

# =============================================================================
# Build and Package
# =============================================================================
build: ## Build the application
	@echo "$(YELLOW)Building frontend...$(RESET)"
	cd frontend && yarn build
	@echo "$(YELLOW)Building Python package...$(RESET)"
	python -m build
	@echo "$(GREEN)Build complete!$(RESET)"

clean: ## Clean build artifacts
	@echo "$(YELLOW)Cleaning build artifacts...$(RESET)"
	rm -rf build/ dist/ *.egg-info/
	rm -rf frontend/dist/ frontend/build/
	rm -rf .coverage htmlcov/ .pytest_cache/
	rm -rf .mypy_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Clean complete!$(RESET)"

# =============================================================================
# Docker Operations
# =============================================================================
docker-build: ## Build Docker image
	@echo "$(YELLOW)Building Docker image...$(RESET)"
	docker build -t $(DOCKER_IMAGE):latest .
	@echo "$(GREEN)Docker image built: $(DOCKER_IMAGE):latest$(RESET)"

docker-build-dev: ## Build Docker image for development
	@echo "$(YELLOW)Building development Docker image...$(RESET)"
	docker build --target runtime -t $(DOCKER_IMAGE):dev .
	@echo "$(GREEN)Development Docker image built: $(DOCKER_IMAGE):dev$(RESET)"

docker-push: ## Push Docker image to registry
	@echo "$(YELLOW)Pushing Docker image...$(RESET)"
	docker push $(DOCKER_IMAGE):latest
	@echo "$(GREEN)Docker image pushed!$(RESET)"

docker-run: ## Run Docker container locally
	@echo "$(YELLOW)Running Docker container...$(RESET)"
	docker run -p 8000:8000 --env-file .env $(DOCKER_IMAGE):latest

# =============================================================================
# Docker Compose Operations
# =============================================================================
up: ## Start all services with Docker Compose
	@echo "$(YELLOW)Starting services...$(RESET)"
	docker compose up -d
	@echo "$(GREEN)Services started!$(RESET)"

down: ## Stop all services
	@echo "$(YELLOW)Stopping services...$(RESET)"
	docker compose down
	@echo "$(GREEN)Services stopped!$(RESET)"

up-dev: ## Start services for development
	@echo "$(YELLOW)Starting development services...$(RESET)"
	docker compose --profile dev up -d
	@echo "$(GREEN)Development services started!$(RESET)"

logs: ## Show service logs
	docker compose logs -f

# =============================================================================
# Kubernetes Operations
# =============================================================================
helm-validate: ## Validate Helm chart
	@echo "$(YELLOW)Validating Helm chart...$(RESET)"
	helm lint helm/
	helm template test helm/ --dry-run
	@echo "$(GREEN)Helm chart validation complete!$(RESET)"

helm-install: ## Install Helm chart
	@echo "$(YELLOW)Installing Helm chart...$(RESET)"
	helm upgrade --install $(PROJECT_NAME) helm/ --namespace $(HELM_NAMESPACE) --create-namespace
	@echo "$(GREEN)Helm chart installed!$(RESET)"

helm-uninstall: ## Uninstall Helm chart
	@echo "$(YELLOW)Uninstalling Helm chart...$(RESET)"
	helm uninstall $(PROJECT_NAME) --namespace $(HELM_NAMESPACE)
	@echo "$(GREEN)Helm chart uninstalled!$(RESET)"

k8s-deploy: ## Deploy to Kubernetes
	@echo "$(YELLOW)Deploying to Kubernetes...$(RESET)"
	kubectl apply -f k8s/
	@echo "$(GREEN)Kubernetes deployment complete!$(RESET)"

# =============================================================================
# Documentation
# =============================================================================
docs: ## Generate documentation
	@echo "$(YELLOW)Generating documentation...$(RESET)"
	python scripts/export_openapi.py
	@echo "$(GREEN)Documentation generated!$(RESET)"

docs-serve: ## Serve documentation locally
	@echo "$(YELLOW)Serving documentation...$(RESET)"
	python -m http.server 8080 --directory docs/

# =============================================================================
# CI/CD Operations
# =============================================================================
ci-test: ## Run CI pipeline tests locally
	@echo "$(YELLOW)Running CI pipeline tests...$(RESET)"
	$(MAKE) lint
	$(MAKE) security
	$(MAKE) test
	$(MAKE) docker-build
	@echo "$(GREEN)CI pipeline tests complete!$(RESET)"

release: ## Create a release
	@echo "$(YELLOW)Creating release...$(RESET)"
	$(MAKE) clean
	$(MAKE) test
	$(MAKE) build
	$(MAKE) docker-build
	$(MAKE) docker-push
	@echo "$(GREEN)Release complete!$(RESET)"

# =============================================================================
# Development Utilities
# =============================================================================
check: ## Run all quality checks
	@echo "$(YELLOW)Running comprehensive quality checks...$(RESET)"
	$(MAKE) lint
	$(MAKE) security
	$(MAKE) complexity
	$(MAKE) test-unit
	@echo "$(GREEN)Quality checks complete!$(RESET)"

pre-commit: ## Run pre-commit hooks on all files
	@echo "$(YELLOW)Running pre-commit hooks...$(RESET)"
	pre-commit run --all-files
	@echo "$(GREEN)Pre-commit hooks complete!$(RESET)"

update-deps: ## Update dependencies
	@echo "$(YELLOW)Updating Python dependencies...$(RESET)"
	pip-compile --upgrade requirements.in
	@echo "$(YELLOW)Updating frontend dependencies...$(RESET)"
	cd frontend && yarn upgrade
	@echo "$(GREEN)Dependencies updated!$(RESET)"

# =============================================================================
# Environment Management
# =============================================================================
env-create: ## Create development environment file
	@echo "$(YELLOW)Creating .env file from template...$(RESET)"
	cp .env.example .env
	@echo "$(GREEN).env file created! Please configure your environment variables.$(RESET)"

env-validate: ## Validate environment configuration
	@echo "$(YELLOW)Validating environment configuration...$(RESET)"
	python -c "from src.unified_runtime.server import app; print('✅ Environment configuration is valid')"

# =============================================================================
# Performance and Benchmarking
# =============================================================================
benchmark: ## Run performance benchmarks
	@echo "$(YELLOW)Running performance benchmarks...$(RESET)"
	pytest --benchmark-only tests/
	@echo "$(GREEN)Benchmarks complete!$(RESET)"

profile: ## Profile application performance
	@echo "$(YELLOW)Profiling application...$(RESET)"
	python -m cProfile -o profile.stats scripts/profile_app.py
	@echo "$(GREEN)Profiling complete! Check profile.stats$(RESET)"

# =============================================================================
# Monitoring and Health Checks
# =============================================================================
health: ## Check application health
	@echo "$(YELLOW)Checking application health...$(RESET)"
	curl -f http://localhost:8000/api/health || echo "❌ Health check failed"
	@echo "$(GREEN)Health check complete!$(RESET)"

metrics: ## Show application metrics
	@echo "$(YELLOW)Fetching metrics...$(RESET)"
	curl -s http://localhost:8000/metrics | head -20

# =============================================================================
# Database Operations
# =============================================================================
db-migrate: ## Run database migrations
	@echo "$(YELLOW)Running database migrations...$(RESET)"
	python scripts/migrate_db.py
	@echo "$(GREEN)Database migrations complete!$(RESET)"

db-seed: ## Seed database with test data
	@echo "$(YELLOW)Seeding database...$(RESET)"
	python scripts/seed_db.py
	@echo "$(GREEN)Database seeding complete!$(RESET)"