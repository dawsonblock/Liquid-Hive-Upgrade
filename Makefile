# Liquid Hive minimal build
.PHONY: help install run dev dev-stop docker-build docker-push clean status

.DEFAULT_GOAL := help

# Colors
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
RED := \033[0;31m
NC := \033[0m

# Build configuration
DOCKER_REGISTRY ?= ghcr.io
IMAGE_NAME ?= liquid-hive
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")

help: ## Show help
	@echo "$(BLUE)Liquid Hive Minimal Build$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install Python dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	pip3 install --upgrade pip
	pip3 install -r requirements.txt
	@echo "$(GREEN)✅ Dependencies installed$(NC)"

run: ## Run API locally (uvicorn)
	uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

dev: ## Start API via Docker Compose
	docker compose up -d --build

dev-stop: ## Stop Docker Compose
	docker compose down

docker-build: ## Build API Docker image
	docker build -f apps/api/Dockerfile -t $(DOCKER_REGISTRY)/$(IMAGE_NAME)-api:$(VERSION) .

docker-push: ## Push API Docker image
	docker push $(DOCKER_REGISTRY)/$(IMAGE_NAME)-api:$(VERSION)

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .mypy_cache htmlcov .coverage coverage.xml logs || true

status: ## Show basic status
	@echo "$(BLUE)Status$(NC)"
	@echo "Version: $(VERSION)"
	@docker compose ps || true
