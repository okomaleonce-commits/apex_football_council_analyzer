from __future__ import annotations

from app.core.metrics import (
    best_price,
    double_chance_true_probs,
    edge,
    expected_roi,
    fair_odds,
    true_market_probs,
)
from app.core.poisson import compute_probabilities, calibrate_probabilities
from app.models import (
    AdvisorOutput,
    AnalysisReport,
    CouncilVerdict,
    DataPack,
    DataQuality,
    MarketSignal,
    ProbabilitySet,
    StakePlan,
)

COUNCIL_DISCLAIMER = (
    "Ce 'conseil' est un ensemble de règles déterministes (pas une délibération "
    "multi-LLM). Aucun agent n'émet d'avis indépendant ; les positions ci-dessous "
    "décrivent les garde-fous appliqués par le code."
)


class FootballAnalyzer:
    def __init__(self, settings):
        self.settings = settings

    def analyze(self, pack: DataPack, calibration: dict | None = None) -> AnalysisReport:
        calibration = calibration or {}
        # Correction #1 : tant que l'edge n'est pas prouvé (CLV/Brier sur
        # historique réglé), on reste en mode conseil, jamais en pari réel.
        proven = bool(self.settings.calibration_proven) or bool(calibration.get("proven"))
        advisory_only = not proven

        quality = self._quality(pack)
        lambda_home, lambda_away, defaults_used = self._estimate_lambdas(pack)
        raw = compute_probabilities(
            lambda_home,
            lambda_away,
            max_goals=self.settings.max_goals,
            rho=self.settings.dc_rho,
        )
        # Calibration anti-surconfiance (backtest : Brier test < 0.25).
        probabilities = ProbabilitySet(**calibrate_probabilities(raw, self.settings))
        signals = self._signals(pack, probabilities, quality.score)
        validated = [s for s in signals if s.status == "VALIDATED"]
        lean = [s for s in signals if s.status == "LEAN"]
        primary = validated[0] if validated else None

        warnings: list[str] = []

        # --- Correction #4 : kill-switches booléens (remplacent le gate additif) ---
        hard_block = False
        if not pack.exact_match_found:
            hard_block = True
            warnings.append("KILL-SWITCH : match exact non confirmé par les sources.")
        if defaults_used:
            hard_block = True
            warnings.append(
                "KILL-SWITCH : statistiques d'équipes absentes — le modèle tournerait "
                "sur des lambdas par défaut. Aucune probabilité fiable, aucun pari."
            )
        if not pack.odds:
            warnings.append("Aucune cote exploitable : pas de value validée possible.")

        # --- Verdict ---
        if hard_block:
            verdict = "WAIT_DATA"
            primary = None
        elif quality.score < self.settings.data_confidence_min:
            verdict = "WAIT_DATA" if quality.verdict != "UNUSABLE" else "NO_BET"
            warnings.append("Qualité des données insuffisante pour valider un pari.")
            primary = None
        elif primary:
            verdict = "BET"
        elif lean:
            verdict = "MONITOR_LIVE"
            warnings.append("Signal intéressant mais edge insuffisant ou cote absente.")
        else:
            verdict = "NO_BET"

        # --- Correction #1 : gate advisory (dégrade BET tant que non prouvé) ---
        if advisory_only and verdict == "BET":
            verdict = "MONITOR_LIVE"
            warnings.append(
                "ADVISORY-ONLY : edge non prouvé (calibration/CLV absente). Signal "
                "fourni à titre de structuration, PAS pour miser de l'argent réel."
            )

        # --- Correction #5 : flat staking (Kelly désactivé tant que non prouvé) ---
        stake_plan = self._stake_plan(advisory_only, verdict)

        council = self._council(quality, signals, primary if verdict == "BET" else None, advisory_only)

        return AnalysisReport(
            request=pack.request,
            data_quality=quality,
            probabilities=probabilities,
            market_signals=signals,
            final_verdict=verdict,
            primary_bet=primary if verdict == "BET" else None,
            alternatives=(validated[1:4] if primary else lean[:3]),
            council=council,
            stake_plan=stake_plan,
            advisory_only=advisory_only,
            calibration=calibration,
            warnings=warnings,
            data_pack_summary={
                "fixture_id": pack.fixture_id,
                "exact_match_found": pack.exact_match_found,
                "kickoff_utc": pack.kickoff_utc,
                "odds_count": len(pack.odds),
                "defaults_used": defaults_used,
                "devig_method": self.settings.devig_method,
                "sources": [s.model_dump(mode="json") for s in pack.source_status],
            },
        )

    def _rate(self, goals: float | None, played: int | None, fallback: float) -> tuple[float, bool]:
        """Retourne (taux par match, defaut_utilise)."""
        if goals is None:
            return fallback, True
        if played and played > 0 and goals > 5:  # 'goals' ressemble à un total -> par match
            return goals / played, False
        return goals, False

    def _estimate_lambdas(self, pack: DataPack) -> tuple[float, float, bool]:
        """Correction #2 : forces relatives normalisées par la ligue (modèle
        multiplicatif type Maher), à la place d'une moyenne arithmétique.

        lambda_home = lg * attaque_home * defense_away * home_adv
        lambda_away = lg * attaque_away * defense_home * away_adj
        """
        s = self.settings
        hgf, d1 = self._rate(pack.home.goals_for, pack.home.played, 1.45)
        hga, d2 = self._rate(pack.home.goals_against, pack.home.played, 1.15)
        agf, d3 = self._rate(pack.away.goals_for, pack.away.played, 1.20)
        aga, d4 = self._rate(pack.away.goals_against, pack.away.played, 1.35)
        defaults_used = d1 or d2 or d3 or d4

        lg = s.league_avg_goals or 1.35
        # Forces relatives (1.0 = moyenne de la ligue).
        atk_home = max(0.2, hgf / lg)
        def_home = max(0.2, hga / lg)
        atk_away = max(0.2, agf / lg)
        def_away = max(0.2, aga / lg)

        lambda_home = lg * atk_home * def_away * s.home_adv
        lambda_away = lg * atk_away * def_home * s.away_adj

        # Ajustement blessures proportionnel (grossier mais borné).
        if pack.home.injuries_count and pack.home.injuries_count >= 3:
            lambda_home *= 0.94
        if pack.away.injuries_count and pack.away.injuries_count >= 3:
            lambda_away *= 0.94

        lambda_home = max(0.25, min(3.6, lambda_home))
        lambda_away = max(0.20, min(3.3, lambda_away))
        return lambda_home, lambda_away, defaults_used

    def _quality(self, pack: DataPack) -> DataQuality:
        """Score de COMPLÉTUDE (indicatif). Ne sert plus de gate principal :
        les kill-switches booléens décident (voir analyze)."""
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
        method = self.settings.devig_method
        # Correction #3 : vraies probas de marché (marge retirée) par marché MECE.
        true_1x2 = true_market_probs(pack.odds, "1X2", method)
        true_btts = true_market_probs(pack.odds, "BTTS", method)
        true_ou = true_market_probs(pack.odds, "OVER_UNDER_2_5", method)
        true_dc = double_chance_true_probs(true_1x2)

        def market_prob(market: str, selection: str) -> tuple[float | None, float | None]:
            src = {
                "1X2": true_1x2,
                "BTTS": true_btts,
                "OVER_UNDER_2_5": true_ou,
                "DOUBLE_CHANCE": true_dc,
            }.get(market)
            if not src:
                return None, None
            mp = src.get(selection)
            return (None if mp is None else float(mp)), src.get("_overround")

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
            mp, overround = market_prob(market, selection)
            if quote and mp is not None:
                # Edge contre la VRAIE proba de marché (marge retirée).
                e = edge(prob, mp)
                roi = expected_roi(prob, quote.price)
                status = "VALIDATED" if e >= self.settings.edge_min and q >= self.settings.data_confidence_min else "NO_VALUE"
                best_odds = quote.price
            elif quote:
                # Cote présente mais marché incomplet : impossible de dévigger.
                e = None
                roi = expected_roi(prob, quote.price)
                best_odds = quote.price
                status = "NO_VALUE"
            else:
                e = None
                roi = None
                best_odds = None
                status = "LEAN" if prob >= 0.68 and q >= 0.55 else "NO_PRICE"
            out.append(
                MarketSignal(
                    market=market,
                    selection=selection,
                    probability=prob,
                    fair_odds=fo,
                    best_odds=best_odds,
                    market_prob=mp,
                    overround=overround,
                    edge=e,
                    roi_estimate=roi,
                    confidence=round(q * prob, 3),
                    status=status,
                    rationale=rationale,
                )
            )
        return sorted(out, key=lambda s: (s.status == "VALIDATED", s.edge or 0, s.confidence), reverse=True)

    def _stake_plan(self, advisory_only: bool, verdict: str) -> StakePlan:
        if advisory_only or verdict != "BET":
            return StakePlan(
                method="none",
                stake_pct=0.0,
                note=(
                    "Aucune mise : edge non prouvé. Kelly désactivé tant que la "
                    "calibration (Brier/log-loss/CLV) n'est pas validée."
                ),
            )
        return StakePlan(
            method="flat",
            stake_pct=self.settings.flat_stake_pct,
            note=(
                f"Mise fixe {self.settings.flat_stake_pct:.1%} de bankroll. "
                "Kelly volontairement désactivé : il amplifie la ruine sur des "
                "probabilités non parfaitement calibrées."
            ),
        )

    def _council(self, quality: DataQuality, signals: list[MarketSignal], primary: MarketSignal | None, advisory_only: bool) -> CouncilVerdict:
        risks = quality.reasons if quality.score < 0.70 else []
        if advisory_only:
            recommendation = "ADVISORY-ONLY : edge non prouvé, ne pas miser d'argent réel."
        elif primary:
            recommendation = f"Signal principal : {primary.market} {primary.selection} (edge dévigé {primary.edge})."
        else:
            recommendation = "NO BET par défaut : données ou value insuffisantes."
        advisors = [
            AdvisorOutput(advisor="Règle Contrarian", position="Rejette si l'edge dévigé ne dépasse pas le seuil", risks=risks, recommendation="Comparer au marché démargé, jamais à la cote brute."),
            AdvisorOutput(advisor="Règle First Principles", position="Valide la logique statistique (Dixon-Coles)", risks=quality.reasons, recommendation="Ne jamais confondre probabilité élevée et value bet."),
            AdvisorOutput(advisor="Règle Risk Manager", position="Mise fixe, Kelly désactivé", risks=[], recommendation=recommendation),
        ]
        return CouncilVerdict(
            where_agrees=["La décision dépend des kill-switches de données ET de l'edge dévigé."],
            where_clashes=["Signal fort sans marché complet = pas de value mesurable."],
            blind_spots=risks,
            recommendation=recommendation,
            first_action="Vérifier les lineups et les cotes proches du coup d'envoi.",
            advisors=advisors,
            engine="rules",
            disclaimer=COUNCIL_DISCLAIMER,
        )
