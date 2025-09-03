# Deployment

## Docker Compose
- docker-compose up --build

## GitHub Container Registry
- Tag and push via docker-build.yml workflow on release tags

## Helm Chart
- Edit helm/values.yaml and install:
```
helm upgrade --install lh ./helm --set image.repository=ghcr.io/OWNER/REPO/liquid-hive --set image.tag=latest
```

## Alerts & Dashboards
- Prometheus runs on 9090, Grafana on 3000; alert thresholds configured in prometheus/alerts.yml

## OpenTelemetry
- Set OTEL_EXPORTER_OTLP_ENDPOINT to enable traces export