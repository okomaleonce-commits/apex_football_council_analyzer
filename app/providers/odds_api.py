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

    @staticmethod
    def normalize_quotes(payload: dict[str, Any] | list[dict[str, Any]], home: str, away: str) -> list[OddsQuote]:
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
                for market in bookmaker.get("markets", []):
                    key = market.get("key", "")
                    for outcome in market.get("outcomes", []):
                        price = outcome.get("price")
                        if not price:
                            continue
                        normalized_market = "1X2" if key == "h2h" else "OVER_UNDER_2_5" if key == "totals" else key
                        selection = outcome.get("name", "")
                        point = outcome.get("point")
                        if key == "totals" and point:
                            selection = f"{selection} {point}"
                        last_update = None
                        try:
                            raw_update = market.get("last_update") or bookmaker.get("last_update")
                            last_update = datetime.fromisoformat(raw_update.replace("Z", "+00:00")) if raw_update else None
                        except Exception:
                            last_update = None
                        quotes.append(OddsQuote(market=normalized_market, selection=selection, bookmaker=bookmaker_name, price=float(price), last_update=last_update))
        return quotes
