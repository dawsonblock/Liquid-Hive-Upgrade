from __future__ import annotations

import hashlib

from sqlitedict import SqliteDict

from .config import CACHE_PATH


def _key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


class Cache:
    def __init__(self, path: str | None = None):
        self.db = SqliteDict(path or CACHE_PATH, autocommit=True)

    def get(self, url: str):
        return self.db.get(_key(url))

    def set(self, url: str, value):
        self.db[_key(url)] = value

    def close(self):
        self.db.close()
