from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.analyzer import FootballAnalyzer
from app.core.data_fetcher import DataFetcher
from app.core.tracking import PredictionTracker
from app.models import MatchAnalysisRequest
from app.settings import get_settings

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
settings = get_settings()

app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

fetcher = DataFetcher(settings)
analyzer = FootballAnalyzer(settings)
tracker = PredictionTracker(settings.tracking_db_path)


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


@app.post("/api/analyze")
async def analyze_match(request: MatchAnalysisRequest):
    if request.home.lower().strip() == request.away.lower().strip():
        raise HTTPException(status_code=400, detail="Home et Away doivent être deux équipes différentes.")
    pack = await fetcher.build_match_pack(request)
    calibration = tracker.calibration_report(min_settled=settings.min_settled_bets)
    report = analyzer.analyze(pack, calibration=calibration)
    tracker.log_report(report)  # correction #1 : on trace pour prouver l'edge
    return report.model_dump(mode="json")


@app.get("/api/calibration")
async def calibration():
    """Preuve d'edge : Brier, log-loss et CLV sur l'historique réglé."""
    return tracker.calibration_report(min_settled=settings.min_settled_bets)


@app.post("/api/settle")
async def settle(prediction_id: int, won: bool, closing_odds: float | None = Query(default=None)):
    """Règle une prédiction (résultat réel + cote de clôture) pour alimenter la CLV."""
    tracker.settle(prediction_id, won=won, closing_odds=closing_odds)
    return {"ok": True, "prediction_id": prediction_id}
