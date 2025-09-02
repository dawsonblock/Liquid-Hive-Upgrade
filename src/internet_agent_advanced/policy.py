from __future__ import annotations

import os
import urllib.parse

import yaml

from .config import DOMAIN_POLICY_PATH


def _policy_path() -> str:
    return DOMAIN_POLICY_PATH or os.path.join(
        os.path.dirname(__file__), "config", "domain_policy.yaml"
    )


def load_policy() -> dict:
    with open(_policy_path(), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def domain_from_url(url: str) -> str:
    return urllib.parse.urlparse(url).netloc.lower()


def apply_policy(url: str, policy: dict) -> dict:
    dom = domain_from_url(url)
    for entry in policy.get("domains", []):
        if entry.get("domain") in dom:
            return entry if entry.get("allow", False) else {"allow": False}
    return policy.get("defaults", {"allow": False})
