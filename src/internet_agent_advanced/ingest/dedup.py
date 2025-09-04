from __future__ import annotations

from simhash import Simhash


def content_hash(text: str) -> str:
    return hex(Simhash(text).value)
