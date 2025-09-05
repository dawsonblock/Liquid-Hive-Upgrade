# internet_agent_advanced

Advanced, compliant headless internet access for Capsule/HiveMind systems.

**Highlights**

- **Dual-lane fetch:** HTTPX fast path + Playwright JS-rendered path (optional screenshot/network capture)
- **Safety + compliance:** robots.txt (cached), domain policy YAML, trust scoring
- **Throughput:** per-host **Redis token bucket** (distributed) + per-process `aiolimiter` fallback
- **RAG ingest:** extract → chunk → dedup (Simhash) → embed → index to **Qdrant** → lineage to **S3/MinIO**
- **Ecosystem:** GitHub + Hugging Face API clients, optional SerpAPI search
- **Observability:** Prometheus counters/histograms and `/metrics` export
- **FastAPI plugin:** `/tools/internet_fetch`, `/tools/internet_search`, `/tools/internet_ingest`

> No CAPTCHA/anti-bot evasion. Challenges are surfaced as `captcha_required=True` or `blocked=True`.
> Respect site ToS and robots. Prefer official APIs when available.

## Install

```bash
pip install -r requirements.txt
python -m playwright install --with-deps  # if using JS-rendered lane
```

## Environment

See `.env.example` in your app; commonly used:

- Redis: `REDIS_URL=redis://localhost:6379/0` (enables distributed token bucket)
- Qdrant: `QDRANT_URL`, `QDRANT_COLLECTION`
- Embeddings: `EMBED_HTTP_URL` or local `sentence-transformers`
- Lineage (MinIO/S3): `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`, `MINIO_SECURE`
- Policies: `DOMAIN_POLICY_PATH` (defaults to `config/domain_policy.yaml`)
- Search: `SEARCH_PROVIDER=serpapi`, `SEARCH_API_KEY=...`

## FastAPI mounting

```python
from fastapi import FastAPI
from internet_agent_advanced.fastapi_plugin import router as tools_router, metrics_app

app = FastAPI(title="Capsule Internet v2")
app.include_router(tools_router)
app.mount("/metrics", metrics_app)  # Prometheus endpoint
```

## Programmatic usage

```python
import asyncio
from internet_agent_advanced.main_tool import internet_fetch, internet_search, internet_ingest

res = asyncio.run(internet_fetch(["https://nasa.gov"]))
res2 = asyncio.run(internet_search("site:nasa.gov Artemis program"))
res3 = asyncio.run(internet_ingest("https://nasa.gov"))  # full RAG pipeline
```

## Legal

This package does not ship or endorse CAPTCHA bypass or anti-bot evasion.
