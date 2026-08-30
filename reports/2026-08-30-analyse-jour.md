# APEX — Analyse des matchs du dimanche 30 août 2026

> Chaîne exécutée : SCRAPER → S1 → S5 → S6 → S7. Moteurs de ligue : `apex-engine-epl` v1.6,
> `apex-engine-serie-a` v1.5, `apex-engine-ligue1`, `apex-engine-jpl` v1.1.

## Verdict global

**NO BET validé.** Aucun signal ne franchit les gates du protocole. Un seul candidat
survit au test de sensibilité : **Monaco (1) @ 2.28**, en statut CONDITIONNEL / WAIT_LINEUPS.

## Log d'exécution

```
[SCRAPER ⚠] cotes = 1 agrégateur secondaire (pas de Pinnacle) | xG saison INDISPONIBLE (J2-J3)
[S1  ⚠] DRS 52-61 DEGRADED sur les 5 matchs | bloc5 (cotes) PARTIAL | bloc2 (xG) MISSING
[S4  ⚠] biais domicile systématique -8.62 pts → recalibration k=1.140 imposée
[S5  ✗] VS 65-85 : DRS_DEGRADED 20 + NO_XG_DATA 10 + incertitude>20% 15 + rotation 20
[S6  ✗] SUSPICIOUS_EDGE sur tous les edges > 15% | 1 seul book → pas de lecture de flux
[S7  ✗] NO_BET — convergence insuffisante, gates DCS non franchies
```

## Le diagnostic central

Le modèle brut sortait des edges de **+27% à +92%, tous du côté extérieur, sur 5 matchs
indépendants**. Ce n'est pas cinq value bets, c'est un biais : ratings construits sur des
buts toutes-compétitions non splittés domicile/extérieur. Écart moyen sur la proba
domicile : **-8.62 points**.

Après recalibration sur le consensus marché (k=1.140), test de sensibilité — l'edge
bouge-t-il quand on retire mes propres hypothèses d'absences ?

| Match | edge « 2 » AVEC hypothèses | SANS | Amplitude | Lecture |
|---|---|---|---|---|
| Lazio–Genoa | +42.5% | -3.9% | **46 pts** | hypothèse, pas signal |
| Man Utd–Ipswich | +38.9% | -1.2% | **40 pts** | hypothèse, pas signal |
| Napoli–Como | +38.7% | +16.6% | **22 pts** | hypothèse, pas signal |
| Chelsea–Brighton | +12.9% | +19.5% | 7 pts | résidu de calibration |
| **Monaco–Marseille (1)** | **+19.5%** | **+18.5%** | **1 pt** | **robuste** |

Un signal dont l'edge se déplace de 40 points selon une hypothèse d'analyste n'est pas
un signal. Trois des quatre « grosses value » du jour sont mes propres coefficients AIS-F
qui se regardent dans le miroir.

## Le piège évité : Over 2.5 Monaco–Marseille

Mon modèle donnait λ_total = 3.80 → Over 2.5 à 73.1% → edge **+18.7%** sur la cote 1.53.
Très tentant. Sauf que le seuil de rentabilité de cette cote est **λ ≥ 3.38**, et la
référence empirique 2025/26 des deux équipes est **3.26 buts/match** (Monaco 3.35, OM 3.18).

Le +18.7% venait de la composition multiplicative attaque × défense qui surcote les
matchs entre deux équipes offensives et poreuses. Le marché price déjà 61.6% contre une
baseline Ligue 1 de 54.8% : il a **déjà vu** que le match est ouvert. **Pas de value.**

## Matchs analysés — prix d'entrée

Cote minimale pour un edge ≥ 3% (filtre 1 de S7), scénario central honnête.

| Match | Marché | Cote | p_model | Fair | Entrée | Statut |
|---|---|---|---|---|---|---|
| Monaco–Marseille | **1** | **2.28** | **47.6%** | **2.10** | **2.17** | ✅ seul survivant |
| Monaco–Marseille | O2.5 | 1.53 | 64.1% | 1.56 | **1.61** | ✗ il manque 5% |
| Chelsea–Brighton | 2 | 4.00 | 27.0% | 3.71 | 3.82 | ~ résidu, non robuste |
| Chelsea–Brighton | O2.5 | 1.63 | 58.3% | 1.71 | 1.77 | ✗ |
| Man Utd–Ipswich | 1 | 1.37 | 65.8% | 1.52 | 1.56 | ✗ marché trop court |
| Napoli–Como | 1 | 2.43 | 34.8% | 2.87 | 2.96 | ✗ |
| Lazio–Genoa | U2.5 | 1.53 | 54.6% | 1.83 | 1.89 | ✗ marché efficient |

## Pourquoi rien n'est validé

1. **Aucune donnée xG exploitable.** J2–J3 : deux matchs joués. Les ratings reposent sur
   les tables finales 2025/26, pas sur la saison en cours. `NO_XG_DATA` → incertitude +15%.
2. **Pas de cotes sharp.** Un seul agrégateur secondaire, pas de Pinnacle, pas de Betfair,
   donc pas de démarginisation de référence ni de lecture de mouvement de ligne. S6 exige
   3 books minimum : **non satisfait**. DCS bloqué sous les gates (70 EPL / 65 Serie A / 70 L1).
3. **Mercato ouvert jusqu'au 1er septembre.** Les effectifs de ce week-end ne sont pas ceux
   de la semaine prochaine.
4. **Aucune compo confirmée** au moment de l'analyse.

## Le candidat conditionnel

**Monaco (1) @ 2.28** — Ligue 1 J2, 20h45 CEST, Stade Louis-II.

- Edge +5.3%, EV +8.5%. Seul signal insensible aux hypothèses d'absences.
- Pour : HOME_ADV Ligue 1 à 1.16 (2e du top 5) ; Monaco a gagné ses 3 dernières
  réceptions de l'OM en L1 ; **Egan-Riley et Balerdi (les deux charnières centrales de
  l'OM) absents** → CB_DÉGRADÉE.
- Contre : Monaco amputé de Balogun, Fati et Minamino ; match de Conference League jeudi
  quand l'OM avait une semaine pleine ; l'OM sort d'un 4-0 avec 67% de possession.
- Statut protocole : **WAIT_LINEUPS**. Mise plafonnée à 0.5–0.75 u si joué malgré tout,
  et seulement à cote ≥ 2.20.

Conditions d'invalidation : compo Monaco avec rotation ≥ 4 titulaires ; cote sous 2.17 ;
Zakaria ou Golovin forfait.

## Correctif prioritaire du repo

`.env` sans clés : `API_FOOTBALL_KEY`, `FOOTBALL_DATA_KEY`, `ODDS_API_KEY` vides. Le
pipeline `app/core/data_fetcher.py` ne peut rien récupérer, d'où la collecte manuelle par
recherche web et un DRS plafonné à ~60. Renseigner ces trois clés ferait passer le DRS
au-dessus de 75 et rendrait les gates franchissables.

## Matchs non analysés

Faute de socle de données suffisant : Leeds–Brentford, Sunderland–Fulham, Paris FC–Nice,
Rennes–Le Mans, Real Madrid–Málaga, Deportivo–Valence, Celta–Bilbao, Fribourg–Werder,
Augsbourg–Schalke, Union SG–Anderlecht (format playoffs JPL → ratings 2025/26 invalides),
Cagliari–Inter (**conflit sur l'heure de coup d'envoi** : 15h45 ou 20h45 selon les sources
→ S1 bloque), et le programme Eredivisie / Nordiques / Brasileirão.
