from __future__ import annotations

from datetime import datetime
from typing import Any
from app.models import OddsQuote
from app.providers.base import HTTPProvider, ProviderError

SPORT_KEY_ALIASES = {
    "premier league": "soccer_epl",
    "epl": "soccer_epl",
    "championship": "soccer_efl_champ",
    "la liga": "soccer_spain_la_liga",
    "serie a": "soccer_italy_serie_a",
    "bundesliga": "soccer_germany_bundesliga",
    "ligue 1": "soccer_france_ligue_one",
    "champions league": "soccer_uefa_champs_league",
    "europa league": "soccer_uefa_europa_league",
    "mls": "soccer_usa_mls",
}


class OddsAPIProvider(HTTPProvider):
    name = "odds_api"

    def __init__(self, base_url: str, api_key: str, regions: str, markets: str):
        super().__init__(base_url)
        self.api_key = api_key
        self.regions = regions
        self.markets = markets

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def sport_key(league: str) -> str | None:
        return SPORT_KEY_ALIASES.get((league or "").lower().strip())

    async def sports(self) -> dict[str, Any]:
        if not self.enabled:
            raise ProviderError("ODDS_API_KEY is missing")
        return await self.get("sports", params={"apiKey": self.api_key})

    async def odds(self, sport_key: str) -> dict[str, Any]:
        if not self.enabled:
            raise ProviderError("ODDS_API_KEY is missing")
        return await self.get(f"sports/{sport_key}/odds", params={"apiKey": self.api_key, "regions": self.regions, "markets": self.markets, "oddsFormat": "decimal", "dateFormat": "iso"})

    async def odds_for_match(self, league: str, home: str, away: str) -> list[OddsQuote]:
        key = self.sport_key(league)
        if not key:
            return []
        payload = await self.odds(key)
        return self.normalize_quotes(payload, home, away)

    @staticmethod
    def normalize_selection(market_key: str, outcome_name: str, home: str, away: str, point: float | None = None) -> tuple[str, str]:
        if market_key == "h2h":
            market = "1X2"
            lowered = outcome_name.lower()
            if lowered == home.lower():
                return market, "HOME"
            if lowered == away.lower():
                return market, "AWAY"
            if lowered in ["draw", "tie"]:
                return market, "DRAW"
            return market, outcome_name.upper()
        if market_key == "totals":
            market = "OVER_UNDER_2_5"
            side = "OVER" if outcome_name.lower().startswith("over") else "UNDER"
            if point and abs(float(point) - 2.5) < 0.01:
                return market, f"{side}_2_5"
            return market, f"{side}_{point}"
        return market_key.upper(), outcome_name.upper()

    @classmethod
    def normalize_quotes(cls, payload: dict[str, Any] | list[dict[str, Any]], home: str, away: str) -> list[OddsQuote]:
        events = payload if isinstance(payload, list) else payload.get("response") or payload.get("data") or []
        quotes: list[OddsQuote] = []
        for event in events:
            event_home = str(event.get("home_team", ""))
            event_away = str(event.get("away_team", ""))
            if home.lower() not in event_home.lower() and event_home.lower() not in home.lower():
                continue
            if away.lower() not in event_away.lower() and event_away.lower() not in away.lower():
                continue
            for bookmaker in event.get("bookmakers", []):
                bookmaker_name = bookmaker.get("title") or bookmaker.get("key") or "unknown"
                for market_data in bookmaker.get("markets", []):
                    key = market_data.get("key", "")
                    for outcome in market_data.get("outcomes", []):
                        price = outcome.get("price")
                        if not price:
                            continue
                        market, selection = cls.normalize_selection(key, outcome.get("name", ""), home, away, outcome.get("point"))
                        last_update = None
                        try:
                            raw_update = market_data.get("last_update") or bookmaker.get("last_update")
                            last_update = datetime.fromisoformat(raw_update.replace("Z", "+00:00")) if raw_update else None
                        except Exception:
                            pass
                        quotes.append(OddsQuote(market=market, selection=selection, bookmaker=bookmaker_name, price=float(price), last_update=last_update))
        return quotes
