# Journal de suivi consolidé — moteurs APEX turf

Tableau de bord des deux moteurs calibrés sur données réelles. Les journaux détaillés,
course par course, sont dans `apex-engine-*/journal/`.

**Dernière mise à jour : 22/09/2026 · 3 courses consignées.**

## État des moteurs

| | TROT-FR v1.0 | OBSTACLE-FR v1.0 |
|---|---|---|
| Courses d'apprentissage exploitables | 10 032 | 2 941 |
| Bloc de test | 2 208 | 648 |
| Période | avr. 2025 – sept. 2026 | mai 2024 – sept. 2026 |
| log-loss modèle / marché | 1,8788 / 1,8857 ✅ | 1,8491 / 1,8537 ✅ |
| ECE modèle / marché | 0,674 / 0,731 ✅ | 0,926 / 0,868 ❌ |
| Porte de risque (gain log-loss) | +0,0291 | +0,0140 |
| Taux de base du risque | 21,9 % (disqualification) | 19,3 % (non-terminaison) |
| **DCS calculé** | **72** | **51** |
| Gate de pari | quasi fermée (G-TROT-4) | **fermée** (G-OBST-4) |

## Bilan des courses consignées

| Date | Course | Moteur | DCS | Décision | Rang APEX du vainqueur | LL APEX | LL marché | Porte de risque |
|---|---|---|---|---|---|---|---|---|
| 22/09 | R2C1 Borély | TROT | 62 | NO BET | 8 / 11 | 3,540 | 3,270 | rien à détecter |
| 22/09 | R2C2 Borély | TROT | 62 | NO BET | 5 / 15 | 2,797 | 2,564 | ❌ échec |
| 22/09 | R1C1 Auteuil | OBSTACLE | 33 | INDICATIF | 6 / 9 | 3,170 | 3,124 | ✅ succès |
| | | | | **moyenne** | | **3,169** | **2,986** | |

**Sur ces trois courses les moteurs sont derrière le marché de 0,183 de log-loss.** À
n = 3 cela ne signifie rien : le gain théorique est de +0,0069 en trot et +0,0045 en
obstacle, soit un ordre de grandeur quarante fois plus petit que l'écart observé ici.
Il faut plusieurs centaines de lignes pour que ce tableau ait un sens.

## Capital engagé

**Zéro.** Aucun signal BET n'a été émis, sur aucune des trois courses. Les gates ont
fonctionné comme prévu : DCS 62 et 33, tous deux sous le seuil de 65 exigé par G-TROT-4,
et le moteur obstacle ne peut structurellement pas émettre de BET.

## Trois observations à tester, aucune à croire

### 1. L'APEX #1 a terminé 2ᵉ sur les trois courses

| Course | APEX #1 | Arrivée | APEX #2 | Arrivée |
|---|---|---|---|---|
| R2C1 | JOLIE COSTARDIÈRE | **2ᵉ** | JURDIG LESMELCHEN | **3ᵉ** |
| R2C2 | NADER | **2ᵉ** | NORREY | **3ᵉ** |
| R1C1 | DOCTORINO | **2ᵉ** | WANTOKNOWHATLOVEIS | non placé |

Trois fois sur trois. Si l'on admet une probabilité de l'ordre de 0,20 qu'un favori
finisse exactement deuxième, trois occurrences consécutives valent environ 1 chance sur
125. C'est remarquable sans être probant, et l'explication la plus simple reste le
hasard. Le marché avait les mêmes favoris : ce n'est donc pas un défaut propre au moteur,
c'est une série de favoris battus.

### 2. Le vainqueur est à chaque fois un cheval de milieu de classement

38,0 · 13,0 · 24,0 de cote finale. Manqué par le moteur **et** par le marché à chaque
fois. Rien n'indique pour l'instant que le moteur soit spécifiquement aveugle à ce
profil — le marché l'est autant.

### 3. Les deux portes de risque divergent fortement

- **Obstacle, R1C1** : les deux chevaux désignés les plus exposés (SEVERAN 26,1 % et
  NECTAR DES DIEUX 23,2 %) sont les deux premiers non-finissants. Trois abandons sur neuf
  partants, soit 33 % contre une base de 19,3 %.
- **Trot, R2C2** : les deux disqualifiés réels étaient classés **11ᵉ et 12ᵉ sur 15** du
  risque estimé. Le classement était quasiment inversé.

C'est d'autant plus notable que le backtest donnait l'avantage inverse : la porte de
faute du trot gagne +0,0291 de log-loss contre +0,0140 pour la porte de chute de
l'obstacle. **À n = 2 courses avec des non-finissants, cette inversion ne prouve rien,
mais c'est la mesure la plus importante à suivre** : la porte de risque est la seule
composante dont le gain soit démontré sur les deux moteurs.

## Prochaines étapes de validation

1. Accumuler des lignes. Trente courses par moteur donneront un premier signal sur la
   porte de risque ; il en faudra plusieurs centaines pour juger le modèle de victoire.
2. Collecter les rapports historiques Couplé, Trio et Tiercé, seuls marchés dont
   l'inefficience n'a pas encore été réfutée.
3. Si le motif « APEX #1 termine 2ᵉ » persistait au-delà d'une dizaine de courses,
   examiner la concentration de la distribution sur le haut du classement — l'exposant de
   Stern et la pénalité L2 seraient les premiers paramètres à revoir.
4. Valider le moteur trot sur un hiver complet (Vincennes, meeting d'hiver) : la fenêtre
   de test actuelle ne couvre que l'été 2026.
