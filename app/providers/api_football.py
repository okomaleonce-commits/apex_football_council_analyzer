from __future__ import annotations

from typing import Any
from app.providers.base import HTTPProvider, ProviderError


class APIFootballProvider(HTTPProvider):
    name = "api_football"

    def __init__(self, base_url: str, api_key: str):
        super().__init__(base_url)
        self.api_key = api_key

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        if not self.enabled:
            raise ProviderError("API_FOOTBALL_KEY is missing")
        return {"x-apisports-key": self.api_key}

    async def countries(self) -> dict[str, Any]:
        return await self.get("countries", headers=self._headers())

    async def leagues(self, country: str | None = None, season: int | None = None) -> dict[str, Any]:
        return await self.get("leagues", headers=self._headers(), params={"country": country, "season": season})

    async def teams(self, league_id: int, season: int) -> dict[str, Any]:
        return await self.get("teams", headers=self._headers(), params={"league": league_id, "season": season})

    async def fixtures(self, match_date: str, league_id: int | None = None, season: int | None = None, team_id: int | None = None) -> dict[str, Any]:
        return await self.get("fixtures", headers=self._headers(), params={"date": match_date, "league": league_id, "season": season, "team": team_id})

    async def standings(self, league_id: int, season: int) -> dict[str, Any]:
        return await self.get("standings", headers=self._headers(), params={"league": league_id, "season": season})

    async def fixture_statistics(self, fixture_id: int) -> dict[str, Any]:
        return await self.get("fixtures/statistics", headers=self._headers(), params={"fixture": fixture_id})

    async def lineups(self, fixture_id: int) -> dict[str, Any]:
        return await self.get("fixtures/lineups", headers=self._headers(), params={"fixture": fixture_id})

    async def injuries(self, fixture_id: int | None = None, league_id: int | None = None, season: int | None = None, team_id: int | None = None) -> dict[str, Any]:
        return await self.get("injuries", headers=self._headers(), params={"fixture": fixture_id, "league": league_id, "season": season, "team": team_id})

    async def odds(self, fixture_id: int | None = None, league_id: int | None = None, season: int | None = None) -> dict[str, Any]:
        return await self.get("odds", headers=self._headers(), params={"fixture": fixture_id, "league": league_id, "season": season})
