"""Moteur de trafic APEX — transforme une analyse de match en contenu social.

Prend un `AnalysisReport` (la sortie de FootballAnalyzer) et produit :
  - un carrousel TikTok/Instagram (liste de slides, texte)
  - un thread X/Threads (liste de posts)
  - un fichier HTML de slides prêtes à screenshoter (format 9:16)

Cadrage EDUCATIF : le contenu montre la méthode et renvoie vers le produit.
Jamais de "pari garanti". Disclaimers +18 / risque de perte inclus partout.

Usage :
    python product/traffic-engine/content_generator.py --demo
    python product/traffic-engine/content_generator.py --demo --html slides.html
    python product/traffic-engine/content_generator.py --report rapport.json

Le lien produit affiché est configurable via PRODUCT_URL ci-dessous.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

# Rendre le package `app` importable quand on lance ce fichier directement.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.models import AnalysisReport  # noqa: E402

# --- À personnaliser ---------------------------------------------------------
PRODUCT_URL = "https://apex-football-council-analyzer.onrender.com"  # plateforme live
BRAND = "APEX"
DISCLAIMER = "Analyse, pas un conseil. Jouer comporte des risques. +18."
# -----------------------------------------------------------------------------

_SELECTION_FR = {
    "HOME": "Victoire domicile",
    "DRAW": "Match nul",
    "AWAY": "Victoire extérieur",
    "1X": "Domicile ou nul",
    "12": "Pas de nul",
    "X2": "Nul ou extérieur",
    "YES": "Les deux marquent",
    "NO": "Une équipe blanchie",
    "OVER_2_5": "Plus de 2.5 buts",
    "UNDER_2_5": "Moins de 2.5 buts",
}

_VERDICT_FR = {
    "BET": "SIGNAL VALIDÉ",
    "NO_BET": "ON PASSE",
    "WAIT_DATA": "DONNÉES INSUFFISANTES",
    "WAIT_LINEUPS": "ON ATTEND LES COMPOS",
    "MONITOR_LIVE": "À SURVEILLER",
}


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{round(x * 100)}%"


def _sel_label(signal) -> str:
    return _SELECTION_FR.get(signal.selection, signal.selection)


def _matchup(report: AnalysisReport) -> str:
    return f"{report.request.home} – {report.request.away}"


def build_tiktok_carousel(report: AnalysisReport) -> list[str]:
    """Retourne une liste de slides (texte) pour un carrousel vertical."""
    r = report
    match = _matchup(r)
    q = r.data_quality
    p = r.probabilities
    slides: list[str] = []

    # Slide 1 — Hook
    if r.final_verdict == "BET" and r.primary_bet:
        hook = f"J'ai passé {match} dans un modèle de Poisson.\nLe marché s'est trompé."
    elif r.final_verdict in ("NO_BET", "WAIT_DATA"):
        hook = f"Tout le monde veut parier sur {match}.\nVoici pourquoi moi je ne parie PAS."
    else:
        hook = f"{match} au microscope.\nLa méthode, étape par étape."
    slides.append(f"[HOOK]\n{hook}\n\n→ swipe")

    # Slide 2 — Qualité des données (la discipline)
    slides.append(
        "[ÉTAPE 1 — LES DONNÉES]\n"
        f"Score de qualité : {_pct(q.score)} ({q.verdict}).\n"
        "Sous 60%, on n'a même pas le droit d'avoir un avis.\n"
        "La plupart des pertes viennent de là."
    )

    # Slide 3 — Le modèle
    slides.append(
        "[ÉTAPE 2 — LE MODÈLE]\n"
        f"Buts attendus : {r.request.home} {p.lambda_home} / {r.request.away} {p.lambda_away}.\n"
        f"Victoire dom {_pct(p.home_win)} · nul {_pct(p.draw)} · ext {_pct(p.away_win)}.\n"
        f"Over 2.5 : {_pct(p.over_2_5)} · BTTS : {_pct(p.btts_yes)}."
    )

    # Slide 4 — La value (le coeur)
    if r.primary_bet and r.primary_bet.edge is not None:
        s = r.primary_bet
        slides.append(
            "[ÉTAPE 3 — LA VALUE]\n"
            f"{_sel_label(s)} : le modèle dit {_pct(s.probability)}.\n"
            f"Cote marché {s.best_odds} = {_pct(1 / s.best_odds) if s.best_odds else '—'} implicite.\n"
            f"EDGE +{round(s.edge * 100, 1)} pts → le marché sous-paie."
        )
    else:
        slides.append(
            "[ÉTAPE 3 — LA VALUE]\n"
            "Aucun marché ne paie au-dessus de son juste prix.\n"
            "Probabilité élevée ≠ bon pari.\n"
            "Pas de value = pas de pari. C'est la règle."
        )

    # Slide 5 — Verdict
    verdict_fr = _VERDICT_FR.get(r.final_verdict, r.final_verdict)
    if r.primary_bet:
        verdict_line = f"{_sel_label(r.primary_bet)} @ {r.primary_bet.best_odds}"
    else:
        verdict_line = "Aucun. Le meilleur pari, c'est souvent zéro pari."
    slides.append(f"[VERDICT : {verdict_fr}]\n{verdict_line}\n\n{DISCLAIMER}")

    # Slide 6 — CTA
    slides.append(
        "[FAIS-LE TOI-MÊME]\n"
        f"Scanner de value, pronostics modélisés, coupons, montante.\n"
        f"La plateforme {BRAND} → lien en bio.\n{PRODUCT_URL}"
    )
    return slides


def build_x_thread(report: AnalysisReport) -> list[str]:
    """Retourne une liste de posts pour un thread X / Threads."""
    r = report
    match = _matchup(r)
    p = r.probabilities
    posts: list[str] = []

    posts.append(
        f"{match}.\n\n"
        "Je l'ai passé dans un modèle quantitatif (Poisson + détection de value). "
        "Le process, étape par étape 🧵"
    )
    posts.append(
        f"1/ Données d'abord.\nScore de qualité : {_pct(r.data_quality.score)} "
        f"({r.data_quality.verdict}).\nSous 60% = aucun avis, aucun pari. "
        "C'est là que 90% des parieurs se plantent."
    )
    posts.append(
        f"2/ Le modèle.\nButs attendus {r.request.home} {p.lambda_home} / "
        f"{r.request.away} {p.lambda_away}.\n"
        f"1 {_pct(p.home_win)} · X {_pct(p.draw)} · 2 {_pct(p.away_win)} · "
        f"O2.5 {_pct(p.over_2_5)} · BTTS {_pct(p.btts_yes)}."
    )
    if r.primary_bet and r.primary_bet.edge is not None:
        s = r.primary_bet
        posts.append(
            f"3/ La value.\n{_sel_label(s)} : modèle {_pct(s.probability)} vs "
            f"marché {_pct(1 / s.best_odds) if s.best_odds else '—'} (cote {s.best_odds}).\n"
            f"EDGE +{round(s.edge * 100, 1)} pts. Le marché sous-paie → signal."
        )
    else:
        posts.append(
            "3/ La value.\nAucun marché au-dessus de son juste prix aujourd'hui.\n"
            "Probabilité haute ≠ value. Donc : pas de pari. Et c'est très bien."
        )
    posts.append(
        f"4/ Verdict : {_VERDICT_FR.get(r.final_verdict, r.final_verdict)}.\n"
        f"{DISCLAIMER}\n\n"
        f"Analyse tes propres matchs sur la plateforme {BRAND} : {PRODUCT_URL}"
    )
    return posts


_SLIDE_HTML = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Slides {match}</title>
<style>
  body{{margin:0;background:#050506;font-family:"Courier New",monospace;
    display:flex;flex-wrap:wrap;gap:24px;padding:24px;justify-content:center}}
  .slide{{width:360px;height:640px;background:#111113;border:1px solid #26262c;
    border-radius:18px;padding:34px 30px;color:#f3f3f5;display:flex;flex-direction:column;
    position:relative;overflow:hidden}}
  .tag{{color:#ff6a2b;font-weight:700;letter-spacing:.12em;font-size:13px;margin-bottom:18px}}
  .body{{font-size:23px;line-height:1.5;white-space:pre-wrap;flex:1}}
  .wm{{position:absolute;bottom:16px;right:22px;color:#55555c;font-size:12px}}
  .n{{position:absolute;top:18px;right:22px;color:#55555c;font-size:13px}}
  @media print{{body{{background:#050506}}}}
</style></head><body>
{cards}
</body></html>"""


