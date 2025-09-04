# Observability

- Traces: OTLP to in-cluster OTEL Collector (enabled by default). Swap `exporters` to Tempo/OTLP as needed.
- Metrics: ServiceMonitor scrapes /metrics on unified-runtime. Ensure your FastAPI exposes Prom metrics (e.g., prometheus_fastapi_instrumentator).
- Logs: Collector exports to logging by default. Configure exporters for Loki if available.
- Dashboards: Import FastAPI/OTEL dashboards into Grafana. Add alerts on 5xx rate, P95 latency, CPU/mem, HPA saturation.
