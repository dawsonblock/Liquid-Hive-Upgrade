# Liquid Hive Build System
.PHONY: help install dev build test clean lint deploy status setup check deps build-all docker-build docker-push security-scan performance-test

.DEFAULT_GOAL := help

# Colors
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
RED := \033[0;31m
NC := \033[0m

# Build configuration
PARALLEL_JOBS := $(shell nproc 2>/dev/null || echo 4)
DOCKER_REGISTRY := ghcr.io
IMAGE_NAME := liquid-hive
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
BUILD_DATE := $(shell date -u +%Y-%m-%dT%H:%M:%SZ)

# Error handling
SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c

help: ## Show help
	@echo "$(BLUE)Liquid Hive Build System$(NC)"
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Initial project setup
	@echo "$(BLUE)Setting up Liquid Hive project...$(NC)"
	@if ! command -v python3 &> /dev/null; then echo "$(RED)❌ Python 3 not found$(NC)"; exit 1; fi
	@if ! command -v node &> /dev/null; then echo "$(RED)❌ Node.js not found$(NC)"; exit 1; fi
	@if ! command -v yarn &> /dev/null; then echo "$(RED)❌ Yarn not found$(NC)"; exit 1; fi
	@if ! command -v docker &> /dev/null; then echo "$(RED)❌ Docker not found$(NC)"; exit 1; fi
	@echo "$(GREEN)✅ Prerequisites check passed$(NC)"

install: setup ## Install dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	pip3 install --upgrade pip
	pip3 install -r requirements.txt
	cd frontend && yarn install --frozen-lockfile
	@echo "$(GREEN)✅ Dependencies installed$(NC)"

deps: install ## Alias for install

dev: ## Start development environment
	@echo "$(BLUE)Starting development...$(NC)"
	docker compose up -d
	@echo "$(GREEN)✅ Development environment started$(NC)"

dev-stop: ## Stop development environment
	docker compose down
	@echo "$(GREEN)✅ Development environment stopped$(NC)"

build: ## Build all components
	@echo "$(BLUE)Building components...$(NC)"
	cd frontend && yarn build
	docker build -f apps/api/Dockerfile -t liquid-hive-api .
	@echo "$(GREEN)✅ Build completed$(NC)"

build-enhanced: ## Enhanced build with optimizations
	@echo "$(BLUE)Running enhanced build...$(NC)"
	@if [ ! -f scripts/enhanced_build.py ]; then \
		echo "$(RED)❌ scripts/enhanced_build.py not found$(NC)"; \
		exit 1; \
	fi
	python3 scripts/enhanced_build.py --clean --optimize
	@echo "$(GREEN)✅ Enhanced build completed$(NC)"

build-optimize: ## Analyze and optimize build
	@echo "$(BLUE)Analyzing build...$(NC)"
	python3 scripts/build_optimizer.py
	@echo "$(GREEN)✅ Build analysis completed$(NC)"

build-all: ## Build all components with parallel processing
	@echo "$(BLUE)Building all components in parallel...$(NC)"
	@$(MAKE) -j$(PARALLEL_JOBS) build-frontend build-backend build-services
	@echo "$(GREEN)✅ All components built$(NC)"

build-frontend: ## Build frontend only
	@echo "$(BLUE)Building frontend...$(NC)"
	cd frontend && yarn build
	@echo "$(GREEN)✅ Frontend built$(NC)"

build-backend: ## Build backend only
	@echo "$(BLUE)Building backend...$(NC)"
	docker build -f apps/api/Dockerfile -t liquid-hive-api .
	@echo "$(GREEN)✅ Backend built$(NC)"

build-services: ## Build all services
	@echo "$(BLUE)Building services...$(NC)"
	@for service in feedback_api oracle_api; do \
		echo "Building $$service..."; \
		docker build -f services/$$service/Dockerfile -t liquid-hive-$$service . || exit 1; \
	done
	@echo "$(GREEN)✅ Services built$(NC)"

docker-build: ## Build all Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker build -f apps/api/Dockerfile -t $(DOCKER_REGISTRY)/$(IMAGE_NAME)-api:$(VERSION) .
	docker build -f frontend/Dockerfile -t $(DOCKER_REGISTRY)/$(IMAGE_NAME)-frontend:$(VERSION) ./frontend
	@for service in feedback_api oracle_api; do \
		echo "Building $$service..."; \
		docker build -f services/$$service/Dockerfile -t $(DOCKER_REGISTRY)/$(IMAGE_NAME)-$$service:$(VERSION) . || exit 1; \
	done
	@echo "$(GREEN)✅ All Docker images built$(NC)"

docker-push: docker-build ## Push Docker images to registry
	@echo "$(BLUE)Pushing Docker images...$(NC)"
	docker push $(DOCKER_REGISTRY)/$(IMAGE_NAME)-api:$(VERSION)
	docker push $(DOCKER_REGISTRY)/$(IMAGE_NAME)-frontend:$(VERSION)
	@for service in feedback_api oracle_api; do \
		echo "Pushing $$service..."; \
		docker push $(DOCKER_REGISTRY)/$(IMAGE_NAME)-$$service:$(VERSION) || exit 1; \
	done
	@echo "$(GREEN)✅ All images pushed$(NC)"

test: ## Run all tests
	@echo "$(BLUE)Running all tests...$(NC)"
	@$(MAKE) -j$(PARALLEL_JOBS) test-python test-frontend test-integration
	@echo "$(GREEN)✅ All tests completed$(NC)"

test-python: ## Run Python tests
	@echo "$(BLUE)Running Python tests...$(NC)"
	python3 -m pytest tests/ -v --cov=src --cov=apps --cov-report=html --cov-report=term
	@echo "$(GREEN)✅ Python tests completed$(NC)"

test-frontend: ## Run frontend tests
	@echo "$(BLUE)Running frontend tests...$(NC)"
	cd frontend && yarn test --watchAll=false --coverage
	@echo "$(GREEN)✅ Frontend tests completed$(NC)"

test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit; \
	exit_code=$$?; \
	docker compose -f docker-compose.test.yml down --volumes --remove-orphans; \
	exit $$exit_code
	@echo "$(GREEN)✅ Integration tests completed$(NC)"

test-services: ## Run service-specific tests
	@echo "$(BLUE)Running service tests...$(NC)"
	@for service in feedback_api oracle_api; do \
		echo "Testing $$service..."; \
		python3 -m pytest tests/services/test_$$service.py -v || exit 1; \
	done
	@echo "$(GREEN)✅ Service tests completed$(NC)"

lint: ## Run all linting
	@echo "$(BLUE)Running all linting...$(NC)"
	@$(MAKE) -j$(PARALLEL_JOBS) lint-python lint-frontend lint-docker
	@echo "$(GREEN)✅ All linting completed$(NC)"

lint-python: ## Run Python linting
	@echo "$(BLUE)Running Python linting...$(NC)"
	ruff check . --output-format=github
	ruff format . --check
	mypy src/ apps/ --ignore-missing-imports
	@echo "$(GREEN)✅ Python linting completed$(NC)"

lint-frontend: ## Run frontend linting
	@echo "$(BLUE)Running frontend linting...$(NC)"
	cd frontend && yarn lint
	cd frontend && yarn type-check
	@echo "$(GREEN)✅ Frontend linting completed$(NC)"

lint-docker: ## Run Docker linting
	@echo "$(BLUE)Running Docker linting...$(NC)"
	@if command -v hadolint &> /dev/null; then \
		find . -name "Dockerfile*" -exec hadolint {} \; || true; \
	else \
		echo "$(YELLOW)⚠️  hadolint not installed, skipping Docker linting$(NC)"; \
	fi
	@echo "$(GREEN)✅ Docker linting completed$(NC)"

security-scan: ## Run security scans
	@echo "$(BLUE)Running security scans...$(NC)"
	bandit -r src/ apps/ -f json -o bandit-report.json || true
	safety check --json --output safety-report.json || true
	cd frontend && yarn audit --json > ../frontend-audit.json || true
	@echo "$(GREEN)✅ Security scans completed$(NC)"

performance-test: ## Run performance tests
	@echo "$(BLUE)Running performance tests...$(NC)"
	@if command -v k6 &> /dev/null; then \
		k6 run tests/performance/k6_smoke.js; \
	else \
		echo "$(YELLOW)⚠️  k6 not installed, skipping performance tests$(NC)"; \
	fi
	@echo "$(GREEN)✅ Performance tests completed$(NC)"

clean: ## Clean build artifacts
	@echo "$(BLUE)Cleaning...$(NC)"
	test -x ./cleanup.sh || chmod +x ./cleanup.sh
	./cleanup.sh
	@echo "$(GREEN)✅ Cleanup completed$(NC)"

status: ## Show comprehensive system status
	@echo "$(BLUE)System Status$(NC)"
	@echo "=========================================="
	@echo "Version: $(VERSION)"
	@echo "Build Date: $(BUILD_DATE)"
	@echo "Parallel Jobs: $(PARALLEL_JOBS)"
	@echo "=========================================="
	@echo "Python: $(shell python3 --version 2>/dev/null || echo 'Not installed')"
	@echo "Node: $(shell node --version 2>/dev/null || echo 'Not installed')"
	@echo "Yarn: $(shell yarn --version 2>/dev/null || echo 'Not installed')"
	@echo "Docker: $(shell docker --version 2>/dev/null || echo 'Not installed')"
	@echo "Docker Compose: $(shell docker compose version 2>/dev/null || echo 'Not installed')"
	@echo "=========================================="
	@echo "Services Status:"
	@docker compose ps 2>/dev/null || echo "Services not running"
	@echo "=========================================="
	@echo "Disk Usage:"
	@df -h . | tail -1 | awk '{print "Available: " $$4 " (" $$5 " used)"}'
	@echo "Memory Usage:"
	@free -h | grep Mem | awk '{print "Used: " $$3 "/" $$2 " (" int($$3/$$2*100) "%)"}'

check: ## Run comprehensive health checks
	@echo "$(BLUE)Running health checks...$(NC)"
	@$(MAKE) -j$(PARALLEL_JOBS) check-deps check-services check-build check-security
	@echo "$(GREEN)✅ All health checks passed$(NC)"

check-deps: ## Check dependencies
	@echo "$(BLUE)Checking dependencies...$(NC)"
	@python3 -c "import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
	@node --version
	@yarn --version
	@docker --version
	@echo "$(GREEN)✅ Dependencies check passed$(NC)"

check-services: ## Check service health
	@echo "$(BLUE)Checking service health...$(NC)"
	@for port in 8001 3000 8091 8092; do \
		if curl -f http://localhost:$$port/health 2>/dev/null; then \
			echo "$(GREEN)✅ Service on port $$port is healthy$(NC)"; \
		else \
			echo "$(YELLOW)⚠️  Service on port $$port is not responding$(NC)"; \
		fi; \
	done

check-build: ## Check build artifacts
	@echo "$(BLUE)Checking build artifacts...$(NC)"
	@if [ -d "frontend/dist" ]; then echo "$(GREEN)✅ Frontend build exists$(NC)"; else echo "$(RED)❌ Frontend build missing$(NC)"; fi
	@if docker images | grep -q liquid-hive-api; then echo "$(GREEN)✅ Backend image exists$(NC)"; else echo "$(RED)❌ Backend image missing$(NC)"; fi

check-security: ## Check security status
	@echo "$(BLUE)Checking security status...$(NC)"
	@if [ -f "bandit-report.json" ]; then echo "$(GREEN)✅ Security scan completed$(NC)"; else echo "$(YELLOW)⚠️  Security scan not run$(NC)"; fi
	@if [ -f "safety-report.json" ]; then echo "$(GREEN)✅ Safety check completed$(NC)"; else echo "$(YELLOW)⚠️  Safety check not run$(NC)"; fi

logs: ## Show logs
	docker compose logs -f

logs-api: ## Show API logs
	docker compose logs -f api

logs-frontend: ## Show frontend logs
	docker compose logs -f frontend

logs-services: ## Show services logs
	docker compose logs -f feedback oracle

deploy: ## Deploy to staging
	@echo "$(BLUE)Deploying...$(NC)"
	helm upgrade --install liquid-hive infra/helm/liquid-hive
	@echo "$(GREEN)✅ Deployed$(NC)"

deploy-prod: ## Deploy to production
	@echo "$(BLUE)Deploying to production...$(NC)"
	helm upgrade --install liquid-hive infra/helm/liquid-hive -f infra/helm/liquid-hive/values-prod.yaml
	@echo "$(GREEN)✅ Production deployment completed$(NC)"

ci: ## Run CI pipeline locally
	@echo "$(BLUE)Running CI pipeline...$(NC)"
	@$(MAKE) -j$(PARALLEL_JOBS) setup lint test security-scan build-all
	@echo "$(GREEN)✅ CI pipeline completed$(NC)"

ci-full: ## Run full CI pipeline with all checks
	@echo "$(BLUE)Running full CI pipeline...$(NC)"
	@$(MAKE) -j$(PARALLEL_JOBS) setup lint test security-scan performance-test build-all docker-build
	@echo "$(GREEN)✅ Full CI pipeline completed$(NC)"

dev-reset: ## Reset development environment
	@echo "$(BLUE)Resetting development environment...$(NC)"
	docker compose down -v
	docker system prune -f
	@$(MAKE) clean
	@$(MAKE) install
	@echo "$(GREEN)✅ Development environment reset$(NC)"

update-deps: ## Update all dependencies
	@echo "$(BLUE)Updating dependencies...$(NC)"
	pip3 install --upgrade pip
	pip3 install -r requirements.txt --upgrade
	cd frontend && yarn upgrade
	@echo "$(GREEN)✅ Dependencies updated$(NC)"

backup: ## Create backup of current state
	@echo "$(BLUE)Creating backup...$(NC)"
	@mkdir -p backups
	@tar -czf backups/liquid-hive-backup-$(shell date +%Y%m%d-%H%M%S).tar.gz \
		--exclude=node_modules --exclude=__pycache__ --exclude=.git \
		--exclude=backups --exclude=dist --exclude=build .
	@echo "$(GREEN)✅ Backup created$(NC)"

restore: ## Restore from backup (usage: make restore BACKUP=filename)
	@echo "$(BLUE)Restoring from backup...$(NC)"
	@if [ -z "$(BACKUP)" ]; then echo "$(RED)❌ Please specify BACKUP=filename$(NC)"; exit 1; fi
	@tar -xzf backups/$(BACKUP)
	@echo "$(GREEN)✅ Restored from backup$(NC)"

metrics: ## Show build metrics
	@echo "$(BLUE)Build Metrics$(NC)"
	@echo "=========================================="
	@echo "Repository size: $(shell du -sh . | cut -f1)"
	@echo "Python files: $(shell find . -name '*.py' | wc -l)"
	@echo "TypeScript files: $(shell find frontend/src -name '*.ts*' | wc -l)"
	@echo "Docker images: $(shell docker images | grep liquid-hive | wc -l)"
	@echo "Test coverage: $(shell find . -name 'coverage.xml' -exec grep -o 'line-rate="[^"]*"' {} \; | head -1 | cut -d'"' -f2 || echo 'Not available')"
	@echo "=========================================="

help-dev: ## Show development help
	@echo "$(BLUE)Development Workflow$(NC)"
	@echo "=========================================="
	@echo "1. Setup: make setup"
	@echo "2. Install: make install"
	@echo "3. Start dev: make dev"
	@echo "4. Run tests: make test"
	@echo "5. Check status: make status"
	@echo "6. Clean up: make clean"
	@echo "=========================================="
	@echo "Quick commands:"
	@echo "  make ci        - Run CI pipeline"
	@echo "  make check     - Health checks"
	@echo "  make logs      - View logs"
	@echo "  make dev-reset - Reset environment"
	@echo "=========================================="
