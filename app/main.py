from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.core import auth, db
from app.core import payments as pay
from app.core.analyzer import FootballAnalyzer
from app.core.coupon import CouponRequest, build_coupon
from app.core.data_fetcher import DataFetcher
from app.core.demo import demo_packs
from app.core.montante import MontanteRequest, build_montante
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
db.configure(settings.db_path)


class Credentials(BaseModel):
    email: str
    password: str


def _current_user(request: Request):
    return auth.user_from_token(request.cookies.get(auth.SESSION_COOKIE))


def _set_session_cookie(response: Response, token: str) -> None:
    secure = settings.app_base_url.startswith("https")
    response.set_cookie(auth.SESSION_COOKIE, token, httponly=True, samesite="lax",
                        secure=secure, max_age=settings.session_days * 86400, path="/")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name, "providers": {"api_football": bool(settings.api_football_key), "football_data": bool(settings.football_data_key), "odds_api": bool(settings.odds_api_key), "llm_council_mode": settings.llm_council_mode}}


@app.get("/api/config")
async def config():
    return {"subscription_price": settings.subscription_price,
            "subscription_currency": settings.subscription_currency,
            "subscription_days": settings.subscription_days,
            "payments_mode": settings.payments_mode}


@app.post("/api/register")
async def register(creds: Credentials, response: Response):
    email = creds.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Email invalide.")
    if len(creds.password) < 8:
        raise HTTPException(status_code=400, detail="Mot de passe : 8 caractères minimum.")
    if db.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet email.")
    user_id = db.create_user(email, auth.hash_password(creds.password))
    token = auth.issue_session(user_id, settings.session_days)
    _set_session_cookie(response, token)
    return {"email": email, "subscribed": False}


@app.post("/api/login")
async def login(creds: Credentials, response: Response):
    user = db.get_user_by_email(creds.email)
    if not user or not auth.verify_password(creds.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")
    token = auth.issue_session(user["id"], settings.session_days)
    _set_session_cookie(response, token)
    return {"email": user["email"], "subscribed": auth.is_subscribed(user)}


@app.post("/api/logout")
async def logout(request: Request, response: Response):
    auth.revoke(request.cookies.get(auth.SESSION_COOKIE))
    response.delete_cookie(auth.SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/api/me")
async def me(request: Request):
    user = _current_user(request)
    if not user:
        return {"authenticated": False}
    return {"authenticated": True, "email": user["email"],
            "subscribed": auth.is_subscribed(user),
            "subscription_until": user["subscription_until"]}


@app.post("/api/subscribe")
async def subscribe(request: Request):
    user = _current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Connecte-toi d'abord.")
    tx = pay.new_transaction_id()
    db.create_payment(tx, user["id"], settings.subscription_price, settings.subscription_currency)
    # URL publique : réglage explicite si fourni (non-localhost), sinon déduite de la requête.
    base_url = settings.app_base_url
    if not base_url.startswith("http") or "localhost" in base_url or "127.0.0.1" in base_url:
        base_url = str(request.base_url)
    try:
        init = await pay.init_payment(settings, base_url, tx, settings.subscription_price,
                                      f"Abonnement APEX {settings.subscription_days} jours")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Paiement indisponible : {exc}")
    return {"transaction_id": tx, "payment_url": init["payment_url"], "mode": init["mode"],
            "amount": settings.subscription_price, "currency": settings.subscription_currency}


@app.post("/api/payments/confirm-demo")
async def confirm_demo(request: Request):
    """Simule un paiement réussi (mode démo uniquement)."""
    if settings.payments_mode == "live":
        raise HTTPException(status_code=400, detail="Indisponible en mode live.")
    user = _current_user(request)
    body = await request.json()
    tx = (body or {}).get("transaction_id", "")
    payment = db.get_payment(tx)
    if not user or not payment or payment["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Paiement introuvable.")
    if payment["status"] != "PENDING":
        return {"status": payment["status"]}
    db.set_payment_status(tx, "ACCEPTED")
    until = auth.extend_subscription(user["id"], settings.subscription_days)
    return {"status": "ACCEPTED", "subscription_until": until.isoformat()}


@app.post("/api/payments/webhook")
async def payments_webhook(request: Request):
    """Notification CinetPay (mode live). On re-vérifie toujours côté serveur."""
    form = await request.form()
    tx = form.get("cpm_trans_id") or form.get("transaction_id")
    if not tx:
        try:
            tx = (await request.json()).get("transaction_id")
        except Exception:
            tx = None
    payment = db.get_payment(tx) if tx else None
    if not payment:
        raise HTTPException(status_code=404, detail="Transaction inconnue.")
    status = await pay.verify_payment(settings, tx)
    if status == "ACCEPTED" and payment["status"] != "ACCEPTED":
        db.set_payment_status(tx, "ACCEPTED")
        auth.extend_subscription(payment["user_id"], settings.subscription_days)
    elif status == "REFUSED":
        db.set_payment_status(tx, "REFUSED")
    return {"status": status}


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


@app.post("/api/montante")
async def montante(req: MontanteRequest):
    """Module Bankroll / Montante : plan de mises progressives + proba de complétion."""
    return build_montante(req).model_dump(mode="json")


@app.get("/api/predictions")
async def predictions(request: Request, league: str = Query(default="Ligue 1")):
    """Module Pronostic du jour : chaque match passé au moteur (Poisson + conseil).

    Paywall : les non-abonnés voient 2 matchs ; les abonnés voient tout.
    En démo (sans clés), utilise des matchs pré-remplis analysés par le vrai moteur.
    """
    reports = [analyzer.analyze(pack).model_dump(mode="json") for pack in demo_packs(league)]
    subscribed = auth.is_subscribed(_current_user(request))
    free_limit = 2
    locked = 0 if subscribed else max(0, len(reports) - free_limit)
    visible = reports if subscribed else reports[:free_limit]
    return {"mode": "demo", "league": league, "subscribed": subscribed,
            "locked_count": locked, "predictions": visible}


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


@app.get("/montante")
async def platform_montante():
    return FileResponse(PLATFORM_DIR / "montante.html")


@app.get("/login")
async def platform_login():
    return FileResponse(PLATFORM_DIR / "login.html")


@app.get("/account")
async def platform_account():
    return FileResponse(PLATFORM_DIR / "account.html")


@app.get("/pay/demo")
async def platform_pay_demo():
    return FileResponse(PLATFORM_DIR / "pay-demo.html")
