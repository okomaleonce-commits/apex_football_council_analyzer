#!/usr/bin/env python3
"""Archivage quotidien des cotes pour la CLV.

Flux en 3 temps (une prédiction par ligne du tracker) :
  1. ENTRÉE   : la cote PRISE est enregistrée au moment du signal
               (FootballAnalyzer -> tracker.log_report, ou tracker.log_entry).
  2. CLÔTURE  : près du coup d'envoi, on archive la cote de CLÔTURE.
  3. RÉSULTAT : après le match, on règle (won/lost).
La CLV = (1/cote_clôture) - (1/cote_prise), moyennée. Positive = on a battu la clôture.

Usage (cron) :
  python -m scripts.archive_odds pending
  python -m scripts.archive_odds close   closings.json    # [{"prediction_id":1,"closing_odds":2.10}, ...]
  python -m scripts.archive_odds settle  results.json     # [{"prediction_id":1,"won":true,"closing_odds":2.10}, ...]
  python -m scripts.archive_odds report

Exemple de cron (clôtures à T-5 min, résultats chaque nuit) :
  */30 * * * *  cd /app && python -m scripts.archive_odds close  /data/closings.json
  0    6 * * *  cd /app && python -m scripts.archive_odds settle /data/results.json && python -m scripts.archive_odds report
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.tracking import PredictionTracker
from app.settings import get_settings


def _tracker() -> PredictionTracker:
    return PredictionTracker(get_settings().tracking_db_path)


def cmd_pending(_args: list[str]) -> None:
    t = _tracker()
    c = t.pending_closings()
    s = t.pending_settlements()
    print(f"En attente de CLÔTURE : {len(c)}")
    for r in c[:50]:
        print(f"  #{r['id']} {r['match_key']} {r['market']}:{r['selection']} (prise {r['taken_odds']})")
    print(f"En attente de RÉSULTAT : {len(s)}")
    for r in s[:50]:
        print(f"  #{r['id']} {r['match_key']} {r['market']}:{r['selection']}")


def _load(path: str) -> list[dict]:
    data = json.loads(Path(path).read_text())
    if not isinstance(data, list):
        raise SystemExit("Le fichier doit être une liste JSON d'objets.")
    return data


def cmd_close(args: list[str]) -> None:
    if not args:
        raise SystemExit("usage: archive_odds close <closings.json>")
    t = _tracker()
    n = 0
    for row in _load(args[0]):
        pid = int(row["prediction_id"]); odds = float(row["closing_odds"])
        if odds <= 1.0:
            print(f"  ignoré #{pid} : cote de clôture invalide ({odds})"); continue
        t.record_closing(pid, odds); n += 1
    print(f"{n} cote(s) de clôture archivée(s).")


def cmd_settle(args: list[str]) -> None:
    if not args:
        raise SystemExit("usage: archive_odds settle <results.json>")
    t = _tracker()
    n = 0
    for row in _load(args[0]):
        pid = int(row["prediction_id"]); won = bool(row["won"])
        closing = row.get("closing_odds")
        t.settle(pid, won=won, closing_odds=None if closing is None else float(closing)); n += 1
    print(f"{n} prédiction(s) réglée(s).")


def cmd_report(_args: list[str]) -> None:
    rep = _tracker().calibration_report(min_settled=get_settings().min_settled_bets)
    print("=== CALIBRATION / CLV ===")
    for k, v in rep.items():
        print(f"  {k}: {v}")


CMDS = {"pending": cmd_pending, "close": cmd_close, "settle": cmd_settle, "report": cmd_report}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        print(__doc__); raise SystemExit(2)
    CMDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
