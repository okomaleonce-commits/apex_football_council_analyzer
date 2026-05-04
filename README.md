# APEX Football Council Analyzer

Logiciel d'analyse de match de football avec auto data fetching, modélisation Poisson, scoring de qualité des données, détection de value bet, et méthodologie "LLM Council" adaptée à l'analyse sportive.

## Ce que fait le logiciel

- Entrée par listes déroulantes : date, pays, ligue, équipe domicile, équipe extérieure.
- Récupération automatique des données via providers configurables :
  - API-FOOTBALL / API-Sports : pays, ligues, équipes, fixtures, classements, lineups, blessures, statistiques.
  - football-data.org : compétitions, matches, standings, équipes.
  - The Odds API : cotes pré-match disponibles selon ligue/sport key.
- Normalisation des données dans un `DataPack` unique.
- Score de qualité des données avant toute recommandation.
- Modèle statistique : Poisson, 1X2, double chance, BTTS, over/under, score exact.
- Lecture des cotes : probabilité implicite, fair odds, edge, ROI théorique.
- Conseil multi-agents inspiré de LLM Council :
  - Contrarian : cherche les pièges.
  - First Principles : teste les hypothèses.
  - Expansionist : cherche les opportunités secondaires.
  - Outsider : vérifie la clarté et les angles morts.
  - Executor : produit l'action concrète.
- Verdict final : BET / NO BET / WAIT DATA / WAIT LINEUPS.

## Limite honnête

Aucun logiciel ne peut légalement accéder à “toutes les sources sans restriction”. Les sources fiables ont des clés API, quotas, paywalls, anti-bot, et conditions d'utilisation. Ce projet est donc conçu comme une architecture extensible : ajoute un nouveau provider dans `app/providers/`, il sera intégré au pipeline sans casser le reste.

## Installation locale

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Ouvre ensuite : http://localhost:8000

## Variables d'environnement

Copie `.env.example` vers `.env`, puis ajoute tes clés.

```env
API_FOOTBALL_KEY=xxx
FOOTBALL_DATA_KEY=xxx
ODDS_API_KEY=xxx
OPENAI_API_KEY=xxx
OPENAI_MODEL=gpt-5.1
```

Sans clé API, l'interface reste disponible, mais les analyses seront limitées et le moteur refusera les recommandations fortes.

## Déploiement Render

Le fichier `render.yaml` est inclus.

```bash
git init
git add .
git commit -m "Initial APEX football analyzer"
git remote add origin <ton-repo-github>
git push -u origin main
```

Ensuite sur Render : New Web Service → connecte le repo → ajoute les variables d'environnement.

## Structure

```text
app/
  main.py                  API FastAPI + interface web
  settings.py              Configuration
  models.py                Schémas Pydantic
  providers/               Clients API externes
  core/
    data_fetcher.py        Agrégation multi-sources
    analyzer.py            Pipeline d'analyse complet
    poisson.py             Modèle de probabilités
    council.py             Conseil multi-agents
    metrics.py             Probabilités, fair odds, edge
    cache.py               Cache SQLite léger
  static/                  Interface HTML/CSS/JS
```

## Workflow analytique

1. Sélection du match.
2. Fetch multi-sources.
3. Normalisation.
4. Contrôle qualité : données, fraîcheur, exactitude match, cotes, lineups, blessures.
5. Modélisation Poisson.
6. Pricing des marchés.
7. Comparaison cotes marché vs fair odds.
8. Conseil multi-agents.
9. Verdict final.

## Règles de prudence intégrées

- Si confiance données < 0.60 : `NO BET`.
- Si kickoff proche et lineups manquantes : `WAIT_LINEUPS`.
- Si aucune cote fiable : pas de value bet validée.
- Si edge < seuil minimal : pas de recommandation principale.
- Si marché volatil ou données contradictoires : réduction de confiance.

## Ajouter une source

Crée un fichier dans `app/providers/mon_provider.py` avec une classe qui expose les méthodes utiles, puis appelle-la dans `DataFetcher`.

Exemple :

```python
class MyProvider:
    async def get_match_context(self, request):
        return {"source": "my_provider", "payload": {...}}
```

## Avertissement

Ce logiciel aide à structurer l'analyse. Il ne garantit aucun gain. Si tu l'utilises pour le betting, applique une gestion de bankroll stricte et accepte que le meilleur signal reste probabiliste.
