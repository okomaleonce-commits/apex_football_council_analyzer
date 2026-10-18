from math import exp, factorial


def poisson_pmf(lmbda: float, goals: int) -> float:
    return (lmbda ** goals) * exp(-lmbda) / factorial(goals)


def dixon_coles_tau(h: int, a: int, lambda_home: float, lambda_away: float, rho: float) -> float:
    """Correction Dixon-Coles sur les 4 scores faibles.

    Le Poisson indépendant sous-estime les scores de parité (0-0, 1-1) et
    surestime (1-0, 0-1). tau réajuste ces 4 cellules ; rho<0 regonfle les nuls.
    Les autres scores ne sont pas modifiés (tau = 1).
    """
    if h == 0 and a == 0:
        return 1.0 - lambda_home * lambda_away * rho
    if h == 0 and a == 1:
        return 1.0 + lambda_home * rho
    if h == 1 and a == 0:
        return 1.0 + lambda_away * rho
    if h == 1 and a == 1:
        return 1.0 - rho
    return 1.0


def compute_probabilities(lambda_home: float, lambda_away: float, max_goals: int = 10, rho: float = -0.13):
    """Loi jointe des buts avec correction Dixon-Coles (calcul analytique exact).

    Pas de Monte-Carlo : la loi jointe est analytique, une troncature à
    max_goals suffit et donne un résultat exact (et reproductible).
    """
    matrix = []
    for h in range(max_goals + 1):
        row = []
        for a in range(max_goals + 1):
            p = poisson_pmf(lambda_home, h) * poisson_pmf(lambda_away, a)
            p *= max(0.0, dixon_coles_tau(h, a, lambda_home, lambda_away, rho))
            row.append(p)
        matrix.append(row)
    total = sum(sum(r) for r in matrix) or 1.0

    hw = dr = aw = ov25 = btts = h05 = a05 = 0.0
    scores = []
    for h, row in enumerate(matrix):
        for a, p in enumerate(row):
            if h > a: hw += p
            elif h == a: dr += p
            else: aw += p
            if h + a >= 3: ov25 += p
            if h > 0 and a > 0: btts += p
            if h > 0: h05 += p
            if a > 0: a05 += p
            scores.append({'score': f'{h}-{a}', 'probability': p / total})
    n = lambda x: round(max(0.0, min(1.0, x / total)), 4)
    top = sorted(scores, key=lambda x: x['probability'], reverse=True)[:7]
    top = [{'score': s['score'], 'probability': round(s['probability'], 4)} for s in top]
    return {
        'home_win': n(hw), 'draw': n(dr), 'away_win': n(aw),
        'home_or_draw': n(hw + dr), 'home_or_away': n(hw + aw), 'draw_or_away': n(dr + aw),
        'btts_yes': n(btts), 'btts_no': n(total - btts),
        'over_2_5': n(ov25), 'under_2_5': n(total - ov25),
        'home_over_0_5': n(h05), 'away_over_0_5': n(a05),
        'most_likely_scores': top,
        'lambda_home': round(lambda_home, 3), 'lambda_away': round(lambda_away, 3),
    }
