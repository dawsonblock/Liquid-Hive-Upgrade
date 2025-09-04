# 🧠 LIQUID-HIVE

[![CI](https://github.com/AetheronResearch/liquid-hive/workflows/CI/badge.svg)](https://github.com/AetheronResearch/liquid-hive/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![Node](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org)
[![Security](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)

> **Production-Ready AI Cognitive System** - A unified multi-agent reasoning platform with advanced memory, retrieval, and self-improvement capabilities.

## 🚀 Quick Start

**One-command deployment:**

```bash
# Development setup
git clone https://github.com/AetheronResearch/liquid-hive.git
cd liquid-hive
make dev-setup

# Production deployment
docker-compose up --build -d
```

**API Usage:**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the capital of France?"}'
```

## 🏗️ Architecture

Liquid-Hive is a production-grade cognitive system built on a microservices architecture:

### **Core Components**

- 🧠 **unified_runtime/** – FastAPI server with dynamic strategy selection
- 💾 **capsule_brain/** – Long-term memory and knowledge graph
- 🤖 **hivemind/** – Multi-agent reasoning core with specialized roles
- 📊 **Observability** – Prometheus metrics + Grafana dashboards
- 🌐 **Frontend** – React/TypeScript interface with real-time chat

### **Infrastructure Services**

| Service | Purpose | Port |
|---------|---------|------|
| FastAPI Backend | Core API | 8000 |
| React Frontend | Web Interface | 3000 |
| Redis | Message Bus | 6379 |
| Neo4j | Knowledge Graph | 7474 |
| Qdrant | Vector Database | 6333 |
| Prometheus | Metrics | 9090 |
| Grafana | Dashboards | 3030 |

## 📦 Installation

### **Prerequisites**

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- 8GB+ RAM (for AI models)

### **Development Setup**

```bash
# Clone and install
git clone https://github.com/AetheronResearch/liquid-hive.git
cd liquid-hive

# Backend setup
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup
cd frontend
yarn install --frozen-lockfile
yarn build

# Start services
docker-compose up --build
```

### **Production Docker**

```bash
# Build production image
docker build -t liquid-hive:latest .

# Deploy with compose
docker-compose -f docker-compose.prod.yml up -d
```

## 🔧 Development

### **Makefile Commands**

```bash
# Development
make dev-setup      # Full development environment setup
make install        # Install all dependencies
make test           # Run all tests (Python + Node.js)
make lint           # Run all linters
make format         # Auto-format all code

# Quality & Security
make security-scan  # Run security analysis (bandit)
make type-check     # Run type checking (mypy)
make clean          # Clean build artifacts
make docs           # Build documentation

# Docker
make docker-build   # Build production Docker image
make docker-run     # Run in Docker
make docker-clean   # Clean Docker resources
```

### **Project Structure**

```
liquid-hive/
├── 🚀 CI/CD & Config
│   ├── .github/workflows/     # GitHub Actions (CI/CD)
│   ├── .gitignore            # Git ignore rules
│   ├── Makefile              # Development commands
│   ├── docker-compose.yml    # Development services
│   └── Dockerfile            # Production container
│
├── 🧠 Core System
│   ├── src/                  # Python source code
│   │   ├── unified_runtime/  # FastAPI server
│   │   ├── capsule_brain/    # Memory & knowledge graph
│   │   ├── hivemind/         # Multi-agent reasoning
│   │   ├── oracle/           # Quality assurance
│   │   └── safety/           # Security & validation
│   │
│   ├── frontend/             # React TypeScript UI
│   │   ├── src/components/   # React components
│   │   ├── src/services/     # API clients
│   │   └── public/           # Static assets
│   │
├── 🗄️ Data & Config
│   ├── data/                 # RAG indices & storage
│   ├── config/               # Service configurations
│   ├── k8s/                  # Kubernetes manifests
│   └── helm/                 # Helm charts
│
├── 📊 Observability
│   ├── prometheus/           # Metrics collection
│   ├── grafana/             # Dashboards
│   └── docs/                # Documentation
│
└── 🧪 Testing
    ├── tests/               # Python tests
    └── scripts/             # Utility scripts
```

## 🔗 API Reference

### **Chat Endpoint**

```http
POST /api/chat
Content-Type: application/json

{
  "query": "What is quantum computing?",
  "strategy": "comprehensive",  # optional: "fast", "comprehensive", "creative"
  "context": "technical",       # optional context hint
  "max_tokens": 1000           # optional token limit
}
```

**Response:**
```json
{
  "response": "Quantum computing is...",
  "strategy_used": "comprehensive",
  "thinking_process": "...",
  "sources": ["doc1.pdf", "doc2.txt"],
  "confidence": 0.92,
  "processing_time_ms": 1500
}
```

### **Vision Analysis**

```http
POST /api/vision
Content-Type: multipart/form-data

question: "Describe this image"
file: [image.png]
grounding_required: false
```

### **Health Check**

```bash
curl http://localhost:8000/api/healthz
```

## 🧪 Testing

### **Quick Test**

```bash
# Backend tests
pytest tests/ -v --cov=src

# Frontend tests  
cd frontend && yarn test

# Integration tests
python tests/test_smoke.py
```

### **Manual Testing**

```bash
# Chat API
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the capital of France?"}'

# Vision API
curl -X POST "http://localhost:8000/api/vision" \
  -F "question=Describe this image" \
  -F "file=@/path/to/image.png" \
  -F "grounding_required=false"
```

## 📈 Performance & Monitoring

### **Metrics Dashboard**

Access Grafana at `http://localhost:3030` for:

- 📊 **Request Metrics** - Latency, throughput, error rates
- 🧠 **AI Model Performance** - Token usage, inference times
- 💾 **Memory Usage** - Capsule brain, knowledge graph
- 🔄 **System Health** - Service status, resource utilization

### **Key Performance Indicators**

| Metric | Target | Alert Threshold |
|--------|---------|----------------|
| API Response Time (p95) | < 2s | > 5s |
| Error Rate | < 1% | > 5% |
| Memory Usage | < 80% | > 90% |
| Token Cost/Request | $0.01 | $0.05 |

## 🔐 Security

### **Security Features**

- ✅ **Input Sanitization** - All inputs validated and sanitized
- ✅ **Authentication** - JWT-based with secure token handling  
- ✅ **Authorization** - Role-based access control (RBAC)
- ✅ **HTTPS** - All communications encrypted in transit
- ✅ **Dependency Scanning** - Automated via Dependabot
- ✅ **Container Security** - Minimal base images, non-root execution

### **Security Scanning**

```bash
# Python security scan
bandit -r src/ -f json -o security-report.json

# Frontend security audit
cd frontend && yarn audit

# Container security scan
docker scout cves liquid-hive:latest
```

See [SECURITY.md](SECURITY.md) for vulnerability reporting.

## 📚 Training & Self-Improvement

### **Dataset Building**

The system uses a hierarchical Oracle-Arbiter pipeline for quality assurance:

```bash
# Build training dataset with Oracle refinement
ENABLE_ORACLE_REFINEMENT=True python -m hivemind.training.dataset_build

# Fast mode (skip external API calls)
ENABLE_ORACLE_REFINEMENT=False python -m hivemind.training.dataset_build

# Enhanced reasoning mode with DeepSeek R1
ENABLE_ORACLE_REFINEMENT=True FORCE_DEEPSEEK_R1_ARBITER=True python -m hivemind.training.dataset_build
```

### **Pipeline Configuration**

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `ENABLE_ORACLE_REFINEMENT` | `True` | Master switch for refinement pipeline |
| `FORCE_DEEPSEEK_R1_ARBITER` | `False` | Use DeepSeek R1 for all refinements |

### **Model Training**

Fine-tune adapters using the `/train` endpoint:

```bash
curl -X POST http://localhost:8000/api/train \
  -H "Content-Type: application/json" \
  -d '{"dataset_path": "/data/training_dataset.jsonl"}'
```

## 🚢 Production Deployment

### **Docker Production**

```dockerfile
# Multi-stage build for optimized production image
FROM python:3.11-slim as builder
# ... (build steps)

FROM node:18-alpine as frontend
# ... (frontend build)

FROM python:3.11-slim as production
# ... (final production image)
```

### **Kubernetes with Helm**

```bash
# Deploy to Kubernetes
helm install liquid-hive ./helm/liquid-hive \
  --set image.tag=v1.0.0 \
  --set ingress.enabled=true \
  --set autoscaling.enabled=true
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for complete deployment guide.

## 📖 Documentation

- 📋 [**Contributing Guide**](CONTRIBUTING.md) - Development workflow
- 🔐 [**Security Policy**](SECURITY.md) - Vulnerability reporting
- 🚀 [**Deployment Guide**](docs/DEPLOYMENT.md) - Production deployment
- 📊 [**Graduation Report**](docs/GRADUATION_REPORT.md) - System analysis
- 🏗️ [**Architecture**](docs/architecture/) - Detailed system design

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### **Quick Contributor Setup**

```bash
# Fork and clone
git clone https://github.com/your-fork/liquid-hive.git
cd liquid-hive

# Development setup
make dev-setup

# Create feature branch
git checkout -b feature/amazing-feature

# Make changes and test
make test lint

# Submit PR
git push origin feature/amazing-feature
```

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **DeepSeek** - For advanced reasoning capabilities
- **OpenAI** - For GPT models and embeddings  
- **Qdrant** - For vector search
- **FastAPI** - For high-performance API framework
- **React** - For modern frontend framework

---

**⚡ Built with production-grade engineering practices:**
[![CI](https://github.com/AetheronResearch/liquid-hive/workflows/CI/badge.svg)](https://github.com/AetheronResearch/liquid-hive/actions)
[![Security](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Code Quality](https://img.shields.io/badge/code%20quality-ruff-orange.svg)](https://github.com/astral-sh/ruff)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
