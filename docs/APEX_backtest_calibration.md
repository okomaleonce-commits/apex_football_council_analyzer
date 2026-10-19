# APEX — Backtest & recalibration du moteur

## Objectif
Faire descendre le **Brier** du modèle sous **0.25** (seuil « mieux qu'un pile ou face »)
par un backtest, pour pouvoir un jour lever le gate `advisory_only`.

## Méthode (sans fuite de données)
Backtest **walk-forward** : pour chaque match, les forces d'attaque/défense sont
calculées **uniquement sur les matchs antérieurs de la même saison** (stats roulantes,
minimum 5 matchs joués par équipe, et > 20 matchs de ligue pour estimer la moyenne).
Aucune information future n'entre dans la prédiction.

- **Échantillon** : 2 740 prédictions sur 8 ligues / saisons complètes
  (EPL, La Liga, Serie A, Bundesliga, Ligue 1 — 2024/25 ; Brésil Série A, MLS,
  Argentine Primera — 2025).
- **Modèle** : Dixon-Coles + forces relatives normalisées par la ligue (identique au moteur).
- **Split** : 70 % train / 30 % test.
- **Métrique** : Brier (binaire par marché ; 1X2 = moyenne des 3 one-vs-rest).

## Résultat

| Marché | Brier TEST brut | Brier TEST calibré |
|---|---:|---:|
| 1X2 | 0.204 | **0.204** |
| Over 2.5 | 0.249 | **0.242** |
| BTTS | 0.258 | **0.248** |

→ **Les 3 marchés passent sous 0.25 après calibration.**

Taux de base (train) : H/D/A = 0.429 / 0.256 / 0.316 · O2.5 = 0.501 · BTTS = 0.523.

## Calibration appliquée
Le modèle brut est **~2× trop confiant**. On applique un shrinkage vers les taux de base :

```
p' = w · p_modèle + (1 − w) · taux_de_base       (w = 0.5, optimal sur le train)
```

Implémenté dans `app/core/poisson.calibrate_probabilities`, appliqué par
`FootballAnalyzer.analyze`. Paramètres dans `settings` (`calibration_blend`,
`base_home/draw/away`, `base_over25`, `base_btts`). `calibration_blend = 1.0`
désactive la calibration.

Enseignement : le crash observé en live (Brier 0.35) venait des **micro-échantillons
Clausura de 10–13 matchs**, pas du modèle lui-même. Sur des stats roulantes
suffisantes + shrinkage, le moteur est honnêtement calibré.

## Limite : CLV non mesurable ici
La **Closing Line Value** exige, par pari, la cote *prise* ET la cote de *clôture*
**historiques**. Le fournisseur de cotes disponible (SharpAPI, tier gratuit) n'expose
ni Pinnacle ni les closing lines (Pro+), et aucune cote historique. La CLV n'est donc
**pas** mesurée ici. Pour `CALIBRATION_PROVEN = True`, il manque encore :
1. un flux de cotes de clôture (SharpAPI Pro+ `get_closing_lines`, ou archivage maison) ;
2. l'enregistrement de la cote réellement prise au moment du signal ;
3. une CLV moyenne positive sur un historique réglé suffisant.

Le Brier < 0.25 est une **condition nécessaire, pas suffisante** : le gate reste
`advisory_only` tant que la CLV n'est pas prouvée positive.

## Flux d'archivage CLV (implémenté)
L'infrastructure pour **mesurer** la CLV dès qu'un flux de cotes est branché :

- **Entrée** : `tracker.log_entry(...)` (ou `/api/analyze`) enregistre la cote *prise* au signal.
- **Clôture** : `POST /api/record_closing?prediction_id=&closing_odds=` (ou
  `tracker.record_closing`) archive la cote de *clôture* près du coup d'envoi.
- **Résultat** : `POST /api/settle?prediction_id=&won=` règle le pari.
- **Mesure** : `GET /api/calibration` renvoie `clv` (moyenne de `1/clôture − 1/prise`,
  positive = on a battu la clôture) et `clv_pct_beat_close`.

Script cron-able : `python -m scripts.archive_odds {pending|close|settle|report}`.
Il reste à alimenter les clôtures (SharpAPI Pro+ `get_closing_lines`, The Odds API,
ou archivage manuel) ; le test de bout en bout du flux est validé.
