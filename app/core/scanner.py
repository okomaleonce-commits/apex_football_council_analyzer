"""Value Scanner — détecte la value en comparant plusieurs bookmakers.

Méthode honnête, qui fonctionne à partir des cotes seules (pas besoin de stats
d'équipe) :

  1. Pour chaque marché d'un match, on lit les cotes de tous les bookmakers.
  2. Par bookmaker, on retire la marge (vig) : proba juste = (1/cote) / somme(1/cotes).
  3. La proba de consensus = moyenne des probas justes sur tous les books.
  4. Le meilleur prix = la cote la plus haute dispo pour cette issue.
  5. Edge (EV) = meilleur_prix × proba_consensus − 1.

Un edge positif = un bookmaker paie au-dessus du juste prix du marché. C'est la
définition d'un value bet — honnête, mesurable, et sans promesse de gain garanti.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from pydantic import BaseModel

from app.providers.odds_api import OddsAPIProvider

# Combien d'issues doit contenir un marché pour pouvoir le dé-marginer.
_GROUP_SIZE = {"1X2": 3, "DOUBLE_CHANCE": 3}  # défaut : 2 (over/under)

_LABELS = {
    "HOME": "Victoire domicile", "DRAW": "Match nul", "AWAY": "Victoire extérieur",
    "OVER_2_5": "Plus de 2.5 buts", "UNDER_2_5": "Moins de 2.5 buts",
}


class ValueSignal(BaseModel):
    match: str
    commence: str | None = None
    market: str
    selection: str
    selection_label: str
    fair_prob: float
    consensus_price: float
    best_price: float
    best_book: str
    books_count: int
    edge: float  # EV relatif au consensus = best_price * fair_prob - 1


def scan_event(event: dict[str, Any], edge_min: float = 0.0) -> list[ValueSignal]:
    """Scanne un événement brut (format The Odds API) et renvoie ses value signals."""
    home = str(event.get("home_team", ""))
    away = str(event.get("away_team", ""))
    commence = event.get("commence_time")
    match = f"{home} – {away}"

    # groups[group_id][book] = {selection: price}
    groups: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    group_market: dict[str, str] = {}

    for book in event.get("bookmakers", []):
        book_name = book.get("title") or book.get("key") or "?"
        for md in book.get("markets", []):
            mkey = md.get("key", "")
            if mkey not in ("h2h", "totals"):
                continue
            for outcome in md.get("outcomes", []):
                price = outcome.get("price")
                if not price:
                    continue
                market, selection = OddsAPIProvider.normalize_selection(
                    mkey, outcome.get("name", ""), home, away, outcome.get("point")
                )
                if mkey == "totals":
                    # On ne garde que les totals 2.5 pour rester lisible.
                    if selection not in ("OVER_2_5", "UNDER_2_5"):
                        continue
                    market = "OVER_UNDER_2_5"
                    gid = f"OVER_UNDER@{outcome.get('point')}"  # OVER et UNDER dans le même groupe
                else:
                    gid = market
                groups[gid][book_name][selection] = float(price)
                group_market[gid] = market

    signals: list[ValueSignal] = []
    for gid, books in groups.items():
        fair_accum: dict[str, list[float]] = defaultdict(list)
        best: dict[str, tuple[float, str]] = {}
        price_accum: dict[str, list[float]] = defaultdict(list)
        market = group_market[gid]
        need = _GROUP_SIZE.get(market, 2)

        for book_name, sels in books.items():
            if len(sels) < need:
                continue  # marché incomplet chez ce book : inutilisable pour dé-marger
            overround = sum(1.0 / p for p in sels.values())
            if overround <= 0:
                continue
            for sel, p in sels.items():
                fair_accum[sel].append((1.0 / p) / overround)
                price_accum[sel].append(p)
                if sel not in best or p > best[sel][0]:
                    best[sel] = (p, book_name)

        for sel, fairs in fair_accum.items():
            books_count = len(fairs)
            if books_count < 2:
                continue  # consensus non fiable avec un seul book
            fair = sum(fairs) / books_count
            best_price, best_book = best[sel]
            consensus_price = sum(price_accum[sel]) / len(price_accum[sel])
            edge = round(best_price * fair - 1.0, 4)
            if edge < edge_min:
                continue
            signals.append(ValueSignal(
                match=match, commence=commence, market=market, selection=sel,
                selection_label=_LABELS.get(sel, sel), fair_prob=round(fair, 4),
                consensus_price=round(consensus_price, 3), best_price=round(best_price, 3),
                best_book=best_book, books_count=books_count, edge=edge,
            ))
    return signals


def scan_payload(payload: Any, edge_min: float = 0.0, limit: int = 40) -> list[ValueSignal]:
    """Scanne un payload complet (liste d'événements) et renvoie les meilleurs signaux."""
    events = payload if isinstance(payload, list) else payload.get("data") or payload.get("response") or []
    out: list[ValueSignal] = []
    for event in events:
        out.extend(scan_event(event, edge_min=edge_min))
    out.sort(key=lambda s: (s.edge, s.books_count), reverse=True)
    return out[:limit]


def demo_signals() -> list[ValueSignal]:
    """Tableau de démonstration quand aucune clé de cotes n'est configurée."""
    raw = [
        ("Olympique Lyonnais – FC Nantes", "OVER_UNDER_2_5", "OVER_2_5", 0.54, 2.02, 2.15, "Pinnacle", 7, 0.077),
        ("Lille – Stade Rennais", "1X2", "HOME", 0.48, 1.95, 2.10, "Betclic", 8, 0.052),
        ("Monaco – Lens", "OVER_UNDER_2_5", "UNDER_2_5", 0.49, 1.98, 2.08, "Unibet", 6, 0.028),
        ("Marseille – Nice", "1X2", "DRAW", 0.27, 3.55, 3.90, "Winamax", 7, 0.053),
    ]
    return [ValueSignal(
        match=m, commence=None, market=mk, selection=s, selection_label=_LABELS.get(s, s),
        fair_prob=fp, consensus_price=cp, best_price=bp, best_book=bb, books_count=bc, edge=e,
    ) for m, mk, s, fp, cp, bp, bb, bc, e in raw]
