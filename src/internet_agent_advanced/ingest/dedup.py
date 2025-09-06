from __future__ import annotations

from simhash import Simhash
from src.logging_config import get_logger


def content_hash(text: str) -> str:
    return hex(Simhash(text).value)
