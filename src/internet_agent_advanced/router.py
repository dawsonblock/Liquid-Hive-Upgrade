from __future__ import annotations
from urllib.parse import urlparse
from typing import Dict, Any
from .scraper import fetch
from .github_client import fetch_repo_readme
from .huggingface_client import fetch_model_card
from .schemas import PageContent


async def route_fetch(target: str, render_js: bool = False) -> Dict[str, Any]:
    p = urlparse(target)
    host = p.netloc.lower()
    if "github.com" in host:
        parts = [x for x in p.path.split("/") if x]
        if len(parts) >= 2:
            return {"kind": "github_repo", "data": fetch_repo_readme(f"{parts[0]}/{parts[1]}")}
    if "huggingface.co" in host:
        parts = [x for x in p.path.split("/") if x]
        if len(parts) >= 2:
            return {"kind": "huggingface_model", "data": fetch_model_card(f"{parts[0]}/{parts[1]}")}
    page = await fetch(target, render_js=render_js)
    return {"kind": "web_page", "data": page.dict()}
