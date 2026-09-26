---
name: apex-backtest
description: >
  Module de backtesting chronologique, de calibration et de simulation probabiliste de
  course, commun aux moteurs hippiques APEX (trot et obstacle). DÉCLENCHER pour toute
  demande de validation, de recalibration, de backtest, de walk-forward, de mesure de
  fiabilité d'un moteur hippique, de simulation Monte-Carlo d'une course, de probabilités
  de top 3 ou top 5, de probabilités de combinés, ou de prévision scellée avant départ
  (« backteste le moteur », « ce modèle est-il fiable », « simule la course », « quelles
  chances de placé », « probabilité du trio », « recalibre »). Fournit l'évaluation à
  origine glissante, les contrôles de fuite automatiques, les métriques groupées par
  course, la simulation à scénarios partagés et l'enregistrement scellé horodaté.
---

# APEX-BACKTEST v1.0

Module transversal. Il ne produit **aucun pronostic** : il mesure les moteurs, les
calibre, simule les arrivées et scelle les prévisions. Les moteurs de pricing restent
`apex-engine-trot-fr` et `apex-engine-obstacle-fr`.

**Lire `PREREGISTRATION.md` avant `REPORT.md`.** Le premier fixe les seuils, le second
donne les mesures. L'ordre des commits du dépôt établit que le premier précède le second.

## Statut de validation en vigueur

| Discipline | Pricing | Risque | Pari |
|---|---|---|---|
| **Trot attelé** | ✅ VALIDÉ | ✅ VALIDÉ | ❌ REFUSÉ |
| **Trot monté** | ❌ **REFUSÉ** | ✅ VALIDÉ | ❌ REFUSÉ |
| **Obstacle** | ✅ VALIDÉ | ✅ VALIDÉ | ❌ REFUSÉ |
| **Plat** | hors couverture | — | — |

Chiffres et critère par critère : `REPORT.md`.

## Utilisation

```bash
python3 scripts/leakage_check.py                    # doit sortir 0 avant tout backtest
python3 scripts/wf.py trot all                      # walk-forward, discipline entiere
python3 scripts/wf.py trot ATTELE                   # sous-ensemble
python3 scripts/wf.py obst all
python3 scripts/fit_shared.py obst                  # estime cf (chutes groupees) et tau
python3 scripts/bet_backtest.py trot                # regle PRE-ENREGISTREE uniquement
python3 scripts/predict.py 26092026 1 3 obst 20260926   # prevision scellee avant depart
```

`predict.py` refuse de tourner sur une course déjà courue et refuse de réécrire un
enregistrement existant.

## Règles de production issues des mesures

**Les deux paramètres de structure jointe s'inversent entre les disciplines.** Ils ont
été estimés séparément, et le résultat interdit de transposer l'un à l'autre.

| | **Trot** | **Obstacle** |
|---|---|---|
| Regroupement des non-terminaisons `cf` | **0,0** — aucun | **0,4** — réel, validé en test |
| Scénarios partagés `tau` | **0,7** | 0,4, sans effet mesurable |
| Top 3 en production | **simulateur** (test 0,4707 contre 0,4719) | **Harville/Stern** (test 0,5055 contre 0,5077) |

Lecture physique : une chute d'obstacle peut en entraîner d'autres et reflète un terrain
commun, donc les abandons se corrèlent ; une faute d'allure au trot est un événement
individuel, et la mesure le confirme — la validation retient `cf = 0` et le test est
identique avec ou sans regroupement (−6,2579 dans les deux cas).

1. **Top 3 : simulateur en trot, Harville/Stern en obstacle.** L'écart est faible dans
   les deux sens (0,0012 et 0,0022 en test) mais le signe est cohérent entre validation
   et test dans chaque discipline.
2. **Top 5, combinés, erreur numérique : toujours le simulateur.** Les probabilités de
   Trio et Tiercé se lisent **sur les arrivées simulées**, jamais comme un produit de
   marginales.
3. **Ne jamais réutiliser `cf` ou `tau` d'une discipline pour l'autre.** `predict.py`
   charge `params/shared_<discipline>.json` ; en son absence il retombe sur des valeurs
   par défaut, ce qui doit être signalé dans la sortie.
4. **Toujours reporter séparément** l'erreur Monte-Carlo et l'incertitude de modèle.
   Sur l'exemple exécuté, la seconde est **dix fois plus large** que la première.
5. **Trot monté : sortie INDICATIF obligatoire**, quel que soit le DCS. Le moteur y est
   moins bien calibré que le marché et l'échantillon est insuffisant.
6. **Une bonne calibration n'ouvre jamais la gate de pari.** Le trot bat maintenant le
   marché de façon significative sur la victoire et la gate reste fermée, faute de P2.

## Métriques imposées

Toute évaluation reporte, avec le **regroupement par course** pour l'incertitude :
nombre de courses et de partants · log-loss et Brier victoire · ECE et table de fiabilité
· top 3 et top 5 quand ils ont un sens · qualité de la porte de non-terminaison
(gain, monotonie, amplitude) · comparaison systématique à **trois références** : uniforme,
marché, moteur en production.

## Interdits

- Modifier un seuil de `PREREGISTRATION.md` après lecture d'un résultat, puis présenter
  le même test comme indépendant.
- Présenter une combinaison à zéro tirage comme impossible : elle est `< 1/N`.
- Multiplier des probabilités individuelles pour obtenir un combiné.
- Confondre « dans les trois premiers » et « gagnant au pari Placé », dont les règles
  dépendent du nombre de partants.
- Produire un pourcentage sans la mesure correspondante dans `REPORT.md`.
