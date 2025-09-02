from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)
from starlette.applications import Starlette
from starlette.responses import Response

scrape_success = Counter("ia_scrape_success_total", "Successful scrapes")
scrape_fail = Counter("ia_scrape_fail_total", "Failed scrapes")
lane_http = Counter("ia_lane_http_total", "HTTP lane hits")
lane_browser = Counter("ia_lane_browser_total", "Browser lane hits")
fetch_latency = Histogram("ia_fetch_latency_seconds", "Fetch latency (s)")

# Minimal ASGI app to expose metrics at /metrics
metrics_app = Starlette()


@metrics_app.route("/")
async def _metrics(_):
    data = generate_latest()
    return Response(data, media_type=CONTENT_TYPE_LATEST)
