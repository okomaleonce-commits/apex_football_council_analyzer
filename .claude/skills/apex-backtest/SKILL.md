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

1. **Top 3 : utiliser Harville/Stern, pas le simulateur.** Le simulateur à scénarios
   partagés perd contre la formule fermée (0,5077 contre 0,5055 en test). Mesuré, assumé.
2. **Top 5, combinés, non-terminaisons groupées, erreur numérique : utiliser le
   simulateur.** Les probabilités de Trio et Tiercé se lisent **sur les arrivées
   simulées**, jamais comme un produit de marginales.
3. **Regroupement des non-terminaisons `cf = 0,4`** : validé en test. Les abandons se
   corrèlent dans une même course.
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
