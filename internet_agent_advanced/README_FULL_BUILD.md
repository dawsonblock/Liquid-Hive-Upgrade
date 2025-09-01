# Internet Agent — Full Build (Advanced + Consent + Challenge)

This package is pre-patched with:
- Advanced dual-lane fetch (HTTPX + Playwright)
- Trust tiers, robots.txt enforcement, domain policy
- RAG ingest → Qdrant, lineage → MinIO
- GitHub + Hugging Face API clients
- Prometheus metrics at `/metrics`
- **Consent system** (TTL approvals per domain for sensitive scopes)
- **Challenge flow** (halt on CAPTCHA/bot walls; resume with user-provided Playwright storage_state)
- FastAPI tools:
  - `POST /tools/internet_fetch`
  - `POST /tools/internet_search`
  - `POST /tools/internet_ingest`
  - `POST /tools/consent/request|approve|revoke`
  - `POST /tools/consent/upload_session|clear_session`
  - Test harness: `GET /test/challenge`, `GET /test/ok`

## Wire into your FastAPI app
```python
from internet_agent_advanced.fastapi_plugin import router as tools_router, metrics_app, test_router

app.include_router(tools_router)
app.include_router(test_router)
app.mount("/metrics", metrics_app)
```

## Consent scopes (configurable: config/permissions.yaml)
- fetch_http (default allow)
- render_js (ask)
- ingest_index (ask)
- large_download (ask if > threshold)
- api_github / api_hf (default allow)
- **Prohibited**: captcha_bypass, robots_override

## Determinism
Fixed seeds + stable UA. See `consent/determinism.py` and headers via `consent/middleware.py`.

## Run smoke
```bash
curl -X POST http://127.0.0.1:8080/tools/internet_fetch -H 'Content-Type: application/json'   -d '{"urls":["https://nasa.gov"],"render_js":false}'
curl -X POST http://127.0.0.1:8080/tools/internet_ingest -H 'Content-Type: application/json'   -d '{"url":"https://nasa.gov","render_js":false}'
curl http://127.0.0.1:8080/metrics | head
```
