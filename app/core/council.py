from __future__ import annotations

import asyncio
import json

import anthropic

from app.models import AdvisorOutput, CouncilVerdict, DataQuality, MarketSignal, ProbabilitySet

_ADVISOR_SCHEMA = {
    "type": "object",
    "properties": {
        "position": {"type": "string"},
        "risks": {"type": "array", "items": {"type": "string"}},
        "recommendation": {"type": "string"},
    },
    "required": ["position", "risks", "recommendation"],
    "additionalProperties": False,
}

_VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "where_agrees": {"type": "array", "items": {"type": "string"}},
        "where_clashes": {"type": "array", "items": {"type": "string"}},
        "blind_spots": {"type": "array", "items": {"type": "string"}},
        "recommendation": {"type": "string"},
        "first_action": {"type": "string"},
    },
    "required": ["where_agrees", "where_clashes", "blind_spots", "recommendation", "first_action"],
    "additionalProperties": False,
}

# Les 5 agents du protocole APEX
_AGENTS = [
    {
        "name": "Contrarian",
        "position": "Cherche les pièges de marché",
        "system": (
            "Tu es l'agent Contrarian du conseil APEX Football. "
            "Tu remets en question l'analyse dominante et détectes les pièges.\n\n"
            "Analyse systématiquement :\n"
            "- Pourquoi la cote dominante est peut-être trompeuse (biais favori, domicile surestimé)\n"
            "- Si le marché a déjà intégré l'information (value absente)\n"
            "- Les contextes invalidant les statistiques (match sans enjeu, rotation, suspension clé)\n"
            "- Si les lambdas Poisson sont fiables sur un échantillon trop court\n"
            "- Les signaux contradictoires entre sources"
        ),
    },
    {
        "name": "First Principles",
        "position": "Valide la logique statistique",
        "system": (
            "Tu es l'agent First Principles du conseil APEX Football. "
            "Tu repars des fondamentaux statistiques et valides chaque hypothèse.\n\n"
            "Analyse :\n"
            "- La cohérence des lambdas Poisson avec les stats réelles fournies\n"
            "- La taille de l'échantillon (matchs joués) : suffisante ou non ?\n"
            "- Si la forme récente contredit les stats saisonnières\n"
            "- La distinction entre probabilité haute et value bet réelle\n"
            "- La validité du score qualité données : justifié ou non ?"
        ),
    },
    {
        "name": "Expansionist",
        "position": "Cherche les opportunités secondaires",
        "system": (
            "Tu es l'agent Expansionist du conseil APEX Football. "
            "Tu identifies les marchés alternatifs à fort edge.\n\n"
            "Analyse :\n"
            "- Les marchés au-delà du 1X2 : BTTS, Over/Under, Double Chance, Score Exact\n"
            "- Quel marché présente le meilleur rapport edge/probabilité dans les signaux fournis\n"
            "- Si les probabilités Poisson révèlent des opportunités sous-estimées par les bookmakers\n"
            "- Des combinaisons logiques si plusieurs signaux convergent\n"
            "- Les marchés moins populaires avec plus d'erreurs de pricing"
        ),
    },
    {
        "name": "Outsider",
        "position": "Vérifie les angles morts",
        "system": (
            "Tu es l'agent Outsider du conseil APEX Football. "
            "Tu vérifies ce que les autres agents ont potentiellement raté.\n\n"
            "Analyse :\n"
            "- La fraîcheur et cohérence des données entre les sources disponibles\n"
            "- Les facteurs externes non capturés (motivation, fatigue de coupe, pression psychologique)\n"
            "- Si les lineups ne sont pas confirmées et l'impact sur la fiabilité\n"
            "- Les incohérences entre sources (cotes vs stats, fixture id absent, etc.)\n"
            "- Le timing de l'analyse : trop tôt (données manquantes) ou trop tard (cotes bougées) ?"
        ),
    },
    {
        "name": "Executor",
        "position": "Transforme l'analyse en action concrète",
        "system": (
            "Tu es l'agent Executor du conseil APEX Football. "
            "Tu synthétises tous les signaux en une décision d'action claire.\n\n"
            "Produis :\n"
            "- UNE recommandation principale : BET / NO BET / WAIT_LINEUPS / WAIT_DATA\n"
            "- Si BET : marché exact, sélection, cote minimum acceptable, % bankroll recommandé\n"
            "- Si NO BET : une phrase expliquant pourquoi\n"
            "- Le déclencheur clair : 'uniquement si [condition]'\n"
            "- Niveau de confiance global : faible / modéré / élevé"
        ),
    },
]

_SYNTHESIZER_SYSTEM = (
    "Tu es le coordinateur du conseil APEX Football. "
    "Tu reçois les analyses de 5 agents spécialisés et produis le verdict final.\n\n"
    "Ton rôle :\n"
    "- Identifier les points de convergence entre agents\n"
    "- Identifier les désaccords significatifs\n"
    "- Lister les angles morts collectifs restants\n"
    "- Formuler une recommandation finale synthétisant tous les avis\n"
    "- Définir la première action concrète à prendre"
)


