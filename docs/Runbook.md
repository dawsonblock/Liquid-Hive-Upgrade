# Runbook

- Enable Planner: set ENABLE_PLANNER=true
- Enable Arena: set ENABLE_ARENA=true
- Observability (OTEL): set OTEL_EXPORTER_OTLP_ENDPOINT and OTEL_SERVICE_NAME
- Providers: edit config/providers.yaml; set provider keys via environment; reload with POST /api/admin/reload-providers (x-admin-token if ADMIN_TOKEN set)
- Grafana: dashboards under grafana/dashboards; Prometheus at 9090; Alertmanager at 9093
- CI: .github/workflows/ci.yml runs planner+arena tests and exports docs/openapi.json
- SDKs: sdks/python and sdks/js
