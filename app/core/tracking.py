"""Suivi des prédictions pour PROUVER l'edge avant tout pari en argent réel.

Correction #1 du conseil : tant qu'on n'a pas mesuré, sur un historique réglé,
un Brier/log-loss corrects ET une Closing Line Value (CLV) positive, le système
ne doit jamais prétendre détecter de la value exploitable.

Dépendances : stdlib uniquement (sqlite3). Aucune donnée inventée.
"""
from __future__ import annotations

import math
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class PredictionTracker:
    def __init__(self, path: str = "/tmp/apex_tracking.sqlite3"):
        self.path = Path(path)
        self._init()

    def _init(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    match_key TEXT NOT NULL,
                    market TEXT NOT NULL,
                    selection TEXT NOT NULL,
                    model_prob REAL NOT NULL,
                    market_prob REAL,
                    best_odds REAL,
                    edge REAL,
                    verdict TEXT,
                    -- règlement a posteriori (NULL tant que non réglé)
                    settled INTEGER NOT NULL DEFAULT 0,
                    won INTEGER,
                    closing_odds REAL
                )
                """
            )
            conn.commit()

    @staticmethod
    def match_key(report: Any) -> str:
        r = report.request
        return f"{r.match_date}|{r.league}|{r.home}|{r.away}"

    def log_report(self, report: Any) -> int:
        """Enregistre les signaux chiffrés d'un rapport. Retourne le nb de lignes."""
        key = self.match_key(report)
        rows = []
        signals = list(report.market_signals or [])
        for s in signals:
            if s.market_prob is None and s.best_odds is None:
                continue  # rien de mesurable sans cote
            rows.append(
                (
                    datetime.utcnow().isoformat(),
                    key,
                    s.market,
                    s.selection,
                    float(s.probability),
                    None if s.market_prob is None else float(s.market_prob),
                    None if s.best_odds is None else float(s.best_odds),
                    None if s.edge is None else float(s.edge),
                    s.status,
                )
            )
        if not rows:
            return 0
        with sqlite3.connect(self.path) as conn:
            conn.executemany(
                """INSERT INTO predictions
                   (created_at, match_key, market, selection, model_prob,
                    market_prob, best_odds, edge, verdict)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                rows,
            )
            conn.commit()
        return len(rows)

    def log_entry(self, match_key: str, market: str, selection: str, model_prob: float,
                  market_prob: float | None, taken_odds: float | None, verdict: str = "") -> int:
        """Enregistre UNE prédiction avec la cote PRISE (entrée). Retourne son id.

        Sert au flux CLV : la cote de clôture sera renseignée plus tard via
        record_closing(), puis le résultat via settle().
        """
        edge = None if market_prob is None else round(model_prob - market_prob, 4)
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute(
                """INSERT INTO predictions
                   (created_at, match_key, market, selection, model_prob,
                    market_prob, best_odds, edge, verdict)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (datetime.utcnow().isoformat(), match_key, market, selection,
                 float(model_prob), market_prob, taken_odds, edge, verdict),
            )
            conn.commit()
            return int(cur.lastrowid)

    def record_closing(self, prediction_id: int, closing_odds: float) -> None:
        """Renseigne la cote de CLÔTURE (près du coup d'envoi) sans régler le pari."""
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "UPDATE predictions SET closing_odds = ? WHERE id = ?",
                (float(closing_odds), prediction_id),
            )
            conn.commit()

    def settle(self, prediction_id: int, won: bool, closing_odds: float | None = None) -> None:
        """Règle le pari (résultat). closing_odds optionnelle si pas déjà archivée."""
        with sqlite3.connect(self.path) as conn:
            if closing_odds is None:
                conn.execute(
                    "UPDATE predictions SET settled = 1, won = ? WHERE id = ?",
                    (1 if won else 0, prediction_id),
                )
            else:
                conn.execute(
                    "UPDATE predictions SET settled = 1, won = ?, closing_odds = ? WHERE id = ?",
                    (1 if won else 0, float(closing_odds), prediction_id),
                )
            conn.commit()

    def pending_closings(self) -> list[dict]:
        """Prédictions dont la cote de clôture n'est pas encore archivée."""
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                """SELECT id, match_key, market, selection, best_odds
                   FROM predictions WHERE closing_odds IS NULL"""
            ).fetchall()
        return [{"id": r[0], "match_key": r[1], "market": r[2], "selection": r[3], "taken_odds": r[4]} for r in rows]

    def pending_settlements(self) -> list[dict]:
        """Prédictions pas encore réglées (résultat manquant)."""
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                """SELECT id, match_key, market, selection
                   FROM predictions WHERE settled = 0"""
            ).fetchall()
        return [{"id": r[0], "match_key": r[1], "market": r[2], "selection": r[3]} for r in rows]

    def calibration_report(self, min_settled: int = 100) -> dict[str, Any]:
        with sqlite3.connect(self.path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
            rows = conn.execute(
                """SELECT model_prob, won, best_odds, closing_odds
                   FROM predictions WHERE settled = 1 AND won IS NOT NULL"""
            ).fetchall()

        settled = len(rows)
        if settled == 0:
            return {
                "total_predictions": total,
                "settled": 0,
                "brier": None,
                "log_loss": None,
                "clv": None,
                "proven": False,
                "message": "Aucun pari réglé : edge NON prouvé. Mode conseil uniquement.",
            }

        brier_sum = 0.0
        ll_sum = 0.0
        clv_vals: list[float] = []
        eps = 1e-12
        for model_prob, won, best_odds, closing_odds in rows:
            p = min(max(float(model_prob), eps), 1 - eps)
            y = 1.0 if won else 0.0
            brier_sum += (p - y) ** 2
            ll_sum += -(y * math.log(p) + (1 - y) * math.log(1 - p))
            if best_odds and closing_odds and closing_odds > 1.0:
                # CLV : a-t-on battu la cote de clôture ? (prob implicite de clôture
                # vs prob implicite de notre prise). Positive = bon timing/edge.
                clv_vals.append((1.0 / closing_odds) - (1.0 / best_odds) if best_odds > 1.0 else 0.0)

        brier = round(brier_sum / settled, 4)
        log_loss = round(ll_sum / settled, 4)
        clv = round(sum(clv_vals) / len(clv_vals), 4) if clv_vals else None
        clv_pct_beat = round(sum(1 for v in clv_vals if v > 0) / len(clv_vals), 4) if clv_vals else None
        # "Proven" : échantillon suffisant, calibration meilleure que le hasard
        # (Brier < 0.25), et CLV strictement positive.
        proven = settled >= min_settled and brier < 0.25 and clv is not None and clv > 0
        return {
            "total_predictions": total,
            "settled": settled,
            "brier": brier,
            "log_loss": log_loss,
            "clv": clv,
            "clv_sample": len(clv_vals),
            "clv_pct_beat_close": clv_pct_beat,
            "proven": proven,
            "message": (
                "Edge prouvé sur l'historique réglé."
                if proven
                else "Edge NON prouvé (échantillon/Brier/CLV insuffisants). Mode conseil uniquement."
            ),
        }
