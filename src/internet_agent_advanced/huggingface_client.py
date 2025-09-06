from __future__ import annotations

import os
import time
from typing import Any

from huggingface_hub import HfApi
from src.logging_config import get_logger


def get_hf(api_token: str | None = None) -> HfApi:
    token = api_token or os.getenv("HUGGINGFACE_TOKEN")
    return HfApi(token=token)


def fetch_model_card(repo_id: str, api_token: str | None = None) -> dict[str, Any]:
    api = get_hf(api_token)
    info = api.model_info(repo_id)
    card = info.cardData or {}
    return {
        "repo_id": repo_id,
        "sha": info.sha,
        "likes": info.likes,
        "downloads": info.downloads,
        "siblings": [s.rfilename for s in info.siblings],
        "pipeline_tag": info.pipeline_tag,
        "tags": info.tags,
        "model_card": card,
        "fetched_at": time.time(),
    }
