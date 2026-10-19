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

    @staticmethod
    def _parse_standings(payload: dict) -> dict[int, dict]:
        """Extrait par team_id : played, win/draw/lose, buts POUR/CONTRE par match, rang, forme."""
        stats: dict[int, dict] = {}
        for entry in payload.get("response", []):
            league = entry.get("league", {})
            for group in league.get("standings", []) or []:
                for row in group:
                    team = row.get("team", {})
                    tid = team.get("id")
                    allm = row.get("all", {}) or {}
                    played = allm.get("played")
                    goals = allm.get("goals", {}) or {}
                    gf = goals.get("for")
                    ga = goals.get("against")
                    if tid is None:
                        continue
                    stats[tid] = {
                        "played": played,
                        "wins": allm.get("win"),
                        "draws": allm.get("draw"),
                        "losses": allm.get("lose"),
                        # Buts par match (total / joués) pour éviter toute ambiguïté d'unité.
                        "goals_for": round(gf / played, 3) if played and gf is not None else None,
                        "goals_against": round(ga / played, 3) if played and ga is not None else None,
                        "rank": row.get("rank"),
                        "form": row.get("form"),
                    }
        return stats

    @staticmethod
    def _apply_team_stats(team: TeamSnapshot, stats: dict | None) -> None:
        if not stats:
            return
        for field in ("played", "wins", "draws", "losses", "goals_for", "goals_against", "rank", "form"):
            value = stats.get(field)
            if value is not None:
                setattr(team, field, value)

    @staticmethod
    def _count_injuries(payload: dict) -> dict[int, int]:
        counts: dict[int, int] = {}
        for item in payload.get("response", []):
            tid = (item.get("team", {}) or {}).get("id")
            if tid is not None:
                counts[tid] = counts.get(tid, 0) + 1
        return counts

    async def build_match_pack(self, request: MatchAnalysisRequest) -> DataPack:
        statuses: list[SourceStatus] = []
        raw = {}
        fixture_id = None
        kickoff = None
        exact_match_found = False
        home = TeamSnapshot(name=request.home)
        away = TeamSnapshot(name=request.away)
        odds: list[OddsQuote] = []
        home_id = away_id = None
        league_id = request.league_id
        season = request.season

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
                        home_id = teams.get("home", {}).get("id")
                        away_id = teams.get("away", {}).get("id")
                        league_id = item.get("league", {}).get("id") or league_id
                        season = item.get("league", {}).get("season") or season
                        date_raw = item.get("fixture", {}).get("date")
                        if date_raw:
                            kickoff = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
                        break
            except Exception as exc:
                statuses.append(SourceStatus(name="api_football", ok=False, confidence=0.0, message=str(exc)))

            # Statistiques d'équipes via classement (indispensable au modèle).
            if exact_match_found and league_id and season:
                try:
                    standings_payload = await self.api_football.standings(league_id=league_id, season=season)
                    raw["api_football_standings"] = standings_payload
                    stats = self._parse_standings(standings_payload)
                    self._apply_team_stats(home, stats.get(home_id))
                    self._apply_team_stats(away, stats.get(away_id))
                    filled = sum(1 for t in (home, away) if t.played is not None)
                    statuses.append(SourceStatus(name="api_football_standings", ok=filled == 2, confidence=0.65 if filled == 2 else 0.2, message=f"Stats remplies pour {filled}/2 équipes"))
                except Exception as exc:
                    statuses.append(SourceStatus(name="api_football_standings", ok=False, confidence=0.0, message=str(exc)))

            # Blessures par équipe sur ce match.
            if exact_match_found and fixture_id:
                try:
                    injuries_payload = await self.api_football.injuries(fixture_id=fixture_id)
                    raw["api_football_injuries"] = injuries_payload
                    counts = self._count_injuries(injuries_payload)
                    if home_id in counts:
                        home.injuries_count = counts[home_id]
                    if away_id in counts:
                        away.injuries_count = counts[away_id]
                    statuses.append(SourceStatus(name="api_football_injuries", ok=True, confidence=0.4, message=f"{sum(counts.values())} blessures recensées"))
                except Exception as exc:
                    statuses.append(SourceStatus(name="api_football_injuries", ok=False, confidence=0.0, message=str(exc)))
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