def build_slide_html(report: AnalysisReport) -> str:
    """Génère un HTML de slides 9:16 prêtes à screenshoter pour un carrousel."""
    slides = build_tiktok_carousel(report)
    cards = []
    for i, raw in enumerate(slides, 1):
        tag, _, body = raw.partition("\n")
        tag = tag.strip("[]")
        cards.append(
            f'<div class="slide"><div class="n">{i}/{len(slides)}</div>'
            f'<div class="tag">{html.escape(tag)}</div>'
            f'<div class="body">{html.escape(body.strip())}</div>'
            f'<div class="wm">{BRAND}</div></div>'
        )
    return _SLIDE_HTML.format(match=html.escape(_matchup(report)), cards="\n".join(cards))


def _demo_report() -> AnalysisReport:
    """Construit un rapport de démo via le vrai moteur (sans clés API)."""
    from datetime import date

    from app.core.analyzer import FootballAnalyzer
    from app.models import (
        DataPack,
        MatchAnalysisRequest,
        OddsQuote,
        SourceStatus,
        TeamSnapshot,
    )
    from app.settings import Settings

    req = MatchAnalysisRequest(
        match_date=date.today(), country="France", league="Ligue 1",
        home="Olympique Lyonnais", away="FC Nantes",
    )
    pack = DataPack(
        request=req, fixture_id=123456, exact_match_found=True,
        source_status=[
            SourceStatus(name="api-football", ok=True, confidence=0.9),
            SourceStatus(name="the-odds-api", ok=True, confidence=0.8),
        ],
        home=TeamSnapshot(name=req.home, played=10, goals_for=1.9, goals_against=1.0, injuries_count=1),
        away=TeamSnapshot(name=req.away, played=10, goals_for=1.0, goals_against=1.6, injuries_count=2),
        odds=[
            OddsQuote(market="1X2", selection="HOME", bookmaker="demo", price=1.75),
            OddsQuote(market="OVER_UNDER_2_5", selection="OVER_2_5", bookmaker="demo", price=2.15),
            OddsQuote(market="BTTS", selection="YES", bookmaker="demo", price=1.95),
        ],
    )
    return FootballAnalyzer(Settings()).analyze(pack)


