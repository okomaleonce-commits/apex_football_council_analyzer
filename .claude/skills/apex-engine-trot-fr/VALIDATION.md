# APEX-ENGINE TROT-FR v1.0 — rapport de validation

Rapport intégral des mesures hors échantillon. Toutes les valeurs sont reproductibles
avec `scripts/calibrate.py` et `scripts/validate.py`.

## Données

| | |
|---|---|
| Source | API PMU `online.turfinfo.api.pmu.fr/rest/client/1` |
| Période aspirée | 22/09/2024 → 21/09/2026 |
| Courses de trot françaises courues | 14 809 |
| Courses exploitables après filtres | **10 032** |
| Période exploitable | 10/04/2025 → 21/09/2026 (chauffe de 200 jours) |
| Partants | ~130 000 |

Filtres : au moins 6 partants, cote finale disponible pour tous, un et un seul vainqueur,
exclusion des non-partants.

### Découpage chronologique strict

| Bloc | Courses | Période |
|---|---|---|
| Apprentissage | 6 019 | 10/04/2025 → ~/01/2026 |
| Validation | 1 805 | ~/01/2026 → 30/05/2026 |
| **Test** | **2 208** | **31/05/2026 → 21/09/2026** |

Les variables longitudinales sont accumulées en parcourant les courses par date
croissante et ne sont lues **qu'avant** la mise à jour par le résultat de la course
en cours. Aucune information future n'entre dans une observation.

## Résultat principal — marché gagnant

| Modèle | log-loss test | Brier test |
|---|---|---|
| Marché PMU (cotes finales) | 1,8857 | 0,06793 |
| Marché recalibré, τ = 1,15 | 1,8835 | — |
| **APEX-TROT (résiduel)** | **1,8788** | — |
| Fondamental seul, sans cotes | 2,0558 | — |

Gain du moteur sur le marché : **+0,0069 de log-loss**, soit 0,37 % en relatif.
Le gain est cohérent entre validation (+0,0110) et test (+0,0069), ce qui écarte
l'hypothèse d'un artefact de sélection.

Le modèle fondamental seul est **inférieur de 0,17 de log-loss** au marché. C'est
l'ordre de grandeur de ce que le marché sait et que les données publiques de forme
ignorent.

### Calibration du modèle retenu (déciles, test)

| Décile | prédit | observé | n |
|---|---|---|---|
| D1 | 0,45 % | 0,30 % | 2 665 |
| D2 | 0,88 % | 0,56 % | 2 666 |
| D3 | 1,43 % | 1,43 % | 2 666 |
| D4 | 2,25 % | 1,73 % | 2 666 |
| D5 | 3,43 % | 3,38 % | 2 666 |
| D6 | 5,06 % | 5,78 % | 2 665 |
| D7 | 7,31 % | 7,91 % | 2 666 |
| D8 | 10,70 % | 10,73 % | 2 666 |
| D9 | 17,11 % | 17,78 % | 2 666 |
| D10 | 34,19 % | 33,23 % | 2 666 |

Erreur de calibration espérée (ECE, 20 classes) : **0,674 point** contre 0,731 pour
les probabilités implicites brutes du marché.

## Rentabilité — la mesure qui compte

Mise plate sur tout partant dont l'EV estimée dépasse le seuil. Intervalles de
confiance par bootstrap (4 000 rééchantillonnages).

| Seuil EV | Paris | ROI | écart-type | IC 95 % |
|---|---|---|---|---|
| 1,00 | 1 661 | +4,55 % | 7,65 pts | [−9,74 % ; +19,53 %] |
| 1,03 | 1 069 | −1,66 % | 8,82 pts | [−18,61 % ; +16,22 %] |
| 1,06 | 677 | +1,85 % | 10,33 pts | [−17,44 % ; +22,22 %] |
| 1,10 | 372 | −1,80 % | 12,90 pts | [−26,51 % ; +25,19 %] |
| 1,20 | 70 | −31,29 % | 23,72 pts | [−72,72 % ; +19,71 %] |

