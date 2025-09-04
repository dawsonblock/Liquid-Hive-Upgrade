#!/usr/bin/env python3
import re

# Read the file
with open('/app/README.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the start of the section to replace
start_pattern = r'### \*\*Health Check\*\*'
start_match = re.search(start_pattern, content)

if start_match:
    start_pos = start_match.start()
    # Replace everything from this point to the end
    new_content = content[:start_pos] + '''### **Health Check**

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
curl -X POST http://localhost:8000/api/chat \\
  -H "Content-Type: application/json" \\
  -d '{"query": "What is the capital of France?"}'

# Vision API
curl -X POST "http://localhost:8000/api/vision" \\
  -F "question=Describe this image" \\
  -F "file=@/path/to/image.png" \\
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
curl -X POST http://localhost:8000/api/train \\
  -H "Content-Type: application/json" \\
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
helm install liquid-hive ./helm/liquid-hive \\
  --set image.tag=v1.0.0 \\
  --set ingress.enabled=true \\
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
'''
    
    # Write the updated content back to the file
    with open('/app/README.md', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Successfully replaced the content!")
else:
    print("Section not found")