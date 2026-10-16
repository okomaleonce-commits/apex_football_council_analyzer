from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "APEX Football Council Analyzer"
    app_env: str = "local"
    cache_ttl_seconds: int = 900

    api_football_base_url: str = "https://v3.football.api-sports.io"
    api_football_key: str = ""

    football_data_base_url: str = "https://api.football-data.org/v4"
    football_data_key: str = ""

    odds_api_base_url: str = "https://api.the-odds-api.com/v4"
    odds_api_key: str = ""
    odds_regions: str = "eu,uk"
    odds_markets: str = "h2h,totals"

    openai_api_key: str = ""
    openai_model: str = "gpt-5.1"
    llm_council_mode: str = "rules"

    data_confidence_min: float = 0.60
    edge_min: float = 0.035

    # --- Comptes, sessions, abonnement ---
    secret_key: str = "change-me-in-production-please"
    db_path: str = "apex.db"
    session_days: int = 30
    subscription_days: int = 30
    subscription_price: int = 5000           # en FCFA (XOF) par défaut
    subscription_currency: str = "XOF"
    app_base_url: str = "http://localhost:8000"

    # --- Paiement mobile money (CinetPay) ---
    payments_mode: str = "demo"              # "demo" (simulé) ou "live"
    cinetpay_base_url: str = "https://api-checkout.cinetpay.com/v2"
    cinetpay_api_key: str = ""
    cinetpay_site_id: str = ""

    host: str = "0.0.0.0"
    port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
