from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.analyzer import FootballAnalyzer
from app.core.data_fetcher import DataFetcher
from app.core.hockey_analyzer import HockeyAnalyzer
from app.core.sports import check_domain
from app.models import MatchAnalysisRequest, OutOfDomainReport
from app.settings import get_settings

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
settings = get_settings()

app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

fetcher = DataFetcher(settings)
analyzer = FootballAnalyzer(settings)
hockey_analyzer = HockeyAnalyzer(settings)


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name, "providers": {"api_football": bool(settings.api_football_key), "football_data": bool(settings.football_data_key), "odds_api": bool(settings.odds_api_key), "llm_council_mode": settings.llm_council_mode}}


@app.get("/api/countries")
async def countries():
    return {"countries": await fetcher.countries()}


@app.get("/api/leagues")
async def leagues(country: str, season: int | None = Query(default=None)):
    return {"leagues": await fetcher.leagues(country=country, season=season)}


@app.get("/api/teams")
async def teams(league: str, league_id: int | None = Query(default=None), season: int | None = Query(default=None)):
    return {"teams": await fetcher.teams(league_id=league_id, league=league, season=season)}


@app.get("/api/sports")
async def sports():
    """Liste des sports calibrés (moteur dédié) exposée à l'interface."""
    from app.core.sports import SUPPORTED_SPORTS
    return {"sports": [{"key": k, "engine": v} for k, v in SUPPORTED_SPORTS.items()]}


@app.post("/api/analyze")
async def analyze_match(request: MatchAnalysisRequest):
    if request.home.lower().strip() == request.away.lower().strip():
        raise HTTPException(status_code=400, detail="Home et Away doivent être deux équipes différentes.")

    # Garde hors-domaine : un sport sans moteur calibré ne traverse jamais le
    # pipeline football/hockey. On renvoie un verdict NO_MODEL honnête.
    domain = check_domain(request.sport)
    if not domain.supported:
        from app.core.sports import SUPPORTED_SPORTS
        return OutOfDomainReport(
            request=request,
            sport=domain.sport,
            message=domain.message,
            supported_sports=list(SUPPORTED_SPORTS),
        ).model_dump(mode="json")

    pack = await fetcher.build_match_pack(request)
    if domain.sport == "hockey":
        report = hockey_analyzer.analyze(pack)
    else:
        report = analyzer.analyze(pack)
    return report.model_dump(mode="json")
