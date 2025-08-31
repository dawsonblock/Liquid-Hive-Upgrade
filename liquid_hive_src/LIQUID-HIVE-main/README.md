# LIQUID-HIVE
[README.md](https://github.com/user-attachments/files/22033452/README.md)
# Apex Hive‑Mind Unified Build

This repository represents a unified fusion of the cognitive agents from
`hivemind2` with the stateful ingestion and retrieval capabilities of
`hivemind_book_pipeline`.  It exposes a single FastAPI server in
`unified_runtime/server.py` that enriches user prompts via retrieval and
forwards them to a dynamic multi‑agent reasoning core.  The system logs
all interactions into a Capsule memory and supports a self‑improvement
loop via LoRA fine‑tuning.

## Canonical Architecture
For the definitive, single-source description of the final fused design, see:
- docs/ARCHITECTURE.md (Canonical)

Key points:
- Live operations use the DS‑Router exclusively (safety + intelligent routing + budget)
- Offline evolution is orchestrated by the Autonomy Orchestrator (dataset forging + fine‑tuning + A/B + approvals)

## Key Components

- **unified_runtime/** – the entry point for serving requests.  It contains
  the FastAPI application, the DS‑Router and the context bridge.
- **capsule_brain/** – provides long‑term memory, knowledge graph and
  self‑analysis routines.
- **hivemind/** – contains the agent roles, judge logic, retrieval and
  training scripts.
- **prometheus/** and **grafana/** – metrics collection and dashboards.
- **docker-compose.yml** – orchestrates the unified runtime and all supporting
  services.

## Running Locally

Install the dependencies:

```bash
pip install -r requirements.txt
```

Then start the services:

```bash
docker-compose up --build
```

This will launch all required services and expose the API on port 8000.  You can
query it via:

```bash
curl -X POST http://localhost:8000/api/chat -d 'q=What is the capital of France?'
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
stored in the `/data/runs` directory and fine‑tune LoRA adapters.  The
Oracle/Arbiter pipeline refines the system's synthesized answers before they are
used for training. DeepSeek‑R1 is the cost‑effective authority; GPT‑4o is an
optional fallback for golden datasets.

The fine‑tuned adapters can be deployed by updating the `adapter`
path in your configuration.  After running the `/train` endpoint to produce a
new adapter the `AdapterDeploymentManager` can register it as a challenger and
route a fraction of requests to it for A/B testing.

## Environment Variables

Set these in a `.env` at the repository root (used by Settings and DS‑Router):
- `DEEPSEEK_API_KEY`: enables DeepSeek providers (chat, thinking, R1)
- `HF_TOKEN`: enables local Qwen CPU fallback model downloads

Optional:
- `ADMIN_TOKEN`: required to call `/api/admin/*` endpoints

## Additional Considerations

See docs/ADDITIONAL_CONSIDERATIONS.md for security, observability, migration,
performance, testing, and deployment guidance associated with the latest changes.

### Operational Considerations (Summary)
- Security: Input sanitization in /api/chat; keep Approval Queue; use secrets manager (no committed .env).
- Observability: cb_* metrics in Grafana; consider SLO alerts for p95 latency, 5xx, token spikes.
- Migration: backend/ removed; unified_runtime is the API entrypoint; foundational_adapter_path centralized.
- Performance/Cost: Economic routing via DS‑Router; budget governance; deterministic fallbacks.
- Testing: Vision tests on ChatPanel; add backend tests for sanitize_input and error handling.

## Final System Analysis & Graduation Report
- Read the comprehensive, honest assessment here: docs/GRADUATION_REPORT.md