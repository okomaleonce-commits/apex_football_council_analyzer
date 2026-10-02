from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from pydantic import BaseModel, Field

Verdict = Literal["BET", "NO_BET", "WAIT_DATA", "WAIT_LINEUPS", "MONITOR_LIVE", "NO_MODEL"]
MarketName = Literal["1X2", "DOUBLE_CHANCE", "BTTS", "OVER_UNDER_2_5", "TEAM_TOTALS", "CORRECT_SCORE"]


class MatchAnalysisRequest(BaseModel):
    match_date: date
    country: str
    league: str
    home: str
    away: str
    # `sport` reste un str libre (et non un Literal) pour que les sports non
    # calibrés atteignent la garde hors-domaine (verdict NO_MODEL) au lieu
    # d'être rejetés en amont par la validation Pydantic.
    sport: str = "football"
    season: int | None = None
    league_id: int | None = None
    risk_profile: Literal["faible", "modere", "eleve"] = "modere"
    markets: list[MarketName] = Field(default_factory=lambda: ["1X2", "DOUBLE_CHANCE", "BTTS", "OVER_UNDER_2_5", "TEAM_TOTALS", "CORRECT_SCORE"])


class SourceStatus(BaseModel):
    name: str
    ok: bool
    confidence: float = 0.0
    message: str = ""
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class TeamSnapshot(BaseModel):
    name: str
    api_id: int | None = None
    rank: int | None = None
    played: int | None = None
    wins: int | None = None
    draws: int | None = None
    losses: int | None = None
    goals_for: float | None = None
    goals_against: float | None = None
    form: str | None = None
    injuries_count: int | None = None
    red_flags: list[str] = Field(default_factory=list)


class OddsQuote(BaseModel):
    market: str
    selection: str
    bookmaker: str
    price: float
    last_update: datetime | None = None


class DataPack(BaseModel):
    request: MatchAnalysisRequest
    source_status: list[SourceStatus] = Field(default_factory=list)
    fixture_id: int | None = None
    kickoff_utc: datetime | None = None
    exact_match_found: bool = False
    home: TeamSnapshot
    away: TeamSnapshot
    standings_payload: dict[str, Any] = Field(default_factory=dict)
    fixtures_payload: dict[str, Any] = Field(default_factory=dict)
    injuries_payload: dict[str, Any] = Field(default_factory=dict)
    lineups_payload: dict[str, Any] = Field(default_factory=dict)
    odds: list[OddsQuote] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class DataQuality(BaseModel):
    score: float
    verdict: Literal["GOOD", "MEDIUM", "WEAK", "UNUSABLE"]
    reasons: list[str]


class ProbabilitySet(BaseModel):
    home_win: float
    draw: float
    away_win: float
    home_or_draw: float
    home_or_away: float
    draw_or_away: float
    btts_yes: float
    btts_no: float
    over_2_5: float
    under_2_5: float
    home_over_0_5: float
    away_over_0_5: float
    most_likely_scores: list[dict[str, Any]]
    lambda_home: float
    lambda_away: float


class MarketSignal(BaseModel):
    market: str
    selection: str
    probability: float
    fair_odds: float
    best_odds: float | None = None
    edge: float | None = None
    roi_estimate: float | None = None
    confidence: float
    status: Literal["VALIDATED", "LEAN", "NO_VALUE", "NO_PRICE", "REJECTED"]
    rationale: str


class HockeyProbabilitySet(BaseModel):
    moneyline_home: float
    moneyline_away: float
    regulation_home: float
    regulation_tie: float
    regulation_away: float
    puckline_home_minus_1_5: float
    puckline_away_plus_1_5: float
    puckline_away_minus_1_5: float
    puckline_home_plus_1_5: float
    home_total_over_2_5: float
    away_total_over_2_5: float
    overtime_home_share: float
    most_likely_scores: list[dict[str, Any]]
    lambda_home: float
    lambda_away: float
    expected_total: float
    totals: dict[str, dict[str, float]]


class AdvisorOutput(BaseModel):
    advisor: str
    position: str
    risks: list[str] = Field(default_factory=list)
    recommendation: str


class CouncilVerdict(BaseModel):
    where_agrees: list[str]
    where_clashes: list[str]
    blind_spots: list[str]
    recommendation: str
    first_action: str
    advisors: list[AdvisorOutput]


class AnalysisReport(BaseModel):
    request: MatchAnalysisRequest
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    data_quality: DataQuality
    probabilities: ProbabilitySet
    market_signals: list[MarketSignal]
    final_verdict: Verdict
    primary_bet: MarketSignal | None = None
    alternatives: list[MarketSignal] = Field(default_factory=list)
    council: CouncilVerdict
    warnings: list[str] = Field(default_factory=list)
    data_pack_summary: dict[str, Any] = Field(default_factory=dict)


class HockeyReport(BaseModel):
    request: MatchAnalysisRequest
    sport: str = "hockey"
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    data_quality: DataQuality
    probabilities: HockeyProbabilitySet
    market_signals: list[MarketSignal]
    final_verdict: Verdict
    primary_bet: MarketSignal | None = None
    alternatives: list[MarketSignal] = Field(default_factory=list)
    council: CouncilVerdict
    warnings: list[str] = Field(default_factory=list)
    data_pack_summary: dict[str, Any] = Field(default_factory=dict)


class OutOfDomainReport(BaseModel):
    """Réponse structurée quand aucun moteur calibré n'existe pour le sport."""

    request: MatchAnalysisRequest
    sport: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    final_verdict: Verdict = "NO_MODEL"
    message: str
    supported_sports: list[str] = Field(default_factory=list)
