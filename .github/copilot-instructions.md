# Liquid Hive Upgrade - AI System Development Instructions

**CRITICAL**: Always follow these instructions first and fallback to additional search or bash commands only when the information here is incomplete or found to be in error.

## System Overview

Liquid Hive Upgrade is a multi-component AI system that combines cognitive agents, vector RAG, semantic caching, and real-time streaming capabilities. The system includes:

- **unified_runtime/** - FastAPI entry point serving requests with dynamic strategy selection
- **hivemind/** - Agent roles, training pipeline, retrieval, and self-improvement loops  
- **capsule_brain/** - Long-term memory, knowledge graph, and belief state management
- **frontend/** - TypeScript/React web interface with real-time chat
- **src/internet_agent_advanced/** - Enhanced web scraping tools with consent/challenge system
- **Infrastructure** - Docker, Helm, Redis, Neo4j, Qdrant, Prometheus/Grafana monitoring

## Bootstrap and Build Process

### CRITICAL TIMING WARNINGS
- **NEVER CANCEL** builds or long-running commands. All timing below includes 50% safety buffer.
- Set timeouts to 300+ seconds for builds, 180+ seconds for tests
- Complete bootstrap takes 5+ minutes. Full validation takes 10+ minutes.

### 1. Initial Setup (3-5 minutes total)
```bash
# Install Python dependencies - NEVER CANCEL: Takes 3+ minutes
make install

# Install linting tools (required for validation)
pip install ruff black isort pytest pytest-asyncio

# Verify Python setup
python --version  # Should be 3.11+
```

### 2. Frontend Build (1-2 minutes total)
```bash
cd frontend

# NEVER CANCEL: npm install takes 30+ seconds
npm ci

# NEVER CANCEL: Build takes 20+ seconds  
npm run build

cd ..
```

### 3. Validation Commands (Always run before making changes)
```bash
# Fast unit tests - NEVER CANCEL: 15+ seconds
make test

# Linting validation - 5 seconds
make lint

# OpenAPI export - 10 seconds
make openapi

# Full test suite (optional) - NEVER CANCEL: 30+ seconds
pytest tests/ -q
```

## Running the Application

### Development Mode (Local)
```bash
# Start with Python path configured
PYTHONPATH=src python -m unified_runtime.__main__

# Application will start on http://localhost:8000
# Expect warnings about missing Redis/models - this is normal for dev mode
```

### Full Stack with Docker Compose
```bash
# Start infrastructure services - NEVER CANCEL: 60+ seconds first time
docker compose up redis prometheus qdrant neo4j --build

# In separate terminal, start main application
PYTHONPATH=src python -m unified_runtime.__main__
```

### Production Docker Build
```bash
# NEVER CANCEL: Full build takes 10+ minutes including frontend
make docker-build

# Run built container
make docker-run
```

## Essential Validation Scenarios

**ALWAYS** test these scenarios after making changes to ensure functionality:

### 1. Health and Basic API Validation
```bash
# Start application first, then test:
curl http://localhost:8000/api/healthz
# Expected: {"ok":true}

curl http://localhost:8000/metrics | head -5
# Expected: Prometheus metrics with cb_* prefixed counters

curl -s http://localhost:8000/docs
# Expected: Interactive API documentation (Swagger UI)
```

### 2. Chat System Validation (requires API keys)
```bash
# Basic chat test (will timeout without API keys but should not error)
timeout 10 curl -X POST "http://localhost:8000/api/chat?q=Hello" || echo "Timeout expected without API keys"

# With API keys configured:
curl -X POST "http://localhost:8000/api/chat?q=What is the capital of France?"
# Expected: JSON response with structured answer
```

### 3. Training System Validation
```bash
# Bootstrap training (requires model access)
PYTHONPATH=src python -m hivemind.training.bootstrap

# Check adapter management
curl http://localhost:8000/api/adapters
# Expected: JSON with adapter status and deployments
```

### 4. Frontend Validation
```bash
# After building frontend, check static files
ls frontend/dist/
# Expected: index.html, assets/, built CSS/JS files

# Test with browser or curl
curl -s http://localhost:8000/ | grep -i "Liquid Hive"
# Expected: HTML content with application title
```

## Development Workflow

### Making Code Changes
1. **Always** run validation commands first:
   ```bash
   make test && make lint
   ```

2. **Never** commit without formatting:
   ```bash
   make format
   ```

3. **Always** test your changes with a complete restart:
   ```bash
   # Stop app, restart, validate endpoints
   PYTHONPATH=src python -m unified_runtime.__main__
   curl http://localhost:8000/api/healthz
   ```

### Pre-commit Validation Checklist
- [ ] `make test` passes (15+ seconds)
- [ ] `make lint` shows no errors (5 seconds) 
- [ ] `make format` applied (10 seconds)
- [ ] Frontend builds without errors: `cd frontend && npm run build` (20+ seconds)
- [ ] Application starts successfully and `/api/healthz` returns `{"ok":true}`
- [ ] Key endpoints respond without errors (see validation scenarios above)

## Common Issues and Solutions

### Build Problems
- **SSL certificate errors in Docker**: Use `docker build --no-cache` or check network settings
- **Missing dependencies**: Run `make install` again with fresh environment
- **Frontend build failures**: Clear `node_modules` and run `npm ci` again

### Runtime Issues  
- **Redis connection failed**: Start with `docker compose up redis` first
- **Model provider errors**: Configure API keys in `.env` file (never commit secrets)
- **Import errors**: Ensure `PYTHONPATH=src` is set

### Test Failures
- **Circular import in internet_agent_advanced**: Skip these tests, known issue
- **Missing external services**: Many tests require Redis/databases - this is expected

## API Key Configuration

Create `.env` file (never commit this):
```bash
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_R1_API_KEY=your_r1_key_here  
OPENAI_API_KEY=your_openai_key_here
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333
NEO4J_URL=bolt://localhost:7687
```

## Timeout Reference

Use these timeout values in your commands:

| Command | Timeout | Description |
|---------|---------|-------------|
| `make install` | 300s | Python dependency installation |
| `make test` | 60s | Fast unit test suite |
| `pytest tests/` | 180s | Full test suite |
| `npm ci` | 120s | Frontend dependency installation |
| `npm run build` | 180s | Frontend build process |
| `make docker-build` | 900s | Complete Docker image build |
| `docker compose up` | 300s | Multi-service startup |

## Key File Locations

- Main server: `src/unified_runtime/server.py`
- Training scripts: `src/hivemind/training/`
- Frontend source: `frontend/src/`
- Configuration: `config/`
- Documentation: `docs/`
- Helm charts: `helm/`
- CI/CD workflows: `.github/workflows/`

## Production Deployment

For Kubernetes deployment:
```bash
# Helm installation
make helm-install IMAGE_REPO=ghcr.io/your-org/liquid-hive IMAGE_TAG=latest

# Health check in cluster
kubectl get pods -l app=liquid-hive
kubectl logs -l app=liquid-hive --tail=50
```

**REMEMBER**: This system processes sensitive data and connects to external APIs. Always validate security configurations and never commit secrets to version control.