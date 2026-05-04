from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

CACHE_PATH = Path("/tmp/apex_football_cache.sqlite3")


class SQLiteCache:
    def __init__(self, path: Path = CACHE_PATH):
        self.path = path
        self._init()

    def _init(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            conn.commit()

    @staticmethod
    def make_key(prefix: str, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, default=str)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"{prefix}:{digest}"

    def get(self, key: str) -> Any | None:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT value, expires_at FROM cache WHERE key = ?", (key,)).fetchone()
        if not row:
            return None
        value, expires_at = row
        if expires_at < time.time():
            self.delete(key)
            return None
        return json.loads(value)

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        expires_at = time.time() + ttl_seconds
        encoded = json.dumps(value, default=str)
        with sqlite3.connect(self.path) as conn:
            conn.execute("INSERT OR REPLACE INTO cache(key, value, expires_at) VALUES (?, ?, ?)", (key, encoded, expires_at))
            conn.commit()

    def delete(self, key: str) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()
