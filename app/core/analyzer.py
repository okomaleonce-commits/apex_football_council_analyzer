from __future__ import annotations

from app.core.metrics import best_price, edge, expected_roi, fair_odds
from app.core.poisson import compute_probabilities
from app.models import AnalysisReport, CouncilVerdict, DataPack, DataQuality, MarketSignal, ProbabilitySet, AdvisorOutput


class FootballAnalyzer:
    def __init__(self, settings):
        self.settings = settings

    def analyze(self, pack: DataPack) -> AnalysisReport:
        quality = self._quality(pack)
        lambda_home, lambda_away = self._estimate_lambdas(pack)
        probabilities = ProbabilitySet(**compute_probabilities(lambda_home, lambda_away))
        signals = self._signals(pack, probabilities, quality.score)
        validated = [s for s in signals if s.status == "VALIDATED"]
        lean = [s for s in signals if s.status == "LEAN"]
        primary = validated[0] if validated else None
        verdict = "NO_BET"
        warnings = []
        if quality.score < self.settings.data_confidence_min:
            verdict = "WAIT_DATA" if quality.verdict != "UNUSABLE" else "NO_BET"
            warnings.append("Qualité des données insuffisante pour valider un pari.")
        elif primary:
            verdict = "BET"
        elif lean:
            verdict = "MONITOR_LIVE"
            warnings.append("Signal intéressant mais edge insuffisant ou cote absente.")
        council = self._council(quality, signals, primary)
        return AnalysisReport(
            request=pack.request,
            data_quality=quality,
            probabilities=probabilities,
            market_signals=signals,
            final_verdict=verdict,
            primary_bet=primary,
            alternatives=validated[1:4] if primary else lean[:3],
            council=council,
            warnings=warnings,
            data_pack_summary={
                "fixture_id": pack.fixture_id,
                "exact_match_found": pack.exact_match_found,
                "kickoff_utc": pack.kickoff_utc,
                "odds_count": len(pack.odds),
                "sources": [s.model_dump(mode="json") for s in pack.source_status],
            },
        )

    def _estimate_lambdas(self, pack: DataPack) -> tuple[float, float]:
        home_gf = pack.home.goals_for if pack.home.goals_for is not None else 1.45
        home_ga = pack.home.goals_against if pack.home.goals_against is not None else 1.15
        away_gf = pack.away.goals_for if pack.away.goals_for is not None else 1.20
        away_ga = pack.away.goals_against if pack.away.goals_against is not None else 1.35
        lambda_home = max(0.25, min(3.6, ((home_gf + away_ga) / 2) * 1.08))
        lambda_away = max(0.20, min(3.3, ((away_gf + home_ga) / 2) * 0.96))
        if pack.home.injuries_count and pack.home.injuries_count >= 3:
            lambda_home *= 0.94
        if pack.away.injuries_count and pack.away.injuries_count >= 3:
            lambda_away *= 0.94
        return lambda_home, lambda_away

    def _quality(self, pack: DataPack) -> DataQuality:
        score = 0.15
        reasons = []
        if pack.exact_match_found:
            score += 0.20
        else:
            reasons.append("Match exact non confirmé par les sources.")
        if pack.fixture_id:
            score += 0.10
        if pack.home.played and pack.away.played:
            score += 0.20
        else:
            reasons.append("Statistiques d'équipes incomplètes.")
        if pack.odds:
            score += 0.20
        else:
            reasons.append("Aucune cote marché exploitable.")
        ok_sources = [s for s in pack.source_status if s.ok]
        score += min(0.15, len(ok_sources) * 0.05)
        score = round(min(1.0, score), 3)
        verdict = "GOOD" if score >= 0.78 else "MEDIUM" if score >= 0.60 else "WEAK" if score >= 0.40 else "UNUSABLE"
        return DataQuality(score=score, verdict=verdict, reasons=reasons or ["Données exploitables."])

    def _signals(self, pack: DataPack, p: ProbabilitySet, q: float) -> list[MarketSignal]:
        candidates = [
            ("1X2", "HOME", p.home_win, "Victoire domicile"),
            ("1X2", "DRAW", p.draw, "Match nul"),
            ("1X2", "AWAY", p.away_win, "Victoire extérieur"),
            ("DOUBLE_CHANCE", "1X", p.home_or_draw, "Domicile ou nul"),
            ("DOUBLE_CHANCE", "12", p.home_or_away, "Pas de nul"),
            ("DOUBLE_CHANCE", "X2", p.draw_or_away, "Nul ou extérieur"),
            ("BTTS", "YES", p.btts_yes, "Les deux équipes marquent"),
            ("BTTS", "NO", p.btts_no, "Au moins une équipe ne marque pas"),
            ("OVER_UNDER_2_5", "OVER_2_5", p.over_2_5, "Plus de 2.5 buts"),
            ("OVER_UNDER_2_5", "UNDER_2_5", p.under_2_5, "Moins de 2.5 buts"),
        ]
        out = []
        for market, selection, prob, rationale in candidates:
            quote = best_price(pack.odds, market, selection)
            fo = fair_odds(prob)
            if quote:
                e = edge(prob, quote.price)
                roi = expected_roi(prob, quote.price)
                status = "VALIDATED" if e >= self.settings.edge_min and q >= self.settings.data_confidence_min else "NO_VALUE"
                best_odds = quote.price
            else:
                e = None
                roi = None
                best_odds = None
                status = "LEAN" if prob >= 0.68 and q >= 0.55 else "NO_PRICE"
            out.append(MarketSignal(market=market, selection=selection, probability=prob, fair_odds=fo, best_odds=best_odds, edge=e, roi_estimate=roi, confidence=round(q * prob, 3), status=status, rationale=rationale))
        return sorted(out, key=lambda s: (s.status == "VALIDATED", s.edge or 0, s.confidence), reverse=True)

    def _council(self, quality: DataQuality, signals: list[MarketSignal], primary: MarketSignal | None) -> CouncilVerdict:
        risks = quality.reasons if quality.score < 0.70 else []
        recommendation = "NO BET par défaut : données ou value insuffisantes." if not primary else f"Signal principal : {primary.market} {primary.selection}."
        advisors = [
            AdvisorOutput(advisor="Contrarian", position="Cherche les pièges de marché", risks=risks, recommendation="Refuser si la cote ne dépasse pas la fair odds."),
            AdvisorOutput(advisor="First Principles", position="Valide la logique statistique", risks=quality.reasons, recommendation="Ne jamais confondre probabilité élevée et value bet."),
            AdvisorOutput(advisor="Executor", position="Transforme l'analyse en action", risks=[], recommendation=recommendation),
        ]
        return CouncilVerdict(where_agrees=["La décision doit dépendre de la qualité des données et de l'edge."], where_clashes=["Signal fort sans cote exploitable = surveillance, pas pari."], blind_spots=risks, recommendation=recommendation, first_action="Vérifier les lineups et les cotes proches du coup d'envoi.", advisors=advisors)
