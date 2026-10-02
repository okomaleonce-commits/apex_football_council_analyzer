"""Pipeline d'analyse hockey : DataPack -> HockeyReport.

Réutilise au maximum la machinerie existante (edge/fair_odds/ROI, seuils de
`Settings`, structure de conseil multi-agents) pour rester cohérent avec le
moteur football, tout en appliquant des marchés et une calibration hockey.
"""

from __future__ import annotations

from app.core.hockey import compute_probabilities, estimate_lambdas
from app.core.metrics import best_price, edge, expected_roi, fair_odds
from app.models import (
    AdvisorOutput,
    CouncilVerdict,
    DataPack,
    DataQuality,
    HockeyProbabilitySet,
    HockeyReport,
    MarketSignal,
)

# Ligne de total de référence pour le marché principal (NHL : 5.5 le plus courant).
PRIMARY_TOTAL_LINE = "5.5"


class HockeyAnalyzer:
    def __init__(self, settings):
        self.settings = settings

    def analyze(self, pack: DataPack) -> HockeyReport:
        quality = self._quality(pack)
        lambda_home, lambda_away = estimate_lambdas(
            pack.home.goals_for, pack.home.goals_against,
            pack.away.goals_for, pack.away.goals_against,
        )
        probs_raw = compute_probabilities(lambda_home, lambda_away)
        probabilities = HockeyProbabilitySet(**probs_raw)
        signals = self._signals(pack, probs_raw, quality.score)

        validated = [s for s in signals if s.status == "VALIDATED"]
        lean = [s for s in signals if s.status == "LEAN"]
        primary = validated[0] if validated else None

        warnings: list[str] = []
        verdict = "NO_BET"
        if quality.score < self.settings.data_confidence_min:
            verdict = "WAIT_DATA" if quality.verdict != "UNUSABLE" else "NO_BET"
            warnings.append("Qualité des données insuffisante pour valider un pari.")
        elif primary:
            verdict = "BET"
        elif lean:
            verdict = "MONITOR_LIVE"
            warnings.append("Signal intéressant mais edge insuffisant ou cote absente.")

        if not pack.odds:
            warnings.append("Aucune cote hockey branchée : fair odds calculées, value non validable.")

        council = self._council(quality, primary)
        return HockeyReport(
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
                "sport": "hockey",
                "fixture_id": pack.fixture_id,
                "exact_match_found": pack.exact_match_found,
                "kickoff_utc": pack.kickoff_utc,
                "odds_count": len(pack.odds),
                "expected_total": probs_raw["expected_total"],
                "sources": [s.model_dump(mode="json") for s in pack.source_status],
            },
        )

    def _quality(self, pack: DataPack) -> DataQuality:
        score = 0.15
        reasons: list[str] = []
        if pack.exact_match_found:
            score += 0.20
        else:
            reasons.append("Match exact non confirmé par les sources.")
        if pack.fixture_id:
            score += 0.10
        if pack.home.played and pack.away.played:
            score += 0.20
        else:
            reasons.append("Statistiques d'équipes incomplètes (début de saison ?).")
        if pack.odds:
            score += 0.20
        else:
            reasons.append("Aucune cote hockey exploitable.")
        ok_sources = [s for s in pack.source_status if s.ok]
        score += min(0.15, len(ok_sources) * 0.05)
        score = round(min(1.0, score), 3)
        verdict = "GOOD" if score >= 0.78 else "MEDIUM" if score >= 0.60 else "WEAK" if score >= 0.40 else "UNUSABLE"
        return DataQuality(score=score, verdict=verdict, reasons=reasons or ["Données exploitables."])

    def _signals(self, pack: DataPack, p: dict, q: float) -> list[MarketSignal]:
        line = PRIMARY_TOTAL_LINE
        totals = p["totals"].get(line, {"over": 0.0, "under": 0.0})
        candidates = [
            ("MONEYLINE", "HOME", p["moneyline_home"], "Victoire domicile (inclut prolongation/TAB)"),
            ("MONEYLINE", "AWAY", p["moneyline_away"], "Victoire extérieur (inclut prolongation/TAB)"),
            (f"TOTAL_{line}", "OVER", totals["over"], f"Plus de {line} buts"),
            (f"TOTAL_{line}", "UNDER", totals["under"], f"Moins de {line} buts"),
            ("PUCK_LINE", "HOME_-1.5", p["puckline_home_minus_1_5"], "Domicile gagne par 2 buts ou plus (réglementaire)"),
            ("PUCK_LINE", "AWAY_+1.5", p["puckline_away_plus_1_5"], "Extérieur +1.5"),
        ]
        out: list[MarketSignal] = []
        for market, selection, prob, rationale in candidates:
            quote = best_price(pack.odds, market, selection)
            fo = fair_odds(prob)
            if quote:
                e = edge(prob, quote.price)
                roi = expected_roi(prob, quote.price)
                status = "VALIDATED" if e >= self.settings.edge_min and q >= self.settings.data_confidence_min else "NO_VALUE"
                best_odds = quote.price
            else:
                e = roi = best_odds = None
                status = "LEAN" if prob >= 0.68 and q >= 0.55 else "NO_PRICE"
            out.append(MarketSignal(
                market=market, selection=selection, probability=prob, fair_odds=fo,
                best_odds=best_odds, edge=e, roi_estimate=roi,
                confidence=round(q * prob, 3), status=status, rationale=rationale,
            ))
        return sorted(out, key=lambda s: (s.status == "VALIDATED", s.edge or 0, s.confidence), reverse=True)

    def _council(self, quality: DataQuality, primary: MarketSignal | None) -> CouncilVerdict:
        risks = quality.reasons if quality.score < 0.70 else []
        recommendation = (
            "NO BET par défaut : données ou value insuffisantes."
            if not primary else f"Signal principal : {primary.market} {primary.selection}."
        )
        advisors = [
            AdvisorOutput(advisor="Contrarian", position="Cherche les pièges de marché", risks=risks, recommendation="Refuser si la cote ne dépasse pas la fair odds."),
            AdvisorOutput(advisor="First Principles", position="Valide la logique statistique", risks=quality.reasons, recommendation="Le gardien partant et le repos (back-to-back) priment sur la moyenne de buts."),
            AdvisorOutput(advisor="Executor", position="Transforme l'analyse en action", risks=[], recommendation=recommendation),
        ]
        return CouncilVerdict(
            where_agrees=["La décision dépend de la qualité des données et de l'edge."],
            where_clashes=["Signal fort sans cote exploitable = surveillance, pas pari."],
            blind_spots=risks,
            recommendation=recommendation,
            first_action="Confirmer les gardiens partants et le repos (back-to-back) avant le coup d'envoi.",
            advisors=advisors,
        )
