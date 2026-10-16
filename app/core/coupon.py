"""Module Générateur de coupons.

Assemble plusieurs sélections (issues du Value Scanner) en un coupon combiné et
en chiffre honnêtement le profil : cote combinée, probabilité, espérance (EV) et
mise suggérée par Kelly fractionné.

Hypothèse explicite : les sélections sont traitées comme indépendantes (la proba
combinée est le produit des probas). C'est une approximation — deux marchés d'un
même match ne le sont pas. Un coupon combine aussi les risques : plus il y a de
jambes, plus la variance monte et plus la proba de tout gagner chute.
"""
from __future__ import annotations

from math import prod

from pydantic import BaseModel, Field


class CouponLeg(BaseModel):
    match: str
    market: str = ""
    selection_label: str = ""
    best_price: float
    fair_prob: float
    best_book: str = ""


class CouponRequest(BaseModel):
    legs: list[CouponLeg] = Field(default_factory=list)
    bankroll: float = 100.0
    kelly_fraction: float = 0.25  # on ne mise qu'une fraction du Kelly plein


class CouponResult(BaseModel):
    legs: list[CouponLeg]
    legs_count: int
    combined_odds: float
    combined_prob: float
    edge: float            # EV = cote_combinée × proba_combinée − 1
    kelly_full: float      # fraction de bankroll recommandée par Kelly plein
    stake: float           # mise suggérée (Kelly fractionné)
    potential_return: float
    warnings: list[str]


def build_coupon(req: CouponRequest) -> CouponResult:
    legs = [leg for leg in req.legs if leg.best_price > 1.0 and 0 < leg.fair_prob < 1]
    warnings: list[str] = []
    if not legs:
        return CouponResult(legs=[], legs_count=0, combined_odds=0.0, combined_prob=0.0,
                            edge=0.0, kelly_full=0.0, stake=0.0, potential_return=0.0,
                            warnings=["Aucune sélection valide."])

    combined_odds = round(prod(leg.best_price for leg in legs), 3)
    combined_prob = round(prod(leg.fair_prob for leg in legs), 4)
    edge = round(combined_odds * combined_prob - 1.0, 4)

    # Kelly : f = (b·p − q) / b, avec b = cote − 1. Négatif → on ne mise pas.
    b = combined_odds - 1.0
    kelly_full = round(max(0.0, (b * combined_prob - (1.0 - combined_prob)) / b), 4) if b > 0 else 0.0
    frac = min(max(req.kelly_fraction, 0.0), 1.0)
    stake = round(req.bankroll * kelly_full * frac, 2)
    potential_return = round(stake * combined_odds, 2)

    if len(legs) >= 4:
        warnings.append("4 jambes ou plus : la proba de tout gagner est faible, la variance très élevée.")
    if edge <= 0:
        warnings.append("Edge négatif : ce coupon n'a pas de value — à éviter.")
    if kelly_full == 0.0:
        warnings.append("Kelly nul ou négatif : aucune mise recommandée sur ce coupon.")

    return CouponResult(
        legs=legs, legs_count=len(legs), combined_odds=combined_odds,
        combined_prob=combined_prob, edge=edge, kelly_full=kelly_full,
        stake=stake, potential_return=potential_return, warnings=warnings,
    )
