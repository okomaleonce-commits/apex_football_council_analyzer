# APEX-BACKTEST v1.0 — rapport d'exécution

Toutes les valeurs proviennent d'exécutions réelles des scripts de `scripts/`.
Critères fixés dans `PREREGISTRATION.md`, commité **avant** toute exécution (`7ab8c6a`).

## 1. Volume évalué

| Discipline | Courses en base | **Courses évaluées en prévision** | Partants évalués | Période |
|---|---|---|---|---|
| Trot (tout) | 10 032 | **8 423** | 104 731 | 07/2025 → 09/2026 |
| — Trot attelé | 8 603 | 7 226 | 90 979 | idem |
| — **Trot monté** | 1 429 | **693** | 7 822 | idem |
| Obstacle | 2 949 | **2 142** | 20 846 | 01/2025 → 09/2026 |
| **Plat** | 0 | **0** | 0 | hors couverture |

Source unique : API PMU `online.turfinfo.api.pmu.fr`. Données manquantes déclarées :
pas de valeur handicap hors handicaps, pas de style de course ni de position en course,
pas de qualité de saut, pas de matériel hors déferrage.

## 2. Protocole exécuté

Origine glissante trimestrielle. À chaque origine : ré-estimation complète sur tout le
passé, L2 choisie sur le dernier cinquième de la fenêtre d'apprentissage, prévision du
trimestre suivant, puis avancée. Aucune course scindée. 7 blocs en obstacle, 5 en trot.

**Contrôles de fuite** (`scripts/leakage_check.py`, sortie 0) : inspection de l'AST des
fonctions de production. Aucune lecture de `ordreArrivee`, `incident`, `tempsObtenu`,
`reductionKilometrique`, `distanceChevalPrecedent` ni `commentaireApresCourse`. L'état
longitudinal est lu avant sa mise à jour. Une fonction morte du module trot qui lisait
les résultats a été supprimée à cette occasion.

**Limite déclarée, non corrigée :** le backtest utilise les cotes finales. Elles sont
antérieures au départ mais postérieures à H−1. Ce n'est pas une fuite au sens strict,
c'est un avantage dont une analyse en direct ne dispose pas — d'où le malus DCS de −10.

## 3. Résultats mesurés

### Victoire

| | courses | log-loss modèle | marché | uniforme | **gain** IC95 par course | ECE modèle | ECE marché | Brier |
|---|---|---|---|---|---|---|---|---|
| **Trot (tout)** | 8 423 | **1,9100** | 1,9191 | 2,4981 | **+0,0091 [+0,0058 ; +0,0122]** | **0,351 pt** | 0,645 pt | 0,06612 / 0,06621 |
| **Trot attelé** | 7 226 | **1,9105** | 1,9197 | 2,5115 | **+0,0092 [+0,0057 ; +0,0127]** | **0,300 pt** | 0,702 pt | — |
| **Trot monté** | 693 | 1,8859 | 1,8870 | 2,3999 | +0,0013 **[−0,0100 ; +0,0123]** | **1,164 pt** | 0,923 pt | — |
| **Obstacle** | 2 142 | **1,8661** | 1,8688 | 2,2285 | +0,0028 **[−0,0018 ; +0,0071]** | **0,532 pt** | 0,723 pt | 0,08769 / 0,08779 |

Stabilité (V3) : trot 5/5 blocs = 100 % · attelé 5/5 = 100 % · monté 2/3 = 67 % ·
obstacle 6/7 = 86 %.

**Ce tableau corrige le précédent.** Sur un découpage fixe 60/18/22, l'ECE du moteur
obstacle ressortait à 1,053 contre 0,868 pour le marché, et j'en avais conclu qu'il était
moins bien calibré. En évaluation progressive — où le modèle est ré-estimé sur tout le
passé à chaque origine — il ressort à **0,532 contre 0,723**. Le verdict précédent était
un artefact du découpage, pas une propriété du moteur.

### Non-terminaison (disqualification en trot, chute ou arrêt en obstacle)

