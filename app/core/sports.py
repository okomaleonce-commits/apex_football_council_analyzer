"""Registre des sports et garde « hors-domaine ».

Problème résolu
---------------
Le système n'avait aucune route pour un sport sans moteur calibré. Face à une
demande non prévue (ex. hockey avant l'ajout du moteur, ou basket, tennis...),
le risque était de faire tourner silencieusement le modèle football sur des
données qui n'ont rien à voir — et de produire des probabilités fausses avec une
fausse apparence de rigueur.

Cette garde impose une règle simple et explicite :
  - sport calibré  -> on exécute le moteur dédié ;
  - sport inconnu  -> verdict `NO_MODEL` honnête (best-effort only), jamais de
    pari, jamais de réutilisation d'un moteur d'un autre sport.

C'est la traduction en code de la discipline validée par l'audit post-match :
sans modèle calibré, on s'abstient.
"""

from __future__ import annotations

from dataclasses import dataclass

# Sports disposant d'un moteur statistique dédié et calibré.
SUPPORTED_SPORTS: dict[str, str] = {
    "football": "Dixon-Coles / Poisson calibré football (2.7 buts/match).",
    "hockey": "Poisson calibré NHL (~6.1 buts/match, moneyline OT/SO, puck line).",
}

# Sports reconnus mais SANS moteur calibré : best-effort qualitatif uniquement.
KNOWN_UNCALIBRATED: dict[str, str] = {
    "basketball": "Pas de moteur calibré (dynamique de score continue).",
    "tennis": "Pas de moteur calibré (format sets/jeux, pas de buts).",
    "handball": "Pas de moteur calibré.",
    "baseball": "Pas de moteur calibré.",
    "rugby": "Pas de moteur calibré.",
}


class OutOfDomainError(Exception):
    """Levée quand un sport n'a pas de moteur calibré disponible."""

    def __init__(self, sport: str, reason: str) -> None:
        self.sport = sport
        self.reason = reason
        super().__init__(reason)


@dataclass
class DomainCheck:
    sport: str
    supported: bool
    verdict: str          # "MODEL_READY" | "NO_MODEL"
    message: str


def normalize_sport(sport: str | None) -> str:
    return (sport or "football").strip().lower()


def check_domain(sport: str | None) -> DomainCheck:
    """Décide si l'on peut appliquer un moteur calibré à ce sport."""
    key = normalize_sport(sport)
    if key in SUPPORTED_SPORTS:
        return DomainCheck(key, True, "MODEL_READY", SUPPORTED_SPORTS[key])
    reason = KNOWN_UNCALIBRATED.get(
        key, f"Sport « {key} » non reconnu par le système."
    )
    message = (
        f"Aucun moteur calibré pour « {key} ». {reason} "
        "Analyse best-effort uniquement, aucun signal de pari validé. "
        "Le moteur football/hockey ne sera PAS appliqué (éviterait une "
        "contamination de modèle)."
    )
    return DomainCheck(key, False, "NO_MODEL", message)


def assert_supported(sport: str | None) -> str:
    """Retourne le sport normalisé s'il est calibré, sinon lève OutOfDomainError."""
    check = check_domain(sport)
    if not check.supported:
        raise OutOfDomainError(check.sport, check.message)
    return check.sport
