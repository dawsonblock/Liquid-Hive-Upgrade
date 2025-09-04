SHELL := /bin/bash
.PHONY: test lint build clean install help

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*?##/ { printf "  %-15s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install: ## Install dependencies
	@echo "Installing Python dependencies..."
	@if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
	@if [ -f frontend/package.json ]; then cd frontend && yarn install; fi
	@echo "Installing pre-commit hooks..."
	@if command -v pre-commit >/dev/null 2>&1; then pre-commit install; fi

test: ## Run tests
	@echo "Running tests..."
	@if command -v pytest >/dev/null 2>&1; then \
		pytest -q --cov=src --cov-report=term-missing; \
	else \
		bash tests/test_smoke.sh || true; \
	fi

lint: ## Run linting
	@echo "Running linting..."
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check . --fix; \
		ruff format .; \
	else \
		echo "ruff not installed, skipping lint"; \
	fi
	@if command -v mypy >/dev/null 2>&1; then \
		mypy src/ --ignore-missing-imports || true; \
	fi

build: ## Build Docker image
	@echo "Building Docker image..."
	@docker build -t liquid-hive:local .

clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	@rm -rf build/ dist/ *.egg-info/
	@rm -rf .coverage htmlcov/ .pytest_cache/
	@rm -rf .mypy_cache/ .ruff_cache/
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

dev: ## Start development environment
	@echo "Starting development environment..."
	@docker compose --profile dev up -d

down: ## Stop development environment
	@echo "Stopping development environment..."
	@docker compose down

logs: ## Show service logs
	@docker compose logs -f

health: ## Check service health
	@curl -f http://localhost:8000/api/health || echo "Service not available"