def _build_context(
    quality: DataQuality,
    probabilities: ProbabilitySet,
    signals: list[MarketSignal],
    primary: MarketSignal | None,
) -> str:
    top_signals = [s for s in signals if s.status in ("VALIDATED", "LEAN")][:5]
    signals_text = "\n".join(
        f"  - {s.market} {s.selection}: prob={s.probability:.1%}, fair={s.fair_odds}, "
        f"best={s.best_odds or 'N/A'}, edge={s.edge}, status={s.status}"
        for s in top_signals
    ) or "  Aucun signal exploitable."

    primary_text = (
        f"{primary.market} {primary.selection} (edge={primary.edge}, conf={primary.confidence})"
        if primary
        else "AUCUN — pas de signal validé"
    )

    return (
        f"=== CONTEXTE MATCH APEX ===\n"
        f"Qualité données: {quality.score:.2f} ({quality.verdict})\n"
        f"Alertes: {', '.join(quality.reasons)}\n\n"
        f"Probabilités Poisson:\n"
        f"  1X2: dom={probabilities.home_win:.1%} / nul={probabilities.draw:.1%} / ext={probabilities.away_win:.1%}\n"
        f"  BTTS: oui={probabilities.btts_yes:.1%} / non={probabilities.btts_no:.1%}\n"
        f"  Over2.5: {probabilities.over_2_5:.1%} / Under2.5: {probabilities.under_2_5:.1%}\n"
        f"  λ dom={probabilities.lambda_home} / λ ext={probabilities.lambda_away}\n"
        f"  Scores probables: {', '.join(s['score'] for s in probabilities.most_likely_scores[:4])}\n\n"
        f"Signaux marché (top 5):\n{signals_text}\n\n"
        f"Signal principal: {primary_text}\n"
    )


async def _call_agent(
    client: anthropic.AsyncAnthropic,
    model: str,
    agent: dict,
    context: str,
) -> AdvisorOutput:
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=512,
            system=[
                {
                    "type": "text",
                    "text": agent["system"],
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            output_config={"format": {"type": "json_schema", "schema": _ADVISOR_SCHEMA}},
            messages=[{"role": "user", "content": context}],
        )
        text = next((b.text for b in response.content if b.type == "text"), "{}")
        data: dict = json.loads(text)
        return AdvisorOutput(
            advisor=agent["name"],
            position=data.get("position", agent["position"]),
            risks=data.get("risks", []),
            recommendation=data.get("recommendation", ""),
        )
    except Exception as exc:
        return AdvisorOutput(
            advisor=agent["name"],
            position=agent["position"],
            risks=[f"Agent indisponible: {exc}"],
            recommendation="Erreur LLM — résultat non disponible, utiliser le jugement rules-based.",
        )


async def run_llm_council(
    api_key: str,
    model: str,
    quality: DataQuality,
    probabilities: ProbabilitySet,
    signals: list[MarketSignal],
    primary: MarketSignal | None,
) -> CouncilVerdict:
    """Lance les 5 agents APEX en parallèle puis synthétise leur verdict."""
    client = anthropic.AsyncAnthropic(api_key=api_key)
    context = _build_context(quality, probabilities, signals, primary)

    # Les 5 agents tournent en parallèle
    advisor_outputs: list[AdvisorOutput] = list(
        await asyncio.gather(*[
            _call_agent(client, model, agent, context)
            for agent in _AGENTS
        ])
    )

    agents_summary = "\n\n".join(
        f"=== {a.advisor} ===\n"
        f"Position: {a.position}\n"
        f"Recommandation: {a.recommendation}\n"
        f"Risques: {', '.join(a.risks) if a.risks else 'aucun'}"
        for a in advisor_outputs
    )

    # Coordinateur : synthèse des 5 avis
    verdict_data: dict = {}
    try:
        synth = await client.messages.create(
            model=model,
            max_tokens=768,
            system=[
                {
                    "type": "text",
                    "text": _SYNTHESIZER_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            output_config={"format": {"type": "json_schema", "schema": _VERDICT_SCHEMA}},
            messages=[
                {
                    "role": "user",
                    "content": f"{context}\n=== AVIS DES 5 AGENTS ===\n{agents_summary}",
                }
            ],
        )
        text = next((b.text for b in synth.content if b.type == "text"), "{}")
        verdict_data = json.loads(text)
    except Exception:
        pass

    executor = next((a for a in advisor_outputs if a.advisor == "Executor"), None)
    return CouncilVerdict(
        where_agrees=verdict_data.get("where_agrees", ["Convergence indisponible."]),
        where_clashes=verdict_data.get("where_clashes", []),
        blind_spots=verdict_data.get("blind_spots", quality.reasons),
        recommendation=verdict_data.get(
            "recommendation",
            executor.recommendation if executor else "Aucune recommandation disponible.",
        ),
        first_action=verdict_data.get(
            "first_action",
            "Vérifier les lineups et les cotes proches du coup d'envoi.",
        ),
        advisors=advisor_outputs,
    )
