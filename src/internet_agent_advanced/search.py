from __future__ import annotations

import os

import httpx

from .main_tool import internet_fetch
from .schemas import FetchResult


async def internet_search(query: str, max_results: int = 5) -> FetchResult:
    provider = os.getenv("SEARCH_PROVIDER")
    api_key = os.getenv("SEARCH_API_KEY")
    if provider == "serpapi" and api_key:
        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "num": max_results,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get("https://serpapi.com/search", params=params)
            r.raise_for_status()
            data = r.json()
            urls = []
            for item in (data.get("organic_results") or [])[:max_results]:
                link = item.get("link")
                if link:
                    urls.append(link)
            return await internet_fetch(urls)
    return FetchResult(
        errors=[{"query": query, "error": "No SEARCH_PROVIDER configured"}]
    )
