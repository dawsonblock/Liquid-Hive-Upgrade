from __future__ import annotations

import os

import httpx


class LiquidHiveClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.getenv("BASE_URL") or "http://localhost:8000").rstrip("/")
        self.api_key = api_key or os.getenv("API_KEY")
        self._headers = {"Content-Type": "application/json"}
        if self.api_key:
            self._headers["x-api-key"] = self.api_key

    async def health(self) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base_url}/api/healthz")
            r.raise_for_status()
            return r.json()

    async def chat(self, q: str) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{self.base_url}/api/chat", params={"q": q})
            r.raise_for_status()
            return r.json()

    async def arena_submit(self, task_input: str, reference: str | None = None, metadata: dict | None = None) -> dict:
        payload = {"input": task_input, "reference": reference, "metadata": metadata or {}}
        async with httpx.AsyncClient(headers=self._headers) as client:
            r = await client.post(f"{self.base_url}/api/arena/submit", json=payload)
            r.raise_for_status()
            return r.json()

    async def arena_compare(self, task_id: str, model_a: str, model_b: str, output_a: str, output_b: str, winner: str | None = None) -> dict:
        payload = {"task_id": task_id, "model_a": model_a, "model_b": model_b, "output_a": output_a, "output_b": output_b}
        if winner:
            payload["winner"] = winner
        async with httpx.AsyncClient(headers=self._headers) as client:
            r = await client.post(f"{self.base_url}/api/arena/compare", json=payload)
            r.raise_for_status()
            return r.json()

    async def arena_leaderboard(self) -> dict:
        async with httpx.AsyncClient(headers=self._headers) as client:
            r = await client.get(f"{self.base_url}/api/arena/leaderboard")
            r.raise_for_status()
            return r.json()
