"""Moteur de probabilités hockey sur glace (calibré NHL).

Pourquoi un module séparé du football
--------------------------------------
Le hockey ne se modélise pas comme le football :
- ~6.1 buts/match en moyenne NHL (contre ~2.7 en football) ;
- pas de nul au classement « moneyline » : une égalité à la fin du temps
  réglementaire se décide en prolongation (OT) puis tirs au but (SO) ;
- l'avantage de la glace est réel mais modeste (~52-55% de victoires à domicile) ;
- marchés propres : moneyline (inclut OT/SO), ligne réglementaire 3 voies,
  totaux (ligne 5.5 par défaut, aussi 4.5 / 6.5) et puck line (±1.5).

Appliquer le Poisson football à ces chiffres produit des probabilités fausses :
c'est exactement la contamination que la garde hors-domaine (`app/core/sports.py`)
est censée empêcher. Ce module fournit l'alternative calibrée.

Hypothèses et limites (assumées)
---------------------------------
- Poisson indépendant par équipe sur le temps réglementaire. Pas de correction
  Dixon-Coles hockey (la dépendance des scores est plus faible qu'en football).
- Le partage de la prolongation entre les deux équipes est une régression douce
  vers 50/50 pondérée par la force offensive relative.
- Les buts en cage vide (empty-net) sont déjà inclus dans la moyenne ligue, donc
  pas de ré-ajout explicite.
Ce sont des approximations raisonnables, pas une vérité de marché. En début de
saison (aucun match joué), le contrôle qualité dégrade le verdict, par cohérence
avec la discipline APEX (ne pas publier de signal sur échantillon vide).
"""

from __future__ import annotations

from math import exp, factorial

# --- Calibration NHL (ajustable) -------------------------------------------
HOCKEY_TEAM_AVG = 3.05          # buts/match par équipe (≈ 6.1 total)
HOCKEY_HOME_ADV = 1.06          # multiplicateur buts domicile (avantage glace)
HOCKEY_AWAY_ADJ = 0.97          # ajustement buts extérieur
OT_REGRESSION = 0.60            # régression du partage prolongation vers 50/50
LAMBDA_BOUNDS_HOME = (1.2, 5.5)
LAMBDA_BOUNDS_AWAY = (1.0, 5.2)
DEFAULT_TOTAL_LINES = (4.5, 5.5, 6.5)


def poisson_pmf(lmbda: float, goals: int) -> float:
    return (lmbda ** goals) * exp(-lmbda) / factorial(goals)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def estimate_lambdas(
    home_gf: float | None,
    home_ga: float | None,
    away_gf: float | None,
    away_ga: float | None,
) -> tuple[float, float]:
    """Buts attendus (temps réglementaire) depuis les buts pour/contre par match."""
    hgf = home_gf if home_gf is not None else HOCKEY_TEAM_AVG + 0.05
    hga = home_ga if home_ga is not None else HOCKEY_TEAM_AVG - 0.05
    agf = away_gf if away_gf is not None else HOCKEY_TEAM_AVG - 0.05
    aga = away_ga if away_ga is not None else HOCKEY_TEAM_AVG + 0.05
    lambda_home = _clamp(((hgf + aga) / 2) * HOCKEY_HOME_ADV, *LAMBDA_BOUNDS_HOME)
    lambda_away = _clamp(((agf + hga) / 2) * HOCKEY_AWAY_ADJ, *LAMBDA_BOUNDS_AWAY)
    return round(lambda_home, 3), round(lambda_away, 3)


def _overtime_home_share(lambda_home: float, lambda_away: float) -> float:
    strength = lambda_home / (lambda_home + lambda_away)
    share = 0.5 + OT_REGRESSION * (strength - 0.5)
    return _clamp(share, 0.35, 0.65)


def compute_probabilities(
    lambda_home: float,
    lambda_away: float,
    total_lines: tuple[float, ...] = DEFAULT_TOTAL_LINES,
    max_goals: int = 12,
) -> dict:
    """Probabilités des marchés hockey à partir des buts attendus réglementaires."""
    matrix = [
        [poisson_pmf(lambda_home, h) * poisson_pmf(lambda_away, a) for a in range(max_goals + 1)]
        for h in range(max_goals + 1)
    ]
    total = sum(sum(row) for row in matrix) or 1.0

    reg_home = reg_tie = reg_away = 0.0
    margin_ge2 = margin_le_minus2 = 0.0
    totals = {line: 0.0 for line in total_lines}  # proba OVER de chaque ligne
    scores = []
    for h, row in enumerate(matrix):
        for a, p in enumerate(row):
            if h > a:
                reg_home += p
            elif h == a:
                reg_tie += p
            else:
                reg_away += p
            if h - a >= 2:
                margin_ge2 += p
            if a - h >= 2:
                margin_le_minus2 += p
            for line in total_lines:
                if h + a > line:
                    totals[line] += p
            scores.append((f"{h}-{a}", p))

    n = lambda x: round(_clamp(x / total, 0.0, 1.0), 4)
    reg_home_p, reg_tie_p, reg_away_p = n(reg_home), n(reg_tie), n(reg_away)

    ot_home = _overtime_home_share(lambda_home, lambda_away)
    moneyline_home = round(reg_home_p + reg_tie_p * ot_home, 4)
    moneyline_away = round(reg_away_p + reg_tie_p * (1 - ot_home), 4)

    top = sorted(scores, key=lambda item: item[1], reverse=True)[:7]
    top = [{"score": s, "probability": round(p / total, 4)} for s, p in top]

    result = {
        "moneyline_home": moneyline_home,
        "moneyline_away": moneyline_away,
        "regulation_home": reg_home_p,
        "regulation_tie": reg_tie_p,
        "regulation_away": reg_away_p,
        "puckline_home_minus_1_5": n(margin_ge2),
        "puckline_away_plus_1_5": round(1.0 - n(margin_ge2), 4),
        "puckline_away_minus_1_5": n(margin_le_minus2),
        "puckline_home_plus_1_5": round(1.0 - n(margin_le_minus2), 4),
        "home_total_over_2_5": round(_clamp(1.0 - sum(poisson_pmf(lambda_home, g) for g in range(3)), 0.0, 1.0), 4),
        "away_total_over_2_5": round(_clamp(1.0 - sum(poisson_pmf(lambda_away, g) for g in range(3)), 0.0, 1.0), 4),
        "overtime_home_share": round(ot_home, 4),
        "most_likely_scores": top,
        "lambda_home": round(lambda_home, 3),
        "lambda_away": round(lambda_away, 3),
        "expected_total": round(lambda_home + lambda_away, 3),
        "totals": {},
    }
    for line in total_lines:
        over = n(totals[line])
        result["totals"][str(line)] = {"over": over, "under": round(1.0 - over, 4)}
    return result
