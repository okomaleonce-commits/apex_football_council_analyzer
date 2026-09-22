# APEX-ENGINE OBSTACLE-FR v1.0 — rapport de validation

Toutes les valeurs sont reproductibles avec `scripts/calibrate_obst.py`. La trace brute
du run est conservée dans `params/calibration_run.txt`.

## Données

| | |
|---|---|
| Source | API PMU `online.turfinfo.api.pmu.fr/rest/client/1` |
| Période aspirée | 22/09/2023 → 21/09/2026 (3 ans) |
| Courses d'obstacle françaises courues | 4 040 |
| Courses exploitables | **2 941** |
| Période exploitable | 20/05/2024 → 20/09/2026 (chauffe de 240 jours) |
| Répartition | haies 1 721 · steeple-chase 1 057 · cross 163 |
| Taille moyenne du champ | 9,7 partants |
| Taux de non-terminaison | **19,6 %** |

Filtres : au moins 5 partants, cote finale disponible pour tous, un et un seul vainqueur.

| Bloc | Courses | Période |
|---|---|---|
| Apprentissage | 1 764 | 20/05/2024 → ~/10/2025 |
| Validation | 529 | ~/10/2025 → 25/02/2026 |
| **Test** | **648** | **26/02/2026 → 20/09/2026** |

**L'échantillon est trois fois plus petit que celui du moteur trot** (2 941 contre
10 032), et le bloc de test quatre fois plus petit (648 contre 2 208). Toutes les
conclusions ci-dessous en portent la marque.

## Marché gagnant

| Modèle | log-loss test |
|---|---|
| Marché PMU (cotes finales) | 1,8537 |
| **APEX-OBSTACLE (résiduel)** | **1,8491** |
| Fondamental seul, sans cotes | 1,9861 |

Gain sur le marché : **+0,0045** (0,24 % relatif). Sur validation : +0,0024. Le signe est
cohérent entre les deux blocs, mais l'amplitude est deux fois plus faible que celle du
moteur trot (+0,0069).

**La pénalité L2 retenue est de 2 500**, contre 600 pour le trot. Le plus fort coefficient
du résidu vaut **0,018** (`t_fall`), contre 0,086 pour le trot. Le modèle a donc été
estimé, par la validation elle-même, comme devant être presque exactement le marché.

### Erreur de calibration — le point qui condamne la gate de pari

| | ECE (20 classes) |
|---|---|
| Marché PMU brut | **0,868 pt** |
| APEX-OBSTACLE | 0,926 pt |

**Le modèle est moins bien calibré que les cotes brutes.** C'est l'inverse du moteur trot
(0,674 contre 0,731). Un modèle qui gagne marginalement en log-loss tout en perdant en
calibration n'est pas utilisable pour décider d'une mise : la log-loss récompense la
confiance sur les bons cas, la calibration mesure si les probabilités affichées veulent
dire ce qu'elles disent. Pour parier, c'est la seconde qui compte.

Calibration par déciles (test) — correcte dans l'ensemble, mais irrégulière au milieu :

| Décile | prédit | observé | n |
|---|---|---|---|
| D1 | 1,09 % | 1,12 % | 623 |
| D2 | 2,05 % | 1,93 % | 623 |
| D3 | 3,21 % | 4,17 % | 623 |
| D4 | 4,54 % | **3,21 %** | 623 |
| D5 | 6,22 % | **7,70 %** | 623 |
| D6 | 8,24 % | **6,74 %** | 623 |
| D7 | 10,39 % | 10,43 % | 623 |
| D8 | 13,95 % | 13,00 % | 623 |
| D9 | 19,78 % | 19,90 % | 623 |
| D10 | 34,49 % | 35,74 % | 624 |

Les déciles 4, 5 et 6 oscillent de ±25 % en relatif. Avec 623 observations par décile,
c'est en partie du bruit — mais c'est exactement la zone de cotes où un pari de valeur
se déciderait.

## Rentabilité — non testable

| Seuil EV | Paris | Gagnants | ROI | IC 95 % bootstrap |
|---|---|---|---|---|
| 1,00 | 58 | 7 | +42,76 % | **[−71,90 % ; +215,01 %]** |
| 1,05 | 17 | 3 | +238,82 % | [−100,00 % ; +776,47 %] |
| 1,10 | 4 | 1 | +925,00 % | [−100,00 % ; +2975,00 %] |
| 1,20 | 0 | — | — | — |

La pénalité L2 de 2 500 écrase les écarts au marché : seuls **58 paris** franchissent le
seuil d'EV 1,00 sur 648 courses. Les intervalles de confiance sont si larges qu'ils
n'excluent rien. **Aucune affirmation de rentabilité n'est possible, dans aucun sens.**

## Place

| Modèle | log-loss place (test, n ≥ 8) |
|---|---|
| Marché + Stern | **0,5191** |
| APEX-OBSTACLE + Stern | 0,5195 |

Le moteur est battu. Exposant de Stern retenu : λ = 0,82 (contre 0,70 en trot — les
favoris de l'obstacle tiennent mieux leur rang au placé).

## Porte de chute — la seule contribution nette

Taux de base : **19,3 %**.

| | log-loss test |
|---|---|
| Taux de base constant | 0,4543 |
| **Modèle logistique** | **0,4404** |

Gain **+0,0140**, soit 3,1 % en relatif. ECE : 1,987 pt.

| Quintile | prédit | observé |
|---|---|---|
| Q1 | 9,3 % | 10,4 % |
| Q2 | 13,4 % | 13,9 % |
| Q3 | 16,5 % | 14,8 % |
| Q4 | 20,5 % | 18,0 % |
| Q5 | 28,8 % | 26,7 % |

Le classement est monotone et l'ordre est respecté, mais **l'amplitude réelle ne va que
de 10,4 % à 26,7 %** — un facteur 2,6 entre les extrêmes, contre 3,9 pour la porte de
faute du moteur trot. Le modèle sait dire qui risque le plus, mais il sépare peu.

Les coefficients sont en revanche tous physiquement interprétables, ce qui constitue la
meilleure validation externe disponible : la distance domine, l'expérience et la forme
protègent, le poids et le taux de chute du jockey aggravent.

## Comparaison avec le moteur trot

| | TROT-FR | OBSTACLE-FR |
|---|---|---|
| Courses exploitables | 10 032 | 2 941 |
| Bloc de test | 2 208 | 648 |
| Gain de log-loss vs marché | +0,0069 | +0,0045 |
| ECE modèle vs marché | **0,674 / 0,731** ✅ | **0,926 / 0,868** ❌ |
| L2 retenue | 600 | 2 500 |
| Plus fort coefficient du résidu | 0,086 | 0,018 |
| Gain de la porte de risque | +0,0291 | +0,0140 |
| Amplitude de la porte de risque | 10,7 → 39,5 % | 9,3 → 28,8 % |
| **DCS** | **72** | **51** |

Sur tous les axes, l'obstacle est plus difficile à modéliser que le trot avec les données
publiques. Deux explications tiennent :

1. **La qualité du saut n'est mesurée par aucune variable disponible.** En trot, la faute
   d'allure a un antécédent lisible dans la musique et se répète ; en obstacle, la chute
   dépend d'un parcours, d'une trajectoire et d'un terrain dont rien ne reste dans les
   données.
2. **L'état du terrain est décisif en obstacle et l'API ne publie pas le pénétromètre.**
   Un terrain lourd redistribue complètement les chances ; le marché l'intègre le matin
   même, le modèle jamais.

## Limites

- Échantillon de test de 648 courses : la puissance statistique est faible.
- Le cross n'est représenté que par 163 courses et n'a pas été validé séparément.
- Les cotes d'apprentissage sont les cotes finales ; une analyse à H−1 est hors des
  conditions d'estimation.
- Aucun rapport historique Couplé, Trio, Tiercé ou Quinté n'a été collecté.
- Le terrain, la nature des obstacles et la qualité du saut sont absents de la base.
