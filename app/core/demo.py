"""Matchs de démonstration pour le module Pronostic du jour.

Les statistiques sont pré-remplies, mais l'analyse (lambdas, probabilités, value,
verdict, conseil) est produite par le VRAI moteur FootballAnalyzer. C'est donc une
démo honnête : données d'entrée fictives, calculs réels. En production, ces packs
sont remplacés par les vraies données via DataFetcher.
"""
from __future__ import annotations

from datetime import date

from app.models import (
    DataPack,
    MatchAnalysisRequest,
    OddsQuote,
    SourceStatus,
    TeamSnapshot,
)

_SOURCES = [
    SourceStatus(name="api-football", ok=True, confidence=0.9),
    SourceStatus(name="the-odds-api", ok=True, confidence=0.8),
]


def _pack(home, away, hgf, hga, agf, aga, h_inj, a_inj, odds, league="Ligue 1") -> DataPack:
    req = MatchAnalysisRequest(match_date=date.today(), country="France", league=league, home=home, away=away)
    return DataPack(
        request=req, fixture_id=abs(hash(home + away)) % 999999, exact_match_found=True,
        source_status=_SOURCES,
        home=TeamSnapshot(name=home, played=10, goals_for=hgf, goals_against=hga, injuries_count=h_inj),
        away=TeamSnapshot(name=away, played=10, goals_for=agf, goals_against=aga, injuries_count=a_inj),
        odds=[OddsQuote(market=m, selection=s, bookmaker=b, price=p) for m, s, b, p in odds],
    )


def demo_packs(league: str = "Ligue 1") -> list[DataPack]:
    """Cinq matchs variés : certains avec value (BET), d'autres sans (NO_BET)."""
    return [
        # Fort domicile + cote Over généreuse -> value probable
        _pack("Olympique Lyonnais", "FC Nantes", 1.9, 1.0, 1.0, 1.6, 1, 2, [
            ("1X2", "HOME", "Betclic", 1.80), ("1X2", "DRAW", "Winamax", 3.70), ("1X2", "AWAY", "Unibet", 4.60),
            ("OVER_UNDER_2_5", "OVER_2_5", "Pinnacle", 2.15), ("OVER_UNDER_2_5", "UNDER_2_5", "Betclic", 1.72),
            ("BTTS", "YES", "Unibet", 1.95), ("BTTS", "NO", "Winamax", 1.85),
        ]),
        # Gros favori, cotes trop courtes -> pas de value
        _pack("Paris Saint-Germain", "Le Havre", 2.6, 0.7, 0.8, 1.9, 0, 1, [
            ("1X2", "HOME", "Betclic", 1.20), ("1X2", "DRAW", "Winamax", 7.00), ("1X2", "AWAY", "Unibet", 13.0),
            ("OVER_UNDER_2_5", "OVER_2_5", "Pinnacle", 1.55), ("OVER_UNDER_2_5", "UNDER_2_5", "Betclic", 2.45),
            ("BTTS", "YES", "Unibet", 2.10), ("BTTS", "NO", "Winamax", 1.70),
        ]),
        # Match équilibré, cote nul généreuse
        _pack("Olympique de Marseille", "LOSC Lille", 1.5, 1.2, 1.4, 1.3, 2, 1, [
            ("1X2", "HOME", "Betclic", 2.20), ("1X2", "DRAW", "Winamax", 3.95), ("1X2", "AWAY", "Unibet", 3.10),
            ("OVER_UNDER_2_5", "OVER_2_5", "Pinnacle", 1.90), ("OVER_UNDER_2_5", "UNDER_2_5", "Betclic", 1.95),
            ("BTTS", "YES", "Unibet", 1.75), ("BTTS", "NO", "Winamax", 2.05),
        ]),
        # Défenses solides, Under potentiellement value
        _pack("AS Monaco", "RC Lens", 1.3, 1.0, 1.1, 1.0, 1, 2, [
            ("1X2", "HOME", "Betclic", 2.05), ("1X2", "DRAW", "Winamax", 3.30), ("1X2", "AWAY", "Unibet", 3.70),
            ("OVER_UNDER_2_5", "OVER_2_5", "Pinnacle", 2.25), ("OVER_UNDER_2_5", "UNDER_2_5", "Betclic", 1.68),
            ("BTTS", "YES", "Unibet", 2.00), ("BTTS", "NO", "Winamax", 1.80),
        ]),
        # Deux équipes offensives, BTTS
        _pack("Stade Rennais", "RC Strasbourg", 1.7, 1.4, 1.6, 1.3, 1, 1, [
            ("1X2", "HOME", "Betclic", 2.10), ("1X2", "DRAW", "Winamax", 3.60), ("1X2", "AWAY", "Unibet", 3.30),
            ("OVER_UNDER_2_5", "OVER_2_5", "Pinnacle", 1.80), ("OVER_UNDER_2_5", "UNDER_2_5", "Betclic", 2.05),
            ("BTTS", "YES", "Unibet", 1.72), ("BTTS", "NO", "Winamax", 2.10),
        ]),
    ]