**Conclusion : aucun seuil ne produit de profit statistiquement significatif.** Le
+4,55 % au seuil 1,00 a un intervalle de confiance qui contient largement zéro, et la
non-monotonie de la série (positif, négatif, positif, négatif) est la signature du bruit.
Le moteur améliore la mesure de probabilité sans franchir le prélèvement du PMU.

## Marché placé

| Modèle | log-loss place (test, n ≥ 8 partants) |
|---|---|
| Marché + Stern | 0,4783 |
| APEX-TROT + Stern | 0,4788 |

Le moteur **ne bat pas** le marché au placé. Exposant de Stern retenu : λ = 0,70.

ROI réel des rapports Simple Placé définitifs, 3 125 courses collectées, par tranche de
probabilité estimée :

| P(top 3) | n | observé | rapport moyen | ROI |
|---|---|---|---|---|
| 2,2–6,1 % | 271 | 1,11 % | 9,53 | −89,45 % |
| 6,1–9,4 % | 271 | 6,64 % | 8,74 | −41,92 % |
| 9,4–14,2 % | 271 | 12,18 % | 6,66 | −18,93 % |
| 14,2–19,5 % | 272 | 15,44 % | 4,89 | −24,45 % |
| 19,5–26,2 % | 271 | 23,99 % | 3,28 | −21,25 % |
| 26,2–34,3 % | 271 | 34,69 % | 2,52 | −12,69 % |
| 34,4–47,7 % | 271 | 42,07 % | 2,13 | −10,52 % |
| 47,7–90,8 % | 272 | 58,82 % | 1,62 | −4,63 % |

Les probabilités estimées sont bien ordonnées et proches des fréquences observées
(12,18 % prédit → 12,18 % observé au 3ᵉ octile), mais **toutes les tranches perdent de
l'argent.** Le prélèvement du PMU au Simple Placé n'est franchi nulle part.

## Porte de disqualification — le seul gain net

Taux de base : **21,9 %** des partants sont disqualifiés, arrêtés, tombés ou distancés.

| | log-loss test |
|---|---|
| Taux de base constant | 0,5313 |
| **Modèle logistique** | **0,5022** |

Gain **+0,0291**, soit 5,5 % en relatif — huit fois le gain obtenu sur le marché gagnant.

| Quintile | prédit | observé |
|---|---|---|
| Q1 | 10,7 % | 9,8 % |
| Q2 | 15,3 % | 15,4 % |
| Q3 | 19,7 % | 21,3 % |
| Q4 | 26,1 % | 27,3 % |
| Q5 | 39,5 % | 37,9 % |

ECE : 1,508 point. Le classement est monotone et l'amplitude réelle (9,8 % → 37,9 %)
est presque aussi large que l'amplitude prédite.

## Lecture d'ensemble

Le moteur fait trois choses avec des degrés de confiance très différents :

1. **Il mesure correctement le risque de faute.** C'est neuf, c'est calibré, et c'est
   la contribution la plus solide. Une disqualification à 21,9 % de probabilité de base
   est le facteur dominant du trot et aucun affichage de cote ne l'exprime directement.
2. **Il reproduit le marché au gagnant avec une amélioration marginale mais réelle.**
   Utile pour ordonner un lot et pour construire des combinés, insuffisant pour parier.
3. **Il ne bat pas le marché au placé** et le backtest réfute toute stratégie placé.

La conséquence pratique est inconfortable mais elle est le résultat de la mesure :
sur les marchés simples du PMU, ce moteur sert à **refuser des paris**, pas à en trouver.

## Limites connues

- Les cotes d'apprentissage sont les **cotes finales**. Une analyse conduite à H−1
  travaille sur des cotes qui bougeront ; le moteur est alors hors de ses conditions
  d'estimation. Appliquer le modificateur DCS de −10.
- Les rapports historiques Couplé, Trio, Tiercé et Quinté n'ont pas été collectés :
  aucune affirmation de rentabilité n'est possible sur ces marchés.
- Le trot monté est sous-représenté et n'a pas été validé séparément.
- La base ne contient ni l'état du terrain, ni le matériel hors déferrage, ni le
  déroulé de course.
- La fenêtre de test couvre l'été 2026 (31 mai – 21 septembre). Une validation sur un
  hiver complet, avec Vincennes et le meeting d'hiver, reste à faire.