def _print_text(report: AnalysisReport) -> None:
    print("=" * 60)
    print("CARROUSEL TIKTOK / INSTAGRAM")
    print("=" * 60)
    for i, s in enumerate(build_tiktok_carousel(report), 1):
        print(f"\n--- Slide {i} ---\n{s}")
    print("\n" + "=" * 60)
    print("THREAD X / THREADS")
    print("=" * 60)
    for i, p in enumerate(build_x_thread(report), 1):
        print(f"\n[{i}] {p}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Génère du contenu social depuis une analyse APEX.")
    ap.add_argument("--demo", action="store_true", help="Utilise un match de démonstration.")
    ap.add_argument("--report", help="Chemin d'un AnalysisReport au format JSON.")
    ap.add_argument("--html", help="Écrit les slides dans ce fichier HTML (9:16).")
    args = ap.parse_args(argv)

    if args.report:
        report = AnalysisReport.model_validate_json(Path(args.report).read_text(encoding="utf-8"))
    elif args.demo:
        report = _demo_report()
    else:
        ap.error("Précise --demo ou --report <fichier.json>.")
        return 2

    _print_text(report)
    if args.html:
        out = Path(args.html)
        out.write_text(build_slide_html(report), encoding="utf-8")
        print(f"\n✅ Slides HTML écrites : {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
