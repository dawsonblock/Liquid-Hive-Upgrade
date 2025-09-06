from __future__ import annotations

import os
from typing import Any

import httpx
from src.logging_config import get_logger

QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "web_corpus")


async def index_qdrant(
    chunks: list[dict[str, Any]], vectors: list[list[float]], meta: dict[str, Any]
):
    points = []
    for i, ch in enumerate(chunks):
        points.append(
            {
                "id": f"{meta.get('hash', 'h')}_{i}",
                "vector": vectors[i],
                "payload": {"text": ch["text"], **meta, "chunk_id": ch["chunk_id"]},
            }
        )
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.put(
            f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points?wait=true",
            json={"points": points},
        )
        return {"status": r.status_code, "text": r.text}
