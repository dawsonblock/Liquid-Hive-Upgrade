.PHONY: help dev-setup install test lint format security-scan type-check clean docs docker-build docker-run docker-clean

# Default target
help: ## Show this help message
	@echo "🧠 Liquid-Hive Development Commands"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development setup
dev-setup: ## Full development environment setup
	@echo "🚀 Setting up development environment..."
	@python -m venv .venv || python3 -m venv .venv
	@echo "📦 Installing Python dependencies..."
	@. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt
	@echo "📦 Installing frontend dependencies..."
	@cd frontend && yarn install --frozen-lockfile
	@echo "🏗️  Building frontend..."
	@cd frontend && yarn build
	@echo "✅ Development setup complete!"
	@echo ""
	@echo "🎯 Next steps:"
	@echo "  1. Activate virtual environment: source .venv/bin/activate"
	@echo "  2. Start services: docker-compose up --build"
	@echo "  3. Visit: http://localhost:3000 (frontend) or http://localhost:8000/docs (API)"

install: ## Install all dependencies
	@echo "📦 Installing dependencies..."
	@. .venv/bin/activate && pip install -r requirements.txt
	@cd frontend && yarn install --frozen-lockfile

# Testing
test: ## Run all tests (Python + Node.js)
	@echo "🧪 Running all tests..."
	@echo "Backend tests:"
	@. .venv/bin/activate && pytest tests/ -v --cov=src --cov-report=term-missing
	@echo ""
	@echo "Frontend tests:"
	@cd frontend && yarn test --ci --watchAll=false

test-python: ## Run Python tests only
	@. .venv/bin/activate && pytest tests/ -v --cov=src --cov-report=term-missing

test-frontend: ## Run frontend tests only
	@cd frontend && yarn test --ci --watchAll=false

test-smoke: ## Run smoke tests
	@. .venv/bin/activate && python tests/test_smoke.py

# Code quality
lint: ## Run all linters
	@echo "🔍 Running linters..."
	@echo "Python (ruff):"
	@. .venv/bin/activate && ruff check src/ tests/
	@echo ""
	@echo "Frontend (eslint):"
	@cd frontend && yarn lint

lint-fix: ## Auto-fix linting issues
	@echo "🔧 Auto-fixing linting issues..."
	@. .venv/bin/activate && ruff check --fix src/ tests/
	@cd frontend && yarn lint:fix

format: ## Auto-format all code
	@echo "🎨 Formatting code..."
	@. .venv/bin/activate && ruff format src/ tests/
	@cd frontend && yarn format

format-check: ## Check code formatting
	@echo "🎨 Checking code formatting..."
	@. .venv/bin/activate && ruff format --check src/ tests/
	@cd frontend && yarn format:check

type-check: ## Run type checking (mypy)
	@echo "🔍 Type checking..."
	@. .venv/bin/activate && mypy src/

# Security
security-scan: ## Run security analysis (bandit)
	@echo "🛡️  Running security scan..."
	@. .venv/bin/activate && bandit -r src/ -f json -o bandit-report.json
	@echo "Security report generated: bandit-report.json"
	@cd frontend && yarn audit

# Cleanup
clean: ## Clean build artifacts
	@echo "🧹 Cleaning build artifacts..."
	@rm -rf build/ dist/ .coverage htmlcov/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	@rm -rf frontend/dist/ frontend/.next/ frontend/coverage/ frontend/node_modules/.cache/
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete
	@find . -name "*.pyo" -delete
	@find . -name "*.pyd" -delete
	@find . -name "*.db" -delete
	@find . -name "*.log" -delete
	@find . -name "*.tmp" -delete
	@echo "✅ Cleanup complete!"

# Documentation
docs: ## Build documentation
	@echo "📚 Building documentation..."
	@. .venv/bin/activate && mkdocs build --clean

docs-serve: ## Serve documentation locally
	@echo "📚 Serving documentation at http://localhost:8080..."
	@. .venv/bin/activate && mkdocs serve

# Docker
docker-build: ## Build production Docker image
	@echo "🐳 Building Docker image..."
	@docker build -t liquid-hive:latest .
	@docker build -t liquid-hive:dev -f Dockerfile.dev .

docker-run: ## Run in Docker
	@echo "🐳 Running Docker container..."
	@docker-compose up --build

docker-clean: ## Clean Docker resources
	@echo "🐳 Cleaning Docker resources..."
	@docker-compose down --volumes --remove-orphans
	@docker system prune -f

# Database
db-migrate: ## Run database migrations
	@echo "💾 Running database migrations..."
	@. .venv/bin/activate && python scripts/migrate.py

db-seed: ## Seed database with sample data
	@echo "🌱 Seeding database..."
	@. .venv/bin/activate && python scripts/seed_data.py

# Development utilities
start-backend: ## Start backend development server
	@echo "🚀 Starting backend server..."
	@. .venv/bin/activate && cd src && python -m uvicorn unified_runtime.server:app --reload --host 0.0.0.0 --port 8000

start-frontend: ## Start frontend development server
	@echo "🚀 Starting frontend server..."
	@cd frontend && yarn dev

start-services: ## Start all supporting services (Redis, Neo4j, etc.)
	@echo "🚀 Starting supporting services..."
	@docker-compose up redis neo4j qdrant prometheus grafana

# Deployment
build-prod: ## Build production artifacts
	@echo "🏭 Building production artifacts..."
	@cd frontend && yarn build
	@. .venv/bin/activate && python -m build

release-check: ## Check if ready for release
	@echo "✅ Checking release readiness..."
	@make test
	@make lint
	@make security-scan
	@make type-check
	@echo "🎉 Ready for release!"

# Quick development commands
quick-start: ## Quick start for development
	@echo "⚡ Quick starting development environment..."
	@docker-compose up -d redis neo4j qdrant
	@sleep 5
	@make start-backend &
	@make start-frontend &
	@echo "🎯 Development servers started!"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Backend:  http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"

stop: ## Stop all development servers
	@echo "🛑 Stopping development servers..."
	@docker-compose down
	@pkill -f "uvicorn" || true
	@pkill -f "vite" || true
	@echo "✅ All servers stopped!"