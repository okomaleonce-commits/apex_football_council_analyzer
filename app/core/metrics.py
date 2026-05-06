from app.models import OddsQuote


def fair_odds(probability: float) -> float:
    return 999.0 if probability <= 0 else round(1.0 / probability, 3)


def implied_probability(odds: float) -> float:
    return 1.0 if odds <= 1 else round(1.0 / odds, 4)


def expected_roi(probability: float, odds: float) -> float:
    return round((probability * odds) - 1.0, 4)


def edge(probability: float, odds: float) -> float:
    return round(probability - implied_probability(odds), 4)


def best_price(odds: list[OddsQuote], market: str, selection: str) -> OddsQuote | None:
    candidates = [q for q in odds if q.market.lower() == market.lower() and q.selection.lower() == selection.lower()]
    return sorted(candidates, key=lambda q: q.price, reverse=True)[0] if candidates else None
