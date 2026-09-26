---
name: apex-engine-trot-fr
description: >
  Protocole APEX-ENGINE TROT-FR v1.0 pour le trot français (attelé et monté, PMU).
  DÉCLENCHER pour toute analyse, pronostic, évaluation de cotes ou signal de pari sur
  une course de trot en France, même formulée de façon informelle (« analyse R2C1 »,
  « pronostic Vincennes », « que vaut ce quinté », « Borély ce matin », « apex-turf »,
  « ce cheval est-il jouable », « base du trio »). Logit conditionnel estimé par maximum
  de vraisemblance sur 10 032 courses (avril 2025 – septembre 2026), variables
  longitudinales cheval/driver/entraîneur construites en ordre chronologique strict,
  porte de disqualification logistique, correction de Stern pour le placé.
  NE PAS utiliser pour le galop (plat, haies, steeple) ni pour le trot étranger :
  le moteur n'est calibré que sur le trot français.
---

# APEX-ENGINE TROT-FR v1.0

Moteur de pricing pour le trot français. Contrairement aux moteurs football de la famille
APEX, celui-ci est calibré sur données réelles et **valide ses propres limites** : la
section « Domaine d'emploi » dit ce qu'il sait faire et, surtout, ce qu'il ne sait pas faire.

## 1. Domaine d'emploi

| Usage | Statut | Preuve |
|---|---|---|
| Estimer P(victoire) de chaque partant | **Validé** | log-loss test 1,8788 vs marché 1,8857 |
| Estimer P(disqualification) | **Validé** | log-loss test 0,5022 vs base 0,5313 |
| Estimer P(top 3) | **Validé, sans gain sur le marché** | 0,4788 vs marché+Stern 0,4783 |
| Générer un profit au Simple Gagnant | **NON démontré** | ROI +4,55 % IC95 [−9,7 % ; +19,5 %] |
| Générer un profit au Simple Placé | **RÉFUTÉ** | toutes les tranches en ROI négatif |
| Galop, trot étranger | **Hors domaine** | non calibré |

**Conséquence opératoire : le moteur est un instrument de mesure du risque, pas une
machine à produire du profit sur les marchés simples du PMU.** Toute sortie qui annonce
un « edge » sur le Simple Gagnant ou le Simple Placé doit être traitée comme du bruit,
sauf si elle franchit la gate G-TROT-4 ci-dessous.

## 2. Architecture

```
harvest.py       API PMU turfinfo -> JSONL brut (programme + participants + arrivée)
features.py      29 variables statiques (musique, gains, déferrage, recul, avis…)
longitudinal.py  21 variables d'historique cheval / driver / entraîneur / paire,
                 accumulées en ordre chronologique strict (aucune fuite)
dataset.py       assemblage + période de chauffe de 200 jours
model.py         logit conditionnel (softmax intra-course) par L-BFGS
                 + logistique de disqualification + Harville/Stern pour le placé
calibrate.py     estimation, sélection L2 sur validation, métriques sur test
validate.py      bootstrap du ROI, efficience du marché placé
analyze.py       notation d'une course à venir
```

### Spécification du modèle de victoire

Le modèle **n'essaie pas de remplacer le marché** : il le prend en offset et n'estime
que le résidu.

```
η_i = log(q_i / moyenne) + x_i' β        q_i = probabilité implicite du marché
P(i gagne) = softmax(η) sur les partants de la course
```

