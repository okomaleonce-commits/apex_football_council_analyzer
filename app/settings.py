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

    # --- Modèle statistique (correction #2 : Dixon-Coles + ratings relatifs) ---
    # rho : dépendance des petits scores (Dixon-Coles). Valeur négative ~ -0.13
    # regonfle les scores de parité (0-0, 1-1) sous-estimés par le Poisson indépendant.
    dc_rho: float = -0.13
    max_goals: int = 10
    # Avantage du terrain appliqué multiplicativement aux lambdas.
    home_adv: float = 1.10
    away_adj: float = 0.92
    # Moyenne de buts par équipe et par match utilisée pour normaliser par ligue
    # quand on ne dispose pas de la vraie moyenne de la ligue.
    league_avg_goals: float = 1.35

    # --- Lecture des cotes (correction #3 : dévig avant calcul d'edge) ---
    # "shin" ou "proportional". Retire la marge du bookmaker pour obtenir les
    # vraies probabilités de marché avant de comparer au modèle.
    devig_method: str = "shin"

    # --- Gestion du risque (correction #5 : flat staking) ---
    # Mise fixe (fraction de bankroll) tant que la calibration n'est pas prouvée.
    flat_stake_pct: float = 0.01

    # --- Preuve d'edge (correction #1) ---
    # Tant que False, le moteur n'émet jamais de BET "argent réel" : les signaux
    # restent en mode conseil/structuration (advisory_only).
    calibration_proven: bool = False
    # Nombre minimal de paris réglés avec CLV positive avant de passer proven.
    min_settled_bets: int = 100
    tracking_db_path: str = "/tmp/apex_tracking.sqlite3"

    host: str = "0.0.0.0"
    port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
