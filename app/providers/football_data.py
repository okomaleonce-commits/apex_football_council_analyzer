from __future__ import annotations

from typing import Any
from app.providers.base import HTTPProvider, ProviderError

COMPETITION_ALIASES = {
    "premier league": "PL",
    "epl": "PL",
    "la liga": "PD",
    "primera division": "PD",
    "serie a": "SA",
    "bundesliga": "BL1",
    "ligue 1": "FL1",
    "eredivisie": "DED",
    "championship": "ELC",
    "primeira liga": "PPL",
}


class FootballDataProvider(HTTPProvider):
    name = "football_data"

    def __init__(self, base_url: str, api_key: str):
        super().__init__(base_url)
        self.api_key = api_key

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        if not self.enabled:
            raise ProviderError("FOOTBALL_DATA_KEY is missing")
        return {"X-Auth-Token": self.api_key}

    @staticmethod
    def competition_code(league: str) -> str | None:
        return COMPETITION_ALIASES.get((league or "").lower().strip())

    async def competitions(self) -> dict[str, Any]:
        return await self.get("competitions", headers=self._headers())

    async def matches(self, competition_code: str, date_from: str | None = None, date_to: str | None = None, season: int | None = None) -> dict[str, Any]:
        return await self.get(f"competitions/{competition_code}/matches", headers=self._headers(), params={"dateFrom": date_from, "dateTo": date_to, "season": season})

    async def standings(self, competition_code: str) -> dict[str, Any]:
        return await self.get(f"competitions/{competition_code}/standings", headers=self._headers())
