from __future__ import annotations

from typing import Any
import httpx


class ProviderError(Exception):
    pass


class HTTPProvider:
    def __init__(self, base_url: str, timeout: float = 20.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def get(self, path: str, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        clean_params = {k: v for k, v in (params or {}).items() if v not in [None, ""]}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=headers or {}, params=clean_params)
        if response.status_code >= 400:
            raise ProviderError(f"{response.status_code} from {url}: {response.text[:300]}")
        return response.json()
