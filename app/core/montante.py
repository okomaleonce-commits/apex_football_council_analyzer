"""Module Bankroll / Montante.

Une montante est un plan de mises progressives : on part d'un capital et on vise
un objectif en enchaînant des paris gagnants, chaque palier réinvestissant le gain
du précédent.

Ce module la calcule honnêtement :
  - le plan palier par palier (capital avant, mise, capital après un gain) ;
  - la MISE de chaque palier pour que le capital soit multiplié par le facteur g ;
  - surtout, la PROBABILITÉ d'aller au bout = p^N (p = proba de gagner un palier).

Message clé, non négociable : une montante NE CRÉE PAS de value. Chaque pari garde
la marge du bookmaker contre toi. Elle ne fait que concentrer le risque : une seule
défaite casse la série. Plus il y a de paliers, plus la proba de tout réussir chute.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class MontanteRequest(BaseModel):
    capital_depart: float = 100.0
    objectif: float = 200.0
    cote: float = 1.50            # cote moyenne visée par palier
    nb_paliers: int = 5
    proba_palier: float | None = None  # proba estimée de gagner un palier ; défaut = 1/cote


class MontanteStep(BaseModel):
    palier: int
    capital_avant: float
    mise: float
    capital_apres_gain: float
    pct_capital_mise: float


class MontanteResult(BaseModel):
    steps: list[MontanteStep]
    nb_paliers: int
    cote: float
    proba_palier: float
    proba_completion: float       # p^N
    objectif: float
    capital_depart: float
    faisable: bool
    warnings: list[str]


def build_montante(req: MontanteRequest) -> MontanteResult:
    warnings: list[str] = []
    c0 = max(0.01, req.capital_depart)
    objectif = max(c0, req.objectif)
    cote = max(1.01, req.cote)
    n = max(1, min(req.nb_paliers, 50))
    p = req.proba_palier if req.proba_palier is not None else round(1.0 / cote, 4)
    p = min(max(p, 0.0), 1.0)

    # Facteur de croissance par palier pour atteindre l'objectif en n paliers.
    g = (objectif / c0) ** (1.0 / n)

    faisable = g <= cote
    if not faisable:
        warnings.append(
            f"Objectif inatteignable en {n} paliers à la cote {cote} : il faudrait "
            f"miser plus que le capital. Augmente le nombre de paliers ou la cote."
        )

    steps: list[MontanteStep] = []
    capital = c0
    for i in range(1, n + 1):
        cible = capital * g
        # mise telle qu'un gain à `cote` amène le capital à `cible`
        mise = (cible - capital) / (cote - 1.0)
        mise = max(0.0, min(mise, capital))  # jamais plus que le capital en jeu
        apres = capital + mise * (cote - 1.0)
        steps.append(MontanteStep(
            palier=i, capital_avant=round(capital, 2), mise=round(mise, 2),
            capital_apres_gain=round(apres, 2),
            pct_capital_mise=round(100.0 * mise / capital, 1) if capital else 0.0,
        ))
        capital = apres

    proba_completion = round(p ** n, 4)

    warnings.append("Une seule défaite fait perdre la mise du palier et casse la série.")
    warnings.append("La montante ne crée pas de value : la marge du bookmaker reste contre toi à chaque pari.")
    if proba_completion < 0.20:
        warnings.append(f"Probabilité d'aller au bout faible : {round(proba_completion*100,1)}%. À tes risques.")
    if n >= 8:
        warnings.append("8 paliers ou plus : la proba de tout réussir est très faible.")

    return MontanteResult(
        steps=steps, nb_paliers=n, cote=round(cote, 3), proba_palier=p,
        proba_completion=proba_completion, objectif=round(objectif, 2),
        capital_depart=round(c0, 2), faisable=faisable, warnings=warnings,
    )