| | taux de base | log-loss base → modèle | **gain** | monotone | amplitude Q5/Q1 |
|---|---|---|---|---|---|
| Trot (tout) | 22,2 % | 0,5288 → **0,5021** | **+0,0267** | oui | **3,66** |
| Trot attelé | 21,2 % | 0,5170 → 0,4903 | +0,0267 | oui | 3,77 |
| Trot monté | **28,7 %** | 0,5995 → 0,5774 | +0,0220 | oui | 2,82 |
| Obstacle | 19,7 % | 0,4958 → **0,4784** | **+0,0174** | oui | **2,97** |

### Paris — règle pré-enregistrée (EV ≥ 1,15 · cote ≤ 13 · chute ≤ 0,20 · n ≥ 8)

Règlement au rapport PMU réellement payé, déjà net de prélèvement. Mise plate.
IC 95 % par bootstrap **au niveau course**.

| | paris | gagnants | ROI | IC 95 % |
|---|---|---|---|---|
| **Trot** | **118** | 21 | **−4,58 %** | **[−44,04 % ; +42,06 %]** |
| **Obstacle** | **21** | 1 | **−89,05 %** | **[−100 % ; −63,20 %]** |

Sensibilité du seuil (trot) : EV≥1,00 → +4,07 % [−7,60 ; +15,27] sur 1 455 paris ·
EV≥1,05 → −1,00 % · EV≥1,10 → +2,80 % · EV≥1,25 → +46,09 % sur 23 paris. La série
alterne : c'est du bruit.

**Défaut de conception à signaler** : la référence « marché » ne déclenche aucun pari,
par construction — son EV vaut 1/surcote, donc toujours inférieure à 1. La comparaison
de rentabilité modèle-contre-marché n'est donc pas informative telle que je l'ai écrite,
et devra être remplacée par une référence de type « parier le favori » dans la v1.1.

## 4. Statut de validation, critère par critère

| Critère | Trot attelé | Trot monté | Obstacle |
|---|---|---|---|
| V1 log-loss < marché | ✅ | ✅ (mais IC contient 0) | ✅ (mais IC contient 0) |
| V2 ECE ≤ marché | ✅ 0,300 / 0,702 | ❌ **1,164 / 0,923** | ✅ 0,532 / 0,723 |
| V3 gain positif ≥ 60 % des blocs | ✅ 100 % | ✅ 67 % | ✅ 86 % |
| V4 ≥ 1 000 courses | ✅ 7 226 | ❌ **693** | ✅ 2 142 |
| **PRICING** | **✅ VALIDÉ** | **❌ REFUSÉ** | **✅ VALIDÉ** |
| R1 gain ≥ +0,010 | ✅ +0,0267 | ✅ +0,0220 | ✅ +0,0174 |
| R2 quintiles croissants | ✅ | ✅ | ✅ |
| R3 amplitude ≥ 2,0 | ✅ 3,77 | ✅ 2,82 | ✅ 2,97 |
| **RISQUE** | **✅ VALIDÉ** | **✅ VALIDÉ** | **✅ VALIDÉ** |
| P2 borne basse ROI > 0 | ❌ −44 % | non testé | ❌ −100 % |
| P3 ≥ 200 paris | ❌ 118 | non testé | ❌ 21 |
| **PARI** | **❌ REFUSÉ** | **❌ REFUSÉ** | **❌ REFUSÉ** |

**Conséquence la plus importante : le moteur trot est désormais bien calibré et bat le
marché de façon statistiquement significative sur la victoire — et la gate de pari reste
fermée.** C'est exactement ce que le pré-enregistrement annonçait : une bonne calibration
ne démontre pas une rentabilité. Le prélèvement du PMU n'est franchi nulle part.

**Le trot monté est refusé au pricing.** Mettre attelé et monté dans un même moteur
n'était pas justifié : le monté a un taux de non-terminaison de 28,7 % contre 21,2 %, un
échantillon quatre fois plus petit, et une calibration inférieure au marché. Une gate
dédiée est ajoutée aux deux moteurs.

