---
name: apex-engine-obstacle-fr
description: >
  Protocole APEX-ENGINE OBSTACLE-FR v1.0 pour les courses d'obstacle françaises
  (haies, steeple-chase, cross — PMU). DÉCLENCHER pour toute analyse, pronostic,
  évaluation de cotes ou signal de pari sur une course d'obstacle en France, même
  formulée de façon informelle (« analyse R1C1 Auteuil », « pronostic haies »,
  « ce steeple », « Grand Steeple », « apex-turf Auteuil », « quinté obstacle »,
  « Compiègne haies », « Pau cross », « risque de chute »). Logit conditionnel
  estimé par maximum de vraisemblance sur 2 941 courses (mai 2024 – septembre 2026),
  variables de poids porté, valeur handicap et prix de réclamation, porte de chute
  logistique, correction de Stern pour le placé.
  NE PAS utiliser pour le trot (utiliser apex-engine-trot-fr) ni pour le plat :
  le moteur n'est calibré que sur l'obstacle français.
---

# APEX-ENGINE OBSTACLE-FR v1.0

Moteur de pricing pour les haies, le steeple-chase et le cross en France. Construit sur
le même appareil de preuve que `apex-engine-trot-fr`, et **il en sort avec un verdict
nettement moins favorable.** Cette section dit d'emblée ce qu'il faut en attendre.

## 1. Domaine d'emploi — lire avant tout

| Usage | Statut | Preuve |
|---|---|---|
| Estimer P(non-terminaison) | **Validé** | log-loss test 0,4368 vs base 0,4543 |
| Estimer P(victoire) | **Équivalent au marché, pas mieux** | 1,8491 vs 1,8537, mais **ECE 0,926 pt contre 0,868 pt pour le marché brut** |
| Estimer P(top 3) | **Sans gain** | 0,5195 vs marché+Stern 0,5191 |
| Générer un profit | **Non testable** | 58 paris au seuil 1,00, IC 95 % [−71,9 % ; +215,0 %] |
| Trot, plat | **Hors domaine** | non calibré |

**Le modèle de victoire est moins bien calibré que les cotes brutes du PMU.** Le gain de
log-loss de +0,0045 est réel mais il s'accompagne d'une dégradation de l'erreur de
calibration. La pénalité L2 retenue par la validation est de **2 500** — c'est-à-dire que
l'estimation écrase les coefficients à quasi-zéro : le plus fort vaut 0,018, contre 0,086
pour le moteur trot. **Traduction : sur l'obstacle, le marché n'a rien à apprendre des
variables publiques que je sais construire.**

**Conséquence : ce moteur ne produit jamais de signal BET.** Voir la gate G-OBST-4.

## 2. Ce qu'il apporte réellement : la porte de chute

Taux de non-terminaison de base : **19,3 % des partants**. Codes relevés dans les données :

| Code | Occurrences |
|---|---|
| ARRETE | 4 981 |
| TOMBE | 2 758 |
| DEROBE | 64 |
| DISTANCE | 35 |
| RESTE_AU_POTEAU | 6 |

Régression logistique, log-loss test **0,4543 → 0,4368** (gain **+0,0175**). Coefficients :

> **Correctif v1.0.1 (22/09/2026).** Le parseur de musique ne comptait pas le code `J`
> (jockey désarçonné) parmi les non-terminaisons, alors qu'il représente 4 792 des
> 31 872 entrées de non-terminaison de la base, soit **15 % du total ignoré**. Le défaut
> a été corrigé. Effet mesuré : la porte de chute est inchangée (+0,0139 contre +0,0140),
> le modèle de victoire gagne un peu en log-loss (1,8478 contre 1,8491) mais **perd en
> calibration** (ECE 1,053 contre 0,926). La correction est conservée parce qu'une
> variable qui décrit mal la réalité est un défaut latent, mais elle n'améliore rien de
> mesurable et le DCS passe de 51 à 50.

| Variable | β | Lecture |
|---|---|---|
| `log_distance` | **+0,262** | plus la course est longue, plus on chute — le facteur dominant |
| `mus_score` | −0,237 | un cheval en forme termine plus souvent |
| **`pen`** | **+0,223** | **terrain lourd = plus de non-terminaisons** |
| `log_experience` | −0,156 | l'expérience protège |
| `has_valeur` | +0,146 | les handicaps chutent davantage |
| `j_fall` | +0,126 | le taux de chute du jockey compte |
| **`pen_x_exp`** | **−0,117** | l'expérience protège **davantage** sur terrain lourd |
| `poids_rel` | **+0,102** | plus on porte lourd, plus on tombe |
| `valeur_rel` | −0,098 | les mieux notés chutent moins |

Ces signes sont tous physiquement cohérents, ce qui est le meilleur argument de validité
externe dont dispose ce moteur. **Attention cependant : la discrimination est faible.**
Les quintiles vont de 9,3 % à 28,8 % de risque prédit, contre 10,7 % à 39,5 % pour la
porte de faute du moteur trot. La porte de chute classe correctement mais sépare peu.

## 3. Variables propres à l'obstacle

Rien n'est repris du trot côté variables — seule la structure du code l'est.

- **`poids`, `poids_rel`, `poids_ecart_moy`** : le poids porté en kg, et l'écart au plus
  léger du lot. C'est la variable structurante de la discipline, sans équivalent en trot.
- **`has_valeur`, `valeur_rel`** : la valeur handicap officielle (`handicapValeur`),
  disponible uniquement dans les handicaps.
- **`has_reclam`, `reclam_rel`** : le prix de réclamation, dans les courses à réclamer.
- **`mus_obst`, `mus_plat`** : part de la musique courue en obstacle contre en plat —
  distingue le spécialiste du cheval qui descend du plat.
