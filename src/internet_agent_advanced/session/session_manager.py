from __future__ import annotations
import os, json, urllib.parse, pathlib

STORAGE_DIR = os.getenv(
    "PLAYWRIGHT_STORAGE_DIR", os.path.join(os.path.dirname(__file__), "..", "sessions")
)
os.makedirs(STORAGE_DIR, exist_ok=True)


def _domain(url_or_domain: str) -> str:
    if "://" in url_or_domain:
        return urllib.parse.urlsplit(url_or_domain).netloc.lower()
    return url_or_domain.lower()


def storage_path_for(domain: str) -> str:
    d = _domain(domain)
    # replace ':' in host:port
    d = d.replace(":", "_")
    return os.path.join(STORAGE_DIR, f"{d}.json")


def get_storage_state_for_url(url: str) -> str | None:
    p = storage_path_for(url)
    return p if os.path.exists(p) else None


def save_storage_state(domain: str, storage_json: str | dict) -> str:
    if isinstance(storage_json, dict):
        txt = json.dumps(storage_json, ensure_ascii=False)
    else:
        txt = storage_json
    path = storage_path_for(domain)
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
    return path


def clear_storage_state(domain: str) -> bool:
    path = storage_path_for(domain)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False
