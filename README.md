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

Health check:

```bash
curl http://localhost:8000/api/healthz
```

Vision example (multipart):

```bash
curl -X POST "http://localhost:8000/api/vision" \
  -F "question=Describe this image" \
  -F "file=@/path/to/image.png" \
  -F "grounding_required=false"
```

## Training and Self‑Improvement

Use the scripts in `hivemind/training/` to build datasets from the run logs
stored in the `/data/runs` directory and fine‑tune LoRA adapters. The
dataset builder now employs a _hierarchical Oracle and Arbiter_ pipeline to
refine the system's synthesized answers before they are used for training.
During dataset construction the `Arbiter` consults a primary Oracle
(DeepSeek‑V3) to critique and improve synthesized answers. If the output
fails structural or semantic validation the task is escalated to a
secondary, more powerful Arbiter (GPT‑4o). The resulting
`final_platinum_answer` is used as the target output for SFT/DPO and the
metadata records which model corrected each example are written to
`datasets/training_metadata.jsonl`.

The fine‑tuned adapters can be deployed by updating the `adapter`
path in your configuration. For example, after running the `/train`
endpoint to produce a new adapter the `AdapterDeploymentManager` will
register it as a challenger and route a fraction of requests to it for
A/B testing.

This repository should be treated as a starting point. Additional work is
required to merge the Helm charts, fine‑tune configuration and deploy in
production.

### Controlling the Oracle Pipeline

The Oracle/Arbiter refinement pipeline has been enhanced to use DeepSeek R1 instead of GPT-4o,
providing superior reasoning capabilities at 70% lower cost. The pipeline can be tuned or
disabled entirely through environment variables exposed by `hivemind.config.Settings`.

| Environment Variable        | Default | Description                                                                                                                                                                                                                                                |
| --------------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ENABLE_ORACLE_REFINEMENT`  | `True`  | Master switch for the refinement pipeline. When set to `False` the dataset builder will skip all external API calls and simply use the Judge's synthesized answer. This mode is the fastest and cheapest, suitable for offline or rapid iterations.        |
| `FORCE_DEEPSEEK_R1_ARBITER` | `False` | Forces all refinements to use DeepSeek R1 (reasoning mode) instead of DeepSeek-V3 when `ENABLE_ORACLE_REFINEMENT` is `True`. This provides the highest quality reasoning analysis while maintaining cost efficiency within the unified DeepSeek ecosystem. |

These environment variables can be set in your `.env` file or passed
directly via your orchestration layer (e.g. docker-compose). For example,
to run a fast, low‑cost training cycle you can disable refinement:

```bash
ENABLE_ORACLE_REFINEMENT=False python -m hivemind.training.dataset_build
```

To force all examples through DeepSeek R1 for enhanced reasoning analysis:

```bash
ENABLE_ORACLE_REFINEMENT=True FORCE_DEEPSEEK_R1_ARBITER=True python -m hivemind.training.dataset_build
```

## Additional Considerations

See docs/ADDITIONAL_CONSIDERATIONS.md for security, observability, migration, performance, testing, and deployment guidance associated with the latest changes.

### Operational Considerations (Summary)

- Security: Input sanitization in /api/chat; keep Approval Queue; use secrets manager (no committed .env).
- Observability: cb\_\* metrics in Grafana; consider SLO alerts for p95 latency, 5xx, token spikes.
- Migration: backend/ removed; unified_runtime is the API entrypoint; foundational_adapter_path centralized.
- Performance/Cost: Economic routing via StrategySelector; cap “Master” usage; gate LoRAX streaming and add rollback.
- Testing: New vision test on ChatPanel; add backend tests for sanitize_input and error handling.

## Final System Analysis & Graduation Report

- Read the comprehensive, honest assessment here: docs/GRADUATION_REPORT.md

## Deployment

For Kubernetes deployment with Helm and GitHub Actions CI/CD, see:

- docs/DEPLOYMENT.md (values, secrets, and workflows)
- .github/workflows (CI build/test/scan; CD for dev/prod)