- **`mus_fall`** : proportion de non-terminaisons dans la musique (codes T, A, D, R).
- **`steeple`, `cross`, `log_distance`** : la discipline et la distance.
- Longitudinal : historique du cheval (dont son passé sur l'hippodrome et sur ce type
  d'obstacle), du **jockey** (montes, victoires, chutes), de l'entraîneur, du couple.

## 4. DCS — Data Confidence Score

Calculé, non décrété.

| Composante | Barème | Mesure | Points |
|---|---|---|---|
| Intégrité des données | 25 | API officielle, 85,1 % des partants ont un passé en base | 20 |
| Calibration gagnant | 25 | ECE 1,053 pt — **moins bon que le marché (0,868)** | 13 |
| Pouvoir discriminant vs marché | 30 | gain de log-loss +0,0059 (0,32 % relatif) | 6 |
| Taille d'échantillon | 20 | 2 941 courses, test 648 seulement | 11 |
| **DCS moteur** | **100** | | **50** |

Modificateurs par course : −10 si les cotes ne sont pas définitives · −8 si plus de 20 %
du lot est sans historique · −6 en cross · −5 si moins de 8 partants · −5 si plus d'un
quart du lot est inédit sur les obstacles.

**Le DCS moteur de 50 est déjà sous la gate de 60.** Aucune course d'obstacle ne peut
donc produire un signal de pari avec cette version. C'est le résultat de la mesure, pas
un choix de prudence.

## 5. Gates de décision

- **G-OBST-1 — Champ.** Moins de 5 partants : ABORT.
- **G-OBST-2 — Cotes.** Un partant sans cote : ABORT.
- **G-OBST-3 — Chute.** Un cheval dont P(chute) > 25 % ne peut pas être base d'un
  combiné. Signaler explicitement tout partant au-dessus de 22 %.
- **G-OBST-4 — Pari simple.** **Fermée.** Un BET exigerait DCS ≥ 65 ; le moteur plafonne
  à 50. Sortie maximale : INDICATIF. Cette gate ne se rouvrira qu'après une
  recalibration qui améliorerait l'ECE sous celui du marché.
- **G-OBST-5 — Placé.** NO BET. Le modèle est battu par le marché.
- **G-OBST-6 — Combinés.** INDICATIF seulement. Aucun rapport historique Couplé/Trio
  n'a été collecté sur l'obstacle.

## 6. Biais favori-outsider mesuré (648 courses de test)

| Cote | n | implicite | observé | ROI |
|---|---|---|---|---|
| 1–2 | 104 | 60,28 % | 57,69 % | −4,0 % |
| 2–3 | 262 | 41,03 % | 36,26 % | −12,5 % |
| 3–5 | 797 | 25,80 % | 22,21 % | −13,6 % |
| 5–8 | 969 | 15,88 % | 13,00 % | −18,1 % |
| 8–13 | 1 156 | 10,23 % | 7,70 % | −25,1 % |
| 13–21 | 1 002 | 6,32 % | 5,19 % | −22,5 % |
| 21–34 | 805 | 3,92 % | 4,10 % | +3,5 % |
| 34–60 | 698 | 2,29 % | 1,58 % | −27,5 % |
| 60+ | 438 | 1,21 % | 1,14 % | −1,8 % |

Le +3,5 % de la tranche 21–34 repose sur 33 gagnants : c'est du bruit, pas une poche
d'inefficience. À noter que les très gros favoris de l'obstacle (cote < 2) perdent
seulement 4,0 %, contre 14,3 % en trot — l'obstacle a moins de biais sur son sommet.

## 7. Procédure

```bash
python3 scripts/harvest_obst.py 2023-09-22 2026-09-21 hist.jsonl
python3 scripts/calibrate_obst.py hist.jsonl
python3 scripts/analyze_obst.py 22092026 1 1 hist.jsonl params/apex_obst_fit.json
```

`analyze_obst.py` refuse de tourner si `specialite != OBSTACLE` — le garde-fou est dans
le code, pas seulement dans ce document.

## 8. Rédaction d'une analyse

1. Annoncer le DCS calculé et rappeler que la gate BET est fermée.
2. Donner la hiérarchie et l'écart au marché, **sans jamais présenter un écart comme un
   signal** : sur l'obstacle le modèle est moins bien calibré que les cotes.
3. Mettre en avant la P(chute), qui est la seule sortie à valeur ajoutée démontrée.
4. Conclure par INDICATIF, NO BET ou ABORT. **Jamais BET.**

## 9. Ce que le moteur ne capte pas

> **Correctif v1.0.2 (22/09/2026).** Cette section affirmait que le pénétromètre n'était
> pas exposé par l'API. **C'était faux** : il est présent sur 4 037 des 4 040 courses
> aspirées (99,9 %), sous `course.penetrometre.valeurMesure`, et le harvester le
> collectait déjà sans que personne ne l'utilise. Il est désormais intégré **au seul
> modèle de chute** : étant constant par course, il ne survit pas au centrage
> intra-course du logit conditionnel et ses interactions n'apportaient que du bruit au
> modèle de victoire (ECE dégradée de 1,053 à 1,119). Effet mesuré sur la porte de
> chute : gain de log-loss **+0,0140 → +0,0175**, ECE **2,007 → 1,876**. `pen` devient
> le troisième coefficient du modèle.

Le détail du parcours et de la nature des haies, la condition physique, le
matériel, la tactique de course, et surtout **la qualité du saut** — qui est au cœur de
la discipline et qu'aucune variable disponible ne mesure. C'est la raison principale
pour laquelle le marché conserve ici tout son avantage.
