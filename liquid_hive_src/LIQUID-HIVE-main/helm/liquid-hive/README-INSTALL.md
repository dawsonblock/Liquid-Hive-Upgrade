# Liquid-Hive Helm Install Notes (Internet Agent Advanced Enabled)

## Template
helm template lh helm/liquid-hive \
  --set image.repository="ghcr.io/your-org/liquid-hive" \
  --set image.tag="latest" \
  -f helm/liquid-hive/values-dev.yaml >/dev/null

## Install/Upgrade
helm upgrade --install lh helm/liquid-hive \
  --set image.repository="ghcr.io/your-org/liquid-hive" \
  --set image.tag="latest" \
  -f helm/liquid-hive/values-dev.yaml

## Port-forward and Probe
kubectl rollout status deploy/liquid-hive --timeout=180s
kubectl port-forward deploy/liquid-hive 8080:8000 &
sleep 3
curl -fsS http://127.0.0.1:8080/api/healthz | jq .
curl -fsS http://127.0.0.1:8080/api/metrics | head -n 10
curl -fsS http://127.0.0.1:8080/api/internet-agent-metrics | head -n 10

## Optional Integrations (Dev)
# In your values-dev.yaml add:
# config:
#   database:
#     qdrantUrl: "http://qdrant:6333"
#     minioEndpoint: "http://minio:9000"
#     minioAccessKey: "minio"
#     minioSecretKey: "minio123"
#     minioBucket: "web-raw"
#     minioSecure: false

# Confirm with:
curl -fsS -X POST http://127.0.0.1:8080/api/tools/internet_ingest \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://nasa.gov","render_js":false}' | jq .
