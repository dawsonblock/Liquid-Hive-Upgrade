# 🚀 Getting Started with Liquid Hive

**Quick 5-minute setup guide for the Liquid Hive AI Agent Platform**

## Prerequisites

- **Python 3.11+** (3.12 recommended)
- **Node.js 18+** (20 recommended) 
- **Yarn package manager**
- **Docker & Docker Compose** (for full stack)
- **Git**

## 🏃‍♂️ Quick Start (5 minutes)

### 1. Clone and Setup

```bash
# Clone repository
git clone <repository-url>
cd liquid-hive

# Copy environment template
cp .env.example .env

# Edit .env with your settings (minimal required: API keys)
nano .env
```

### 2. One-Command Development Setup

```bash
# Install all dependencies and start services
make dev-setup
make dev
```

**That's it!** 🎉 Services will be available at:

- **API**: http://localhost:8001
- **Frontend**: http://localhost:3000  
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090

### 3. Verify Installation

```bash
# Check service health
make health

# Run tests
make test

# Check code quality
make lint
```

## 📋 Development Workflow

### Daily Development Commands

```bash
# Start development environment
make dev                  # Full stack with hot reload

# Individual services  
make dev-api             # Backend API only
make dev-frontend        # Frontend only

# Testing
make test                # Full test suite
make test-unit           # Unit tests only
make test-integration    # Integration tests only

# Code Quality
make lint                # Run all linters
make format              # Format all code
make security            # Security checks

# Utilities
make clean               # Clean build artifacts
make logs                # View service logs
make status              # System status check
```

### Project Structure

```
liquid-hive/
├── src/                 # Core Python libraries
│   ├── hivemind/       # AI agent orchestration
│   ├── capsule_brain/  # Cognitive processing
│   ├── oracle/         # Decision systems  
│   └── config.py       # Configuration management
├── apps/
│   └── api/            # FastAPI backend service
├── frontend/           # React + TypeScript frontend
├── infra/              # Docker, Helm, monitoring configs
├── tests/              # Comprehensive test suites
└── docs/               # Documentation
```

## 🔧 Configuration

### Essential Environment Variables

Edit `.env` for these critical settings:

```bash
# API Keys (at least one required)
OPENAI_API_KEY="sk-..."
ANTHROPIC_API_KEY="sk-ant-..."
DEEPSEEK_API_KEY="sk-..."

# Database  
MONGO_URL="mongodb://localhost:27017/liquid_hive"

# Frontend Connection
REACT_APP_BACKEND_URL="http://localhost:8001"
```

### Feature Flags

Enable/disable major features in `.env`:

```bash
# Core Features
RAG_ENABLED=true
AGENT_AUTONOMY=true
SAFETY_CHECKS=true

# Phase 2 Features (implemented later)
FEEDBACK_LOOP_ENABLED=false  
ORACLE_SYSTEM_ENABLED=false
```

## 🐳 Docker Development

### Full Stack with Docker Compose

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### Services Included

- **liquid-hive-api**: Backend API server
- **liquid-hive-frontend**: React development server
- **prometheus**: Metrics collection
- **grafana**: Monitoring dashboards
- **redis**: Caching (optional)
- **qdrant**: Vector database (optional)

## 🧪 Testing

### Test Levels

```bash
# Unit Tests (fast, isolated)
pytest tests/unit/ -v

# Integration Tests (with services)
pytest tests/integration/ -v

# Performance Tests (k6 load testing)
k6 run tests/performance/k6_smoke.js

# Frontend Tests
cd frontend && yarn test
```

### Coverage Requirements

- **Python**: Minimum 80% coverage
- **Frontend**: Minimum 75% coverage
- **Integration**: All critical paths tested

## 📦 Building for Production

### Local Production Build

```bash
# Build optimized containers
make build-prod

# Generate release artifacts
make release
```

### Kubernetes Deployment

```bash
# Deploy to development cluster
make helm-apply

# Deploy to production
make helm-prod IMAGE_TAG=v1.0.0
```

## 🔍 Troubleshooting

### Common Issues

**Services won't start:**
```bash
# Check system status
make status

# View service logs  
make logs

# Reset environment
make clean && make dev-setup
```

**Import errors:**
```bash
# Ensure Python dependencies installed
pip install -r requirements.txt

# Check Python path
python -c "import src.config; print('✅ Imports work')"
```

**Frontend build fails:**
```bash
cd frontend
yarn install --frozen-lockfile
yarn build
```

### Getting Help

1. **Check logs**: `make logs` or `docker compose logs`
2. **Verify config**: Review `.env` file settings  
3. **Run health checks**: `make health`
4. **Clean rebuild**: `make clean && make dev-setup`

## 🎯 Next Steps

1. **Explore the API**: Visit http://localhost:8001/docs for interactive API documentation
2. **Try the Frontend**: Access the React interface at http://localhost:3000
3. **Monitor Services**: Use Grafana at http://localhost:3000 (admin/admin)
4. **Read Documentation**: Check `docs/` for architecture and advanced features
5. **Run Tests**: Ensure everything works with `make test`

## 🌟 Advanced Features (Coming in Phase 2)

- **Feedback Loop System**: Continuous learning from user interactions
- **Oracle Meta-Loop**: AI-driven system optimization and mutation
- **LoRA Hot-Plugging**: Dynamic model adaptation
- **Advanced Monitoring**: Comprehensive observability and alerting

---

**Happy Developing!** 🚀

For more detailed information, see:
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - System design
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md) - Production deployment
- [`CONTRIBUTING.md`](CONTRIBUTING.md) - Development guidelines