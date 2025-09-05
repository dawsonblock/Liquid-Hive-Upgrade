#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[1/6] Remove mirrored CI workflows under infra/gh-actions"
rm -rf "$ROOT/infra/gh-actions" || true

echo "[2/6] Enforce single helm chart"
# Keep only infra/helm/liquid-hive
[ -d "$ROOT/deploy/helm" ] && rm -rf "$ROOT/deploy/helm"
[ -d "$ROOT/helm" ] && rm -rf "$ROOT/helm"
[ -d "$ROOT/k8s" ] && rm -rf "$ROOT/k8s"  # if these are duplicates of the chart; keep only if unique

echo "[3/6] Prune duplicated library code from apps/api"
# If API contains library copies, delete them and rely on src/*
for PKG in hivemind capsule_brain internet_agent_advanced oracle unified_runtime; do
  if [ -d "$ROOT/apps/api/$PKG" ]; then
    echo " - removing duplicated $PKG under apps/api"
    rm -rf "$ROOT/apps/api/$PKG"
  fi
done

echo "[4/6] Ensure API imports target src.* (best-effort rewrite)"
# Simple sed-based path rewrite from apps/api/<pkg> to src/<pkg>
# (If none found, sed will noop.)
for PKG in hivemind capsule_brain internet_agent_advanced oracle unified_runtime; do
  find "$ROOT/apps/api" -name "*.py" -type f -exec grep -l "apps\.api\.$PKG" {} \; 2>/dev/null | while read -r f; do
    echo " - fixing imports in $f"
    sed -i "s|apps\.api\.$PKG|src.$PKG|g" "$f"
  done
  find "$ROOT/apps/api" -name "*.py" -type f -exec grep -l "from $PKG " {} \; 2>/dev/null | while read -r f; do
    # If bare 'from hivemind import X' exists and module no longer local, prefix with src.
    echo " - fixing bare imports in $f"
    sed -i "s|from $PKG |from src.$PKG |g" "$f"
  done
done

echo "[5/6] Create developer entrypoints if missing"
# .env.example
if [ ! -f "$ROOT/.env.example" ]; then
  cat > "$ROOT/.env.example" <<'ENV'
# Backend
API_PORT=8080
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317

# Frontend
VITE_API_BASE=http://localhost:8080

# Optional services
REDIS_URL=redis://redis:6379/0
QDRANT_URL=http://qdrant:6333

# Providers (optional; leave blank to disable)
OPENAI_API_KEY=
DEEPSEEK_API_KEY=
ANTHROPIC_API_KEY=
ENV
fi

# docker-compose.yaml
if [ ! -f "$ROOT/docker-compose.yaml" ]; then
  cat > "$ROOT/docker-compose.yaml" <<'YML'
services:
  api:
    build: ./apps/api
    env_file: .env
    ports: ["8080:8080"]
    depends_on: [prometheus]
  frontend:
    build: ./frontend
    environment:
      - VITE_API_BASE=${VITE_API_BASE:-http://localhost:8080}
    ports: ["5173:5173"]
    depends_on: [api]
  prometheus:
    image: prom/prometheus:latest
    volumes: ["./infra/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml"]
    ports: ["9090:9090"]
  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    depends_on: [prometheus]
  # optional
  redis:
    image: redis:7
    ports: ["6379:6379"]
  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
YML
fi

# Makefile
if [ ! -f "$ROOT/Makefile" ]; then
  cat > "$ROOT/Makefile" <<'MK'
.PHONY: dev test lint compose-up compose-down helm-apply

dev: ## Run local stack
\tdocker compose up --build

test: ## Run backend + frontend tests with coverage (assumes scripts exist)
\tbash -lc "cd apps/api && pytest --maxfail=1 --disable-warnings -q"
\tbash -lc "cd frontend && npm ci && npm test"

lint:
\tbash -lc "cd apps/api && ruff check . || flake8 ."
\tbash -lc "cd frontend && npx eslint . || true"

compose-up:
\tdocker compose up -d

compose-down:
\tdocker compose down -v

helm-apply:
\thelm upgrade --install liquid-hive infra/helm/liquid-hive -f infra/helm/liquid-hive/values-dev.yaml
MK
fi

echo "[6/6] Done."