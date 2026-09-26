# Pré-enregistrement des critères d'acceptation — APEX-BACKTEST v1.0

**Écrit et commité avant l'exécution du moindre backtest.** L'ordre des commits du dépôt
fait foi. Aucun seuil ci-dessous ne sera modifié après lecture des résultats ; si un
seuil se révèle mal choisi, il sera changé **dans une version ultérieure**, explicitement
datée, et la présente version restera au dépôt comme référence.

## 1. Portée

| Discipline | Moteur | Statut |
|---|---|---|
| Trot attelé | `apex-engine-trot-fr` | couvert |
| Trot monté | `apex-engine-trot-fr` | **couvert mais non calibré séparément** — à mesurer |
| Obstacle (haies, steeple, cross) | `apex-engine-obstacle-fr` | couvert |
| **Plat** | **aucun** | **hors couverture, aucun résultat ne sera produit** |

Le trot et l'obstacle ont des moteurs distincts, des variables distinctes et des
coefficients estimés séparément. Aucun coefficient n'est transposé de l'un à l'autre.
La question « attelé et monté doivent-ils être séparés ? » est posée comme une **mesure**
et non comme une hypothèse : elle sera tranchée par la comparaison log-loss ci-dessous.

## 2. Protocole d'évaluation progressive (walk-forward)

- Origine glissante par blocs trimestriels. Pour chaque origine *t* : apprentissage sur
  tout le passé jusqu'à *t*, prévision du trimestre *[t, t+1[*, puis avancée.
- **Le regroupement est la course, jamais le partant.** Aucune course n'est scindée
  entre apprentissage et prévision.
- La pénalité L2 est choisie **à l'intérieur de la fenêtre d'apprentissage**, sur son
  dernier cinquième, jamais sur la fenêtre de prévision.
- Les blocs de prévision ne sont jamais réutilisés pour régler quoi que ce soit.

## 3. Interdits de fuite

Sont exclus par construction, et l'absence de chacun est vérifiée par un test
automatique dans `scripts/leakage_check.py` :

1. Tout résultat de la course évaluée (rang, incident, temps, réduction kilométrique).
2. Toute variable longitudinale mise à jour par la course évaluée : l'état n'est lu
   qu'**avant** son intégration.
3. La valeur handicap révisée après la course — seule la valeur publiée au programme est
   utilisée.
4. Les commentaires d'après-course (`commentaireApresCourse`), jamais collectés.
5. **Les cotes** : le backtest utilise les cotes finales, ce qui est une **limite
   assumée et déclarée**, pas une fuite au sens strict (elles sont antérieures au
   départ), mais elles ne sont pas disponibles à H−1. Toute analyse en direct applique
   le malus DCS correspondant.

## 4. Références de comparaison obligatoires

Chaque métrique est reportée face à trois références :

1. **Uniforme** : 1/n par partant.
2. **Marché** : probabilités implicites des cotes, normalisées.
3. **Moteur actuel** : la version en production au moment du test.

## 5. Seuils d'acceptation — fixés maintenant

Un moteur passe en statut **VALIDÉ POUR LE PRICING** si, sur l'agrégat walk-forward :

| Critère | Seuil |
|---|---|
| V1 log-loss victoire | strictement inférieure au marché |
| V2 ECE victoire (20 classes) | **inférieure ou égale** à celle du marché |
| V3 stabilité | le gain V1 positif sur **au moins 60 %** des blocs trimestriels |
| V4 volume | au moins 1 000 courses dans l'agrégat de prévision |

Un moteur passe en statut **VALIDÉ POUR LE RISQUE** (porte de chute / faute) si :

| Critère | Seuil |
|---|---|
| R1 log-loss non-terminaison | gain ≥ +0,010 sur le taux de base |
| R2 monotonie | les 5 quintiles de risque prédit sont **strictement croissants** en observé |
| R3 amplitude | rapport observé Q5/Q1 ≥ **2,0** |

Un moteur passe en statut **VALIDÉ POUR LE PARI** si, et seulement si :

| Critère | Seuil |
|---|---|
| P1 | V1 **et** V2 satisfaits |
| P2 ROI | borne **inférieure** de l'IC 95 % par bootstrap **par course** strictement > 0 |
| P3 volume | au moins 200 paris déclenchés par la règle |
| P4 | la règle de sélection est écrite avant le test et non modifiée ensuite |

**L'échec d'un seul critère suffit à refuser le statut.** Une bonne calibration
n'ouvre pas la gate de pari : P2 est indispensable et ne se déduit pas de V1-V2.

## 6. Règle de sélection des paris — figée avant test

Déclenchement d'un pari simple gagnant si **toutes** les conditions sont réunies :
`EV = p_modèle × cote ≥ 1,15` · `cote ≤ 13,0` · `P(non-terminaison) ≤ 0,20` ·
`nombre de partants ≥ 8`.

Mise plate d'une unité. Règlement au **rapport réellement payé** du pari mutuel PMU,
net de prélèvement (le rapport PMU est déjà net). Non-partants : mise remboursée,
pari retiré du décompte. Aucune cote fixe n'est utilisée : le PMU est mutuel, le
rapport n'est connu qu'au départ, et le backtest l'assume.

## 7. Précision numérique de la simulation

- Départ à 10 000 tirages, puis doublement jusqu'à ce que **l'erreur Monte-Carlo
  maximale sur les probabilités de victoire des partants dépasse pas 0,20 point**,
  plafond à 1 000 000 tirages.
- L'erreur Monte-Carlo (`sqrt(p(1−p)/N)`) est reportée **séparément** de l'incertitude
  de modèle, estimée par ré-estimation bootstrap au niveau course.
- Le nombre de tirages réellement exécuté est reporté. Une combinaison à zéro tirage est
  reportée comme « < 1/N », jamais comme impossible.

## 8. Traçabilité

Chaque prévision produite avant une course réelle est scellée dans un enregistrement
horodaté comprenant : date et heure de production, version du moteur, empreinte SHA-256
du fichier de paramètres, graine aléatoire, nombre de tirages, instantané des cotes
utilisé avec son horodatage, et la totalité des probabilités produites. Le fichier est
écrit avant le départ et n'est jamais réécrit.

## 9. Engagement de restitution

Aucun pourcentage ne sera présenté comme validé sans la mesure correspondante dans un
rapport reproductible. Si une donnée ou un moyen de calcul manque, le point est déclaré
**exploratoire** et non mesuré. Aucun historique, résultat de backtest ou simulation ne
sera inventé.
