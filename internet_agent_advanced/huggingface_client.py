from __future__ import annotations
import os, time
from typing import Optional, Dict, Any
from huggingface_hub import HfApi

def get_hf(api_token: Optional[str] = None) -> HfApi:
    token = api_token or os.getenv("HUGGINGFACE_TOKEN")
    return HfApi(token=token)

def fetch_model_card(repo_id: str, api_token: Optional[str] = None) -> Dict[str, Any]:
    api = get_hf(api_token)
    info = api.model_info(repo_id)
    card = info.cardData or {}
    return {
        "repo_id": repo_id, "sha": info.sha, "likes": info.likes, "downloads": info.downloads,
        "siblings": [s.rfilename for s in info.siblings], "pipeline_tag": info.pipeline_tag,
        "tags": info.tags, "model_card": card, "fetched_at": time.time(),
    }
