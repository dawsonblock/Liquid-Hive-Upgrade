from __future__ import annotations

import os

import httpx
from src.logging_config import get_logger

EMBED_HTTP_URL = os.getenv("EMBED_HTTP_URL")
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

_async_client = None


async def _remote_embed(texts: list[str]) -> list[list[float]]:
    global _async_client
    if _async_client is None:
        _async_client = httpx.AsyncClient(timeout=60.0)
    r = await _async_client.post(EMBED_HTTP_URL, json={"model": EMBED_MODEL, "texts": texts})
    r.raise_for_status()
    return r.json()["embeddings"]


def _local_embed(texts: list[str]) -> list[list[float]]:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(EMBED_MODEL)
    return model.encode(texts, normalize_embeddings=True).tolist()


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if EMBED_HTTP_URL:
        return await _remote_embed(texts)
    return _local_embed(texts)
