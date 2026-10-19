from math import sqrt

from app.models import OddsQuote

# Ensembles de sélections mutuellement exclusives et exhaustives (MECE) par
# marché : indispensables pour retirer la marge (dévig) correctement.
MECE_MARKETS: dict[str, list[str]] = {
    "1X2": ["HOME", "DRAW", "AWAY"],
    "BTTS": ["YES", "NO"],
    "OVER_UNDER_2_5": ["OVER_2_5", "UNDER_2_5"],
}


def fair_odds(probability: float) -> float:
    return 999.0 if probability <= 0 else round(1.0 / probability, 3)


def implied_probability(odds: float) -> float:
    """Probabilité implicite BRUTE (marge incluse). Ne pas utiliser pour l'edge."""
    return 1.0 if odds <= 1 else round(1.0 / odds, 4)


def devig_proportional(prices: list[float]) -> list[float]:
    """Retrait de marge proportionnel : normalise 1/cote pour sommer à 1."""
    inv = [1.0 / p for p in prices if p > 1.0]
    s = sum(inv) or 1.0
    return [x / s for x in inv]


def devig_shin(prices: list[float], max_iter: int = 100) -> list[float]:
    """Retrait de marge par la méthode de Shin (1992).

    Modélise une proportion z de paris "informés" et corrige le biais
    favori/outsider que la méthode proportionnelle ignore. Repli sur le
    proportionnel si la résolution numérique échoue.
    """
    inv = [1.0 / p for p in prices if p > 1.0]
    booksum = sum(inv)
    if booksum <= 1.0 or len(inv) < 2:
        return devig_proportional(prices)

    def probs(z: float) -> list[float]:
        z = min(max(z, 0.0), 0.999)
        out = []
        for q in inv:
            val = z * z + 4.0 * (1.0 - z) * q * q / booksum
            out.append((sqrt(max(val, 0.0)) - z) / (2.0 * (1.0 - z)))
        return out

    # f(z) = somme des probabilités - 1 ; décroissante en z. Bissection sur [0, 0.5].
    lo, hi = 0.0, 0.5
    if sum(probs(lo)) - 1.0 < 0:  # déjà sous 1 à z=0 -> rien à corriger
        return devig_proportional(prices)
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        if sum(probs(mid)) - 1.0 > 0:
            lo = mid
        else:
            hi = mid
    p = probs((lo + hi) / 2.0)
    s = sum(p)
    if s <= 0:
        return devig_proportional(prices)
    return [x / s for x in p]


def remove_vig(prices: list[float], method: str = "shin") -> list[float]:
    try:
        if method == "shin":
            return devig_shin(prices)
        return devig_proportional(prices)
    except Exception:
        return devig_proportional(prices)


def expected_roi(probability: float, odds: float) -> float:
    return round((probability * odds) - 1.0, 4)


def edge(probability: float, market_prob: float) -> float:
    """Edge = proba modèle - VRAIE proba de marché (marge déjà retirée)."""
    return round(probability - market_prob, 4)


def best_price(odds: list[OddsQuote], market: str, selection: str) -> OddsQuote | None:
    candidates = [q for q in odds if q.market.lower() == market.lower() and q.selection.lower() == selection.lower()]
    return sorted(candidates, key=lambda q: q.price, reverse=True)[0] if candidates else None


def true_market_probs(odds: list[OddsQuote], market: str, method: str = "shin") -> dict[str, float] | None:
    """Vraies probabilités de marché (marge retirée) pour un marché MECE.

    Retourne None si le marché n'est pas complet (toutes les sélections cotées),
    car on ne peut pas retirer la marge sans l'ensemble complet.
    """
    selections = MECE_MARKETS.get(market)
    if not selections:
        return None
    prices: list[float] = []
    for sel in selections:
        quote = best_price(odds, market, sel)
        if quote is None or quote.price <= 1.0:
            return None
        prices.append(quote.price)
    fair = remove_vig(prices, method)
    result = {sel: round(fair[i], 4) for i, sel in enumerate(selections)}
    result["_overround"] = round(sum(1.0 / p for p in prices) - 1.0, 4)
    return result


def double_chance_true_probs(x2_true: dict[str, float] | None) -> dict[str, float] | None:
    """Dérive les vraies probas Double Chance depuis le 1X2 déjà dévigé."""
    if not x2_true:
        return None
    h, d, a = x2_true.get("HOME"), x2_true.get("DRAW"), x2_true.get("AWAY")
    if h is None or d is None or a is None:
        return None
    return {
        "1X": round(h + d, 4),
        "12": round(h + a, 4),
        "X2": round(d + a, 4),
        "_overround": x2_true.get("_overround", 0.0),
    }