## 5. Structure jointe — deux paramètres estimés, un résultat négatif

### Regroupement des non-terminaisons : **réel et mesuré**

`cf` estimé par maximum de vraisemblance sur les effectifs de non-finissants par course,
intégration de Gauss-Hermite à 21 nœuds, marginales préservées par recentrage.

| cf | log-vraisemblance / course (validation) |
|---|---|
| 0,0 | −4,6594 |
| 0,2 | −4,6517 |
| **0,4** | **−4,6416** |
| 0,6 | −4,6467 |
| 0,9 | −4,6868 |

**Test : −4,6331 avec cf = 0,4 contre −4,6524 sans.** Les chutes et arrêts se regroupent
bel et bien dans une même course. Conséquence concrète : la probabilité qu'un trio
« survive » n'est pas le produit des probabilités individuelles de terminer.

### Scénarios partagés : **le simulateur est battu par la formule simple**

| Modèle top 3 | validation | test |
|---|---|---|
| Simulateur, τ = 0,4 | 0,5172 | 0,5077 |
| **Harville/Stern λ = 0,82** | **0,5142** | **0,5055** |

Le gain de τ sur τ = 0 est de 0,0005, c'est-à-dire rien, et le simulateur perd contre
Harville/Stern sur les deux fenêtres. **Les expositions aux scénarios que j'ai
postulées — le poids face au terrain, l'inexpérience face au trafic — ne portent pas
assez de signal pour battre une formule fermée.** Je ne présente donc pas le simulateur
comme une amélioration du top 3.

**Ce que le simulateur apporte malgré tout, et que Harville ne donne pas :** le top 5,
les probabilités de combinaisons calculées sur les arrivées effectivement tirées, le
regroupement des non-terminaisons via `cf`, et une erreur Monte-Carlo chiffrée.
**Règle de production : Harville/Stern pour le top 3, simulateur pour le reste.**

## 6. Précision numérique et incertitudes, séparées

Exemple exécuté, `reports/exemple_prevision_scellee.json` (R1C3 Auteuil, 26/09/2026,
16 partants, prévision produite avant le départ) :

- **40 000 tirages** exécutés, atteints par doublement depuis 10 000 jusqu'au seuil
  pré-enregistré de 0,20 point d'erreur Monte-Carlo. Erreur maximale atteinte : **0,194 pt**.
- **Erreur Monte-Carlo** sur le favori : ±0,19 pt.
- **Incertitude de modèle** sur le même cheval, par 20 ré-estimations bootstrap au niveau
  course : **[17,3 % ; 21,6 %]** autour de 18,5 %. Soit une bande **dix fois plus large**
  que l'erreur numérique. Les deux sont reportées séparément dans chaque sortie.
- Combinaison jamais tirée : reportée comme **< 0,0025 %**, jamais comme impossible.

## 7. Traçabilité

Chaque prévision scelle : horodatage UTC de production, identifiant de course, moteur,
version, **empreinte SHA-256 du fichier de paramètres**, graine, nombre de tirages, τ, cf,
**horodatage de l'instantané de cotes**, pénétromètre, et la totalité des probabilités
par partant. Le script **refuse de réécrire** un enregistrement existant.

## 8. Ce qui reste exploratoire, non mesuré

- Le **plat** : aucun moteur, aucun chiffre.
- Les rapports Couplé, Trio, Tiercé, Quarté, Quinté historiques ne sont pas collectés :
  **aucune rentabilité de combiné n'est mesurée**, seulement des probabilités.
- Les expositions aux scénarios sont des hypothèses de structure, pas des coefficients
  estimés. Elles ne touchent pas les marginales (recalage IPF) mais leur forme n'est pas
  validée.
- Le bootstrap de modèle n'utilise que 20 ré-estimations : la bande est indicative.
- La référence de rentabilité « marché » est mal posée (voir §3).
