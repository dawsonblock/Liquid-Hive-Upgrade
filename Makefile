# Liquid Hive Build System
.PHONY: help install dev build test clean lint deploy status

.DEFAULT_GOAL := help

# Colors
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m

help: ## Show help
	@echo "$(BLUE)Liquid Hive Build System$(NC)"
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	pip3 install -r requirements.txt
	cd frontend && yarn install --frozen-lockfile
	@echo "$(GREEN)✅ Dependencies installed$(NC)"

dev: ## Start development environment
	@echo "$(BLUE)Starting development...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✅ Development environment started$(NC)"

dev-stop: ## Stop development environment
	docker-compose down
	@echo "$(GREEN)✅ Development environment stopped$(NC)"

build: ## Build all components
	@echo "$(BLUE)Building components...$(NC)"
	cd frontend && yarn build
	docker build -f apps/api/Dockerfile -t liquid-hive-api .
	@echo "$(GREEN)✅ Build completed$(NC)"

test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	python3 -m pytest tests/ -v
	cd frontend && yarn test --watchAll=false
	@echo "$(GREEN)✅ Tests completed$(NC)"

lint: ## Run linting
	@echo "$(BLUE)Running linting...$(NC)"
	ruff check . --output-format=github
	cd frontend && yarn lint
	@echo "$(GREEN)✅ Linting completed$(NC)"

clean: ## Clean build artifacts
	@echo "$(BLUE)Cleaning...$(NC)"
	./cleanup.sh
	@echo "$(GREEN)✅ Cleanup completed$(NC)"

status: ## Show system status
	@echo "$(BLUE)System Status$(NC)"
	@echo "Python: $(shell python3 --version)"
	@echo "Node: $(shell node --version 2>/dev/null || echo 'Not installed')"
	@echo "Docker: $(shell docker --version 2>/dev/null || echo 'Not installed')"
	@docker-compose ps 2>/dev/null || echo "Services not running"

logs: ## Show logs
	docker-compose logs -f

deploy: ## Deploy to staging
	@echo "$(BLUE)Deploying...$(NC)"
	helm upgrade --install liquid-hive infra/helm/liquid-hive
	@echo "$(GREEN)✅ Deployed$(NC)"