β est estimé sous pénalité L2 = 600 (choisie sur l'échantillon de validation). Cette
pénalité forte est le résultat honnête de l'estimation : **le marché contient déjà
presque toute l'information des variables de forme publiques.**

Un modèle fondamental sans les cotes a été estimé pour référence : log-loss test
**2,0558** contre 1,8857 pour le marché seul. Il est très nettement inférieur et ne doit
jamais être utilisé seul.

### Variables qui portent le résidu (coefficients standardisés)

| Variable | β | Lecture |
|---|---|---|
| `def4` | +0,086 | déferré des 4 pieds : le marché sous-évalue encore légèrement |
| `defpost` | +0,065 | déferré postérieurs seuls |
| `d_n` | +0,057 | volume de courses du driver (expérience) |
| `t_win` | +0,044 | taux de victoire de l'entraîneur (rétréci) |
| `h_rk` | +0,040 | vitesse récente : écart de réduction kilométrique au vainqueur |
| `place_rate` | −0,039 | **taux de place carrière élevé = moins de victoires** (profil « placeur ») |
| `h_last` | +0,036 | résultat de la dernière sortie |

### Porte de disqualification

Régression logistique sur les mêmes variables, taux de base **21,9 %** des partants.

| Variable | β | Lecture |
|---|---|---|
| `h_fault` | +0,314 | taux de faute historique du cheval (dominant) |
| `log_n` | *(v1.2)* | taille du champ — ajoutée le 26/09 après audit, voir ci-dessous |
| `hip_fault` | *(v1.2)* | difficulté de l'hippodrome, rétrécie, calculée sur le passé seul |
| `recul_m` | −0,126 | **un cheval reculé faute moins** (il est plus riche, donc plus sûr) |
| `place_rate` | −0,123 | régularité carrière |
| `d_fault` | +0,107 | taux de faute du driver |
| `mus_fault` | +0,100 | fautes dans la musique |

C'est la composante qui apporte le gain le plus net du moteur.

> **Recalibration v1.2 (26/09/2026), après audit post-course.** Un audit a révélé que
> la porte de faute ignorait **la taille du champ** et **la difficulté de l'hippodrome**.
> Sur le trot le biais était modéré (−3,32 pt à +1,23 pt selon la taille du champ, jusqu'à
> ±4,3 pt par hippodrome) — bien plus faible qu'en obstacle où il atteignait +13 pt. Les
> deux variables sont ajoutées, toutes deux connues avant la course. **Effet mesuré sur
> le trot : gain de la porte +0,0267 → +0,0274, amplitude Q5/Q1 inchangée à 3,65.** C'est
> dans le bruit. La correction est conservée parce qu'elle est juste, pas parce qu'elle
> améliore quelque chose de mesurable. Paramètres de production ré-estimés sur la base
> jusqu'au 25/09/2026 (10 032 courses, gain de la porte +0,0301 sur le découpage fixe).

### Placé

Harville sur les forces `p^λ` avec **λ = 0,70** (estimé sur validation). Le modèle de
Stern corrige le biais connu de Harville, qui surestime le placé des favoris.

## 3. DCS — Data Confidence Score

Le DCS de ce moteur n'est pas un nombre choisi : il est **calculé** à partir de mesures
hors échantillon.

| Composante | Barème | Mesure | Points |
|---|---|---|---|
| Intégrité des données | 25 | API officielle, 95,3 % des partants ont un passé en base | 23 |
| Calibration gagnant | 25 | ECE 0,674 pt (marché brut : 0,731 pt) | 23 |
| Pouvoir discriminant vs marché | 30 | gain de log-loss +0,0069 (0,37 % relatif) | 7 |
| Taille d'échantillon | 20 | 10 032 courses, test 2 208 | 19 |
| **DCS moteur** | **100** | | **72** |

> **Révision v1.1 (26/09/2026) après évaluation progressive.** Le DCS ci-dessus repose
> sur un découpage fixe 60/18/22. Le walk-forward sur 8 423 courses de prévision donne
> une image nettement meilleure : ECE **0,351 pt contre 0,645 pt** pour le marché et un
> gain de log-loss de **+0,0091, IC95 [+0,0058 ; +0,0122]** — strictement positif. Le DCS
> recalculé sur ces mesures est de **82** pour l'attelé. **Cela ne rouvre pas la gate de
> pari** : la règle pré-enregistrée déclenche 118 paris pour un ROI de −4,58 %,
> IC95 [−44,04 % ; +42,06 %]. P2 et P3 échouent, G-TROT-4 reste fermée.

Modificateurs à appliquer course par course :

- −10 si les cotes utilisées ne sont pas les cotes de départ (une analyse à H−1 travaille
  sur une information qui bougera encore)
- −8 si plus de 20 % du lot n'a aucun historique dans la base
- −6 en trot monté (échantillon plus faible, taux de faute plus élevé)
- −5 si moins de 8 partants (le modèle de placé n'est calibré que sur n ≥ 8)

**Gate DCS : en dessous de 60, sortie INDICATIF uniquement, aucun signal de pari.**

## 4. Gates de décision

- **G-TROT-0 — Monté.** Le trot monté est **refusé au pricing** par le backtest
  (`apex-backtest/REPORT.md`) : ECE 1,164 pt contre 0,923 pt pour le marché, et 693
  courses évaluées seulement contre le seuil de 1 000. Sortie **INDICATIF obligatoire**
  sur toute course montée, quel que soit le DCS. La porte de faute y reste valide
  (gain +0,0220, amplitude 2,82) avec un taux de base de **28,7 %** contre 21,2 % en
  attelé — la porte est donc plus utile encore en monté qu'en attelé.
- **G-TROT-1 — Champ.** Moins de 6 partants déclarés partants : ABORT.
- **G-TROT-2 — Cotes.** Un partant sans cote : ABORT (le modèle a besoin de l'offset).
- **G-TROT-3 — Faute.** Un cheval dont P(faute) > 25 % ne peut pas être base d'un pari
  combiné. Il peut figurer en associé.
- **G-TROT-4 — Pari simple.** Un signal BET sur Simple Gagnant exige **simultanément** :
  EV ≥ 1,15, cote ≤ 13, P(faute) ≤ 20 %, DCS ≥ 65. Sur le jeu de test, ce filtre ne
  produit presque aucun pari — **c'est voulu.** Le backtest montre qu'aucun seuil d'EV
  ne génère de profit significatif ; la gate est donc volontairement quasi fermée.
- **G-TROT-5 — Simple Placé.** NO BET par défaut. Le marché placé du PMU est en ROI
  négatif sur toutes les tranches de probabilité mesurées, de −4,6 % (les plus probables)
  à −89 % (les moins probables).
- **G-TROT-6 — Combinés.** Le moteur fournit les probabilités de Trio, Couplé et Tiercé
  par Harville/Stern, mais **aucun backtest de rentabilité n'a été mené sur ces marchés**
  (les rapports historiques Couplé/Trio n'ont pas été collectés). Sortie INDICATIF :
  donner la probabilité et le rapport minimum rentable, jamais un signal BET.

## 5. Biais favori-outsider mesuré

Sur les 2 208 courses de test, ROI d'une mise plate par tranche de cote finale :

| Cote | n | implicite | observé | ROI |
|---|---|---|---|---|
| 1–2 | 329 | 59,89 % | 51,37 % | −14,3 % |
| 2–3 | 1 062 | 40,88 % | 36,16 % | −11,8 % |
| 3–5 | 2 461 | 26,01 % | 23,28 % | −10,6 % |
| 5–8 | 2 915 | 15,97 % | 14,20 % | −11,0 % |
| 8–13 | 3 674 | 10,10 % | 7,81 % | −22,7 % |
| 13–21 | 3 649 | 6,31 % | 5,78 % | −7,8 % |
| 21–34 | 3 350 | 3,88 % | 2,60 % | −33,9 % |
| 34–60 | 3 663 | 2,27 % | 1,47 % | −37,0 % |
| 60+ | 5 555 | 1,04 % | 0,52 % | −55,1 % |

Le biais est massif et monotone au-delà de 20/1. **Aucune tranche n'est rentable.**
Un recalibrage du marché par exposant unique (τ = 1,15, c'est-à-dire « affûter » les
cotes) améliore déjà la log-loss à 1,8835 — preuve directe que les outsiders sont
sur-joués.

## 6. Procédure d'analyse

```bash
# 1. actualiser la base (incrémental conseillé : ne réaspirer que les jours manquants)
python3 scripts/harvest.py 2024-09-22 2026-09-21 hist.jsonl

# 2. recalibrer (à refaire tous les 2-3 mois)
python3 scripts/calibrate.py hist.jsonl

# 3. contrôler que l'edge reste non significatif avant tout signal
python3 scripts/validate.py hist.jsonl

# 4. noter une course à venir : date JJMMAAAA, réunion, course
python3 scripts/analyze.py 22092026 2 1 hist.jsonl params/apex_trot_fit.json
```

Le moteur sort pour chaque partant : cote, probabilité marché, probabilité APEX, EV
gagnant, P(faute), P(top 3).

## 7. Règles de rédaction d'une analyse

1. Annoncer le DCS calculé pour cette course, avec ses modificateurs.
2. Donner la hiérarchie APEX et l'écart au marché, sans jamais présenter un écart de
   moins de 15 % d'EV comme un signal.
3. Signaler explicitement les chevaux au-dessus de 25 % de risque de faute.
4. Conclure par une des cinq décisions : **BET** (G-TROT-4 franchie), **INDICATIF**,
   **NO BET**, **WAIT_ODDS** (cotes non définitives, écart proche du seuil),
   **ABORT** (gate G-TROT-1 ou G-TROT-2).
5. Ne jamais présenter une probabilité de ce moteur comme une certitude : l'écart type
   du ROI sur 1 661 paris est de 7,65 points.

## 8. Ce que le moteur ne capte pas

Sources d'information réelles mais absentes de la base, et donc payées au marché :

- l'état du terrain (pénétromètre non publié par l'API)
- les intentions d'écurie et le choix de driver de dernière minute
- le travail à l'entraînement, la condition physique du jour
- le matériel autre que le déferrage (enrênement, bottes, sulky)
- le parcours réellement couru (position en course, trafic, extérieur)
- la stratégie de course sur les départs à la volte

Ces facteurs expliquent pourquoi le marché conserve l'essentiel de l'avantage et
pourquoi β est aussi fortement pénalisé.
