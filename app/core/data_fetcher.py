from __future__ import annotations

from datetime import datetime
from app.models import DataPack, MatchAnalysisRequest, SourceStatus, TeamSnapshot, OddsQuote
from app.providers.api_football import APIFootballProvider
from app.providers.football_data import FootballDataProvider
from app.providers.odds_api import OddsAPIProvider


class DataFetcher:
    def __init__(self, settings):
        self.settings = settings
        self.api_football = APIFootballProvider(settings.api_football_base_url, settings.api_football_key)
        self.football_data = FootballDataProvider(settings.football_data_base_url, settings.football_data_key)
        self.odds_api = OddsAPIProvider(settings.odds_api_base_url, settings.odds_api_key, settings.odds_regions, settings.odds_markets)

    async def countries(self):
        if not self.api_football.enabled:
            return [{"name": c} for c in ["England", "France", "Spain", "Italy", "Germany"]]
        try:
            payload = await self.api_football.countries()
            return payload.get("response", [])
        except Exception:
            return []

    async def leagues(self, country: str, season: int | None = None):
        fallback = ["Premier League", "Ligue 1", "La Liga", "Serie A", "Bundesliga"]
        if not self.api_football.enabled:
            return [{"league": {"id": None, "name": x}} for x in fallback]
        try:
            payload = await self.api_football.leagues(country=country, season=season)
            return payload.get("response", [])
        except Exception:
            return [{"league": {"id": None, "name": x}} for x in fallback]

    async def teams(self, league_id: int | None, league: str, season: int | None = None):
        if self.api_football.enabled and league_id:
            try:
                payload = await self.api_football.teams(league_id=league_id, season=season or datetime.now().year)
                return payload.get("response", [])
            except Exception:
                pass
        return [{"team": {"name": "Home Team"}}, {"team": {"name": "Away Team"}}]

    async def build_match_pack(self, request: MatchAnalysisRequest) -> DataPack:
        statuses: list[SourceStatus] = []
        raw = {}
        fixture_id = None
        kickoff = None
        exact_match_found = False
        home = TeamSnapshot(name=request.home)
        away = TeamSnapshot(name=request.away)
        odds: list[OddsQuote] = []

        if self.api_football.enabled:
            try:
                fixture_payload = await self.api_football.fixtures(match_date=str(request.match_date), league_id=request.league_id, season=request.season)
                raw["api_football_fixtures"] = fixture_payload
                statuses.append(SourceStatus(name="api_football", ok=True, confidence=0.65, message="Fixtures récupérés"))
                for item in fixture_payload.get("response", []):
                    teams = item.get("teams", {})
                    h = teams.get("home", {}).get("name", "")
                    a = teams.get("away", {}).get("name", "")
                    if h.lower() == request.home.lower() and a.lower() == request.away.lower():
                        exact_match_found = True
                        fixture_id = item.get("fixture", {}).get("id")
                        date_raw = item.get("fixture", {}).get("date")
                        if date_raw:
                            kickoff = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
                        break
            except Exception as exc:
                statuses.append(SourceStatus(name="api_football", ok=False, confidence=0.0, message=str(exc)))
        else:
            statuses.append(SourceStatus(name="api_football", ok=False, confidence=0.0, message="API_FOOTBALL_KEY manquante"))

        fd_code = self.football_data.competition_code(request.league)
        if self.football_data.enabled and fd_code:
            try:
                fd_payload = await self.football_data.matches(fd_code, date_from=str(request.match_date), date_to=str(request.match_date), season=request.season)
                raw["football_data_matches"] = fd_payload
                statuses.append(SourceStatus(name="football_data", ok=True, confidence=0.45, message="Données football-data disponibles"))
            except Exception as exc:
                statuses.append(SourceStatus(name="football_data", ok=False, confidence=0.0, message=str(exc)))
        else:
            statuses.append(SourceStatus(name="football_data", ok=False, confidence=0.0, message="FOOTBALL_DATA_KEY manquante ou ligue non mappée"))

        if self.odds_api.enabled:
            try:
                odds = await self.odds_api.odds_for_match(request.league, request.home, request.away)
                statuses.append(SourceStatus(name="odds_api", ok=bool(odds), confidence=0.50 if odds else 0.10, message=f"{len(odds)} cotes récupérées"))
            except Exception as exc:
                statuses.append(SourceStatus(name="odds_api", ok=False, confidence=0.0, message=str(exc)))
        else:
            statuses.append(SourceStatus(name="odds_api", ok=False, confidence=0.0, message="ODDS_API_KEY manquante"))

        return DataPack(request=request, source_status=statuses, fixture_id=fixture_id, kickoff_utc=kickoff, exact_match_found=exact_match_found, home=home, away=away, odds=odds, raw=raw)
