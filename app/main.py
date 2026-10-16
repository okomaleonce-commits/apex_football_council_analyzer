from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.analyzer import FootballAnalyzer
from app.core.coupon import CouponRequest, build_coupon
from app.core.data_fetcher import DataFetcher
from app.core.demo import demo_packs
from app.core.scanner import demo_signals, scan_payload
from app.models import MatchAnalysisRequest
from app.settings import get_settings

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
PLATFORM_DIR = BASE_DIR.parent / "platform"
settings = get_settings()

app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

fetcher = DataFetcher(settings)
analyzer = FootballAnalyzer(settings)


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
    report = analyzer.analyze(pack)
    return report.model_dump(mode="json")


@app.get("/api/scan")
async def scan(league: str = Query(default="Ligue 1"), edge_min: float | None = Query(default=None)):
    """Module Value Scanner : compare les cotes multi-books et détecte la value.

    Sans clé ODDS_API, renvoie un tableau de démonstration (mode=demo).
    """
    threshold = settings.edge_min if edge_min is None else edge_min
    odds_provider = getattr(fetcher, "odds_api", None)
    if not odds_provider or not getattr(odds_provider, "enabled", False):
        return {"mode": "demo", "league": league, "edge_min": threshold,
                "signals": [s.model_dump(mode="json") for s in demo_signals()]}
    sport_key = odds_provider.sport_key(league)
    if not sport_key:
        raise HTTPException(status_code=400, detail=f"Ligue non supportée par le flux de cotes : {league}")
    try:
        payload = await odds_provider.odds(sport_key)
    except Exception as exc:  # flux indisponible : on reste utilisable en démo
        return {"mode": "demo", "league": league, "edge_min": threshold, "error": str(exc),
                "signals": [s.model_dump(mode="json") for s in demo_signals()]}
    signals = scan_payload(payload, edge_min=threshold)
    return {"mode": "live", "league": league, "edge_min": threshold,
            "signals": [s.model_dump(mode="json") for s in signals]}


@app.post("/api/coupon")
async def coupon(req: CouponRequest):
    """Module Générateur de coupons : combine des sélections en un coupon chiffré."""
    return build_coupon(req).model_dump(mode="json")


@app.get("/api/predictions")
async def predictions(league: str = Query(default="Ligue 1")):
    """Module Pronostic du jour : chaque match passé au moteur (Poisson + conseil).

    En démo (sans clés), utilise des matchs pré-remplis analysés par le vrai moteur.
    """
    reports = [analyzer.analyze(pack) for pack in demo_packs(league)]
    return {"mode": "demo", "league": league,
            "predictions": [r.model_dump(mode="json") for r in reports]}


@app.get("/platform")
async def platform_landing():
    return FileResponse(PLATFORM_DIR / "index.html")


@app.get("/board")
async def platform_board():
    return FileResponse(PLATFORM_DIR / "dashboard.html")


@app.get("/coupons")
async def platform_coupons():
    return FileResponse(PLATFORM_DIR / "coupons.html")


@app.get("/predictions")
async def platform_predictions():
    return FileResponse(PLATFORM_DIR / "predictions.html")
