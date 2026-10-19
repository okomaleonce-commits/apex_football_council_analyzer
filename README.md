# APEX Football Council Analyzer

Logiciel d'analyse de match de football avec auto data fetching, modélisation Poisson, scoring de qualité des données, détection de value bet, et méthodologie "LLM Council" adaptée à l'analyse sportive.

## Ce que fait le logiciel

- Entrée par listes déroulantes : date, pays, ligue, équipe domicile, équipe extérieure.
- Récupération automatique des données via providers configurables :
  - API-FOOTBALL / API-Sports : pays, ligues, équipes, fixtures, classements, lineups, blessures, statistiques.
  - football-data.org : compétitions, matches, standings, équipes.
  - The Odds API : cotes pré-match disponibles selon ligue/sport key.
- Normalisation des données dans un `DataPack` unique.
- **Kill-switches de données** (booléens) avant toute recommandation : match non confirmé ou statistiques d'équipes absentes ⇒ `WAIT_DATA`, jamais de pari sur des lambdas par défaut.
- Modèle statistique : Poisson **avec correction Dixon-Coles** (dépendance des petits scores) et estimation des buts par **forces relatives normalisées par la ligue** (pas une simple moyenne) ; marchés 1X2, double chance, BTTS, over/under, score exact.
- Lecture des cotes : **la marge du bookmaker est retirée (dévig Shin ou proportionnel)** avant tout calcul d'edge. L'edge compare le modèle aux *vraies* probabilités de marché, jamais à la cote brute.
- Conseil « multi-agents » : **ensemble de règles déterministes** (ce n'est pas une délibération multi-LLM ; le champ `council.engine = "rules"` et un `disclaimer` le rappellent dans chaque réponse).
- **Preuve d'edge d'abord** : tant que la calibration (Brier / log-loss / **CLV**) n'est pas validée sur un historique réglé, le moteur reste en `advisory_only` et ne produit jamais de `BET` « argent réel ».
- **Mise fixe (flat staking)** ; le critère de Kelly est volontairement désactivé tant que les probabilités ne sont pas prouvées calibrées.
- Verdict final : BET / NO BET / WAIT DATA / WAIT LINEUPS / MONITOR LIVE.

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

- Kill-switch : match non confirmé ou stats d'équipes absentes ⇒ `WAIT_DATA` (jamais de lambdas par défaut).
- Si confiance données < 0.60 : `NO BET` / `WAIT_DATA`.
- Si kickoff proche et lineups manquantes : `WAIT_LINEUPS`.
- Si le marché n'est pas complet (toutes les sélections cotées) : marge non retirable ⇒ pas de value mesurable.
- Si edge dévigé < seuil minimal : pas de recommandation principale.
- Tant que `calibration_proven` est faux : `advisory_only`, aucun `BET` argent réel.

## Preuve d'edge (endpoints)

- `GET /api/calibration` : Brier, log-loss et CLV sur l'historique des prédictions réglées.
- `POST /api/settle?prediction_id=<id>&won=<bool>&closing_odds=<float>` : renseigne le résultat réel et la cote de clôture d'une prédiction, pour alimenter la CLV.
- Chaque `/api/analyze` journalise ses signaux chiffrés (SQLite, `TRACKING_DB_PATH`). Passe `CALIBRATION_PROVEN=True` seulement une fois un edge réellement démontré.

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
