#!/usr/bin/env python3
from __future__ import annotations
import os, asyncio, json
import httpx

BASE_URL = (os.getenv('BASE_URL') or 'http://localhost:8000').rstrip('/')

async def submit_seed(task):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BASE_URL}/api/arena/submit", json=task)
        r.raise_for_status()
        return r.json()

async def main():
    seeds_path = os.getenv('GOLDEN_SEEDS', 'golden/seeds.jsonl')
    if not os.path.exists(seeds_path):
        print(f"No seeds at {seeds_path}")
        return
    ok = 0
    with open(seeds_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            task = json.loads(line)
            try:
                resp = await submit_seed(task)
                ok += 1
                print('submitted', resp)
            except Exception as e:
                print('error', e)
    print('done, submitted', ok)

if __name__ == '__main__':
    asyncio.run(main())