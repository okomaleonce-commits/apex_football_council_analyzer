# Le Framework APEX

### Analyser un match de football comme un quant, pas comme un parieur

**Édition 1.0 — Guide de méthode**

---

> ⚠️ **À lire avant tout.** Ce guide est un produit **éducatif** sur une méthode
> d'analyse statistique. Ce n'est **pas** un conseil financier ni une promesse de
> gain. Les paris sportifs comportent un risque réel de perte d'argent. Aucune
> méthode ne « garantit » de gagner. Réservé aux personnes majeures (+18/+21 selon
> ton pays). Si le jeu devient un problème : demande de l'aide (en France,
> 09 74 75 13 13 — Joueurs Info Service).

---

## Pourquoi ce guide existe

La plupart des gens qui parient font l'inverse de ce qu'il faut :

- ils **prédisent un résultat**, alors qu'il faut **estimer une probabilité** ;
- ils parient parce qu'ils sont **confiants**, alors qu'il faut parier parce qu'il
  y a de la **valeur** ;
- ils parient **tout le temps**, alors que le pari correct est le plus souvent
  *ne rien faire*.

Le framework APEX inverse ces trois réflexes. Ce n'est pas un système pour « gagner
à tous les coups » — ça n'existe pas. C'est une **discipline** pour ne miser que
lorsque le marché se trompe de façon mesurable, et pour s'abstenir le reste du
temps. La majorité de la rentabilité, sur le long terme, vient des paris que tu
**ne fais pas**.

Ce guide t'apprend les 6 étapes du moteur, avec les formules exactes, pour que tu
puisses les appliquer à la main ou dans un tableur — même sans logiciel.

---

## Vue d'ensemble : le pipeline en 6 étapes

```
1. QUALITÉ DES DONNÉES   → ai-je le droit d'avoir une opinion ?
2. MODÈLE POISSON        → quelle est la vraie probabilité de chaque issue ?
3. PRICING DES MARCHÉS   → traduire les probas en cotes justes (fair odds)
4. DÉTECTION DE VALUE    → le marché paie-t-il plus que le juste prix ?
5. CONSEIL MULTI-AGENTS  → qu'est-ce que j'ai raté ?
6. VERDICT + MISE        → BET / NO BET / WAIT, et combien
```

Chaque étape peut **tuer** le pari. Un pari ne survit que s'il passe les six.

---

## Étape 1 — Le score de qualité des données

**Règle d'or : pas de données fiables → pas d'opinion → NO BET.**

Avant toute analyse, on note la qualité des informations disponibles sur 1.0.
On part d'une base basse et on ajoute des points :

| Condition remplie | Points |
|---|---|
| Base de départ | +0.15 |
| Match exact confirmé par les sources | +0.20 |
| Identifiant de match (fixture) trouvé | +0.10 |
| Statistiques des deux équipes disponibles | +0.20 |
| Au moins une cote de marché exploitable | +0.20 |
| Par source fiable active (max +0.15) | +0.05 chacune |

Score plafonné à 1.0. Verdict qualité :

- **≥ 0.78 → GOOD** : analyse pleine autorisée.
- **0.60 – 0.77 → MEDIUM** : analyse possible, prudence.
- **0.40 – 0.59 → WEAK** : au mieux surveillance, aucune mise forte.
- **< 0.40 → UNUSABLE** : NO BET, point.

**Seuil de confiance minimum : 0.60.** En dessous, le moteur refuse toute
recommandation forte et renvoie `WAIT_DATA`. C'est volontaire : la plupart des
pertes viennent de paris pris sur des données trop maigres.

---

## Étape 2 — Le modèle de Poisson

Le football se modélise bien par une loi de Poisson : on estime le nombre moyen de
buts attendus de chaque équipe (les « lambdas »), puis on en déduit la probabilité
de chaque score exact.

### 2.1 Estimer les buts attendus (λ)

```
λ_domicile = moyenne( buts marqués domicile , buts encaissés extérieur ) × 1.08
λ_extérieur = moyenne( buts marqués extérieur , buts encaissés domicile ) × 0.96
```

Le `× 1.08` / `× 0.96` encode **l'avantage du terrain**. On borne ensuite les
valeurs (domicile entre 0.25 et 3.6 ; extérieur entre 0.20 et 3.3) pour éviter les
aberrations.

**Ajustement blessures** : si une équipe a 3 blessés ou plus parmi les titulaires,
on multiplie son λ par 0.94 (−6 %). Simple, mais ça capture l'essentiel.

> Valeurs par défaut quand une stat manque : domicile 1.45 marqués / 1.15 encaissés,
> extérieur 1.20 marqués / 1.35 encaissés. À n'utiliser qu'en dépannage — une stat
> manquante fait baisser le score de qualité (étape 1).

### 2.2 De λ aux probabilités

Probabilité de marquer *k* buts avec une moyenne λ :

```
P(k buts) = (λ^k × e^(−λ)) / k!
```

On construit une matrice des scores de 0-0 à 7-7. La proba d'un score exact (h-a)
est `P(h | λ_dom) × P(a | λ_ext)`. En sommant les bonnes cases :

- **1X2** : victoire dom (h>a), nul (h=a), victoire ext (h<a).
- **Double chance** : 1X, 12, X2.
- **BTTS** (les deux marquent) : cases où h>0 **et** a>0.
- **Over/Under 2.5** : Over = cases où h+a ≥ 3.

Tu obtiens une probabilité propre pour chaque marché. C'est ta **vérité modèle**.

---

## Étape 3 — Le pricing : de la proba à la cote juste

La **cote juste** (fair odds) est simplement l'inverse de la probabilité :

```
fair_odds = 1 / probabilité
```

Exemple : si le modèle dit 55 % de chances → cote juste = 1 / 0.55 = **1.82**.

C'est le prix auquel le pari est neutre (ni gagnant ni perdant en moyenne). Tout
l'enjeu est de comparer ce prix au prix du marché.

---

## Étape 4 — La détection de value (le cœur du système)

Le marché publie une cote. On en déduit sa **probabilité implicite** :

```
proba_implicite = 1 / cote_marché
```

On compare alors ta proba modèle à celle du marché :

```
EDGE = proba_modèle − proba_implicite
ROI espéré = (proba_modèle × cote_marché) − 1
```

- **EDGE > 0** → le marché sous-estime l'issue : il y a potentiellement de la value.
- **EDGE ≤ 0** → le marché paie moins que le juste prix : NO VALUE, on passe.

**Seuil de validation : EDGE ≥ seuil minimum (par défaut ≈ 0.03 à 0.05) ET score
qualité ≥ 0.60.** Les deux conditions, pas une seule.

> ⚡ **Erreur n°1 des débutants** : confondre *probabilité élevée* et *value*. Une
> issue à 80 % n'est PAS un bon pari si le marché la paie 1.20 (proba implicite
> 83 %). Le modèle dit moins que le marché → edge négatif → NO BET. La value, pas
> la confiance.

**Best price** : s'il existe plusieurs bookmakers, on prend toujours la **cote la
plus haute** disponible pour la sélection. Sur le long terme, chercher le meilleur
prix est l'un des plus gros leviers de rentabilité.

---

## Étape 5 — Le conseil multi-agents (LLM Council)

Un seul angle de vue, c'est un angle mort. Avant de valider, on fait passer le
signal devant plusieurs « conseillers », chacun avec un rôle fixe :

- **Contrarian** — cherche les pièges du marché. Règle : *refuser si la cote ne
  dépasse pas la fair odds.*
- **First Principles** — valide la logique statistique. Règle : *ne jamais
  confondre probabilité élevée et value bet.*
- **Expansionist** — cherche des opportunités secondaires (un autre marché mieux
  valorisé sur le même match).
- **Outsider** — vérifie la clarté et les angles morts (données douteuses,
  sur-confiance).
- **Executor** — transforme l'analyse en une action concrète et unique.

Le conseil produit : les points d'accord, les points de friction, les angles morts,
et une recommandation finale. Si les conseillers divergent fortement, c'est un
signal de prudence, pas de pari.

---

## Étape 6 — Le verdict et la mise

Le moteur conclut par un verdict unique :

| Verdict | Signification |
|---|---|
| **BET** | Edge validé + données solides. Pari recommandé. |
| **NO_BET** | Pas de value, ou données inutilisables. Défaut. |
| **WAIT_DATA** | Données insuffisantes (< 0.60). Revenir plus tard. |
| **WAIT_LINEUPS** | Attendre les compositions officielles. |
| **MONITOR_LIVE** | Signal fort mais pas de cote exploitable : surveiller. |

### Dimensionner la mise (staking)

Ne jamais miser « au feeling ». Deux approches saines :

1. **Mise plate** : 1 % de ta bankroll par pari validé. Simple, robuste, faible
   variance. Recommandé pour débuter.
2. **Kelly fractionné** : `fraction_Kelly = edge / (cote − 1)`, puis on ne mise
   qu'une **fraction** (¼ ou ½) de ce résultat pour réduire la variance. Jamais le
   Kelly plein — trop agressif, il ruine sur une mauvaise série.

> 🔒 **Règles de survie non négociables** : jamais plus de 1–2 % par pari ; jamais
> de « martingale » (doubler après une perte) ; jamais parier pour se « refaire » ;
> tenir un journal de tous les paris (date, match, marché, proba modèle, cote,
> edge, mise, résultat). Sans journal, pas d'amélioration possible.

---

## Exemple complet de bout en bout

**Match** : Équipe A (dom) vs Équipe B (ext).

1. **Données** : match confirmé (+0.20), fixture trouvé (+0.10), stats des deux
   équipes (+0.20), cotes présentes (+0.20), 2 sources actives (+0.10), base
   (+0.15) → **0.95 → GOOD.** Autorisé.
2. **Lambdas** : A marque 1.8 / encaisse 1.0 ; B marque 1.1 / encaisse 1.6.
   - λ_A = moy(1.8 , 1.6) × 1.08 = 1.7 × 1.08 ≈ **1.84**
   - λ_B = moy(1.1 , 1.0) × 0.96 = 1.05 × 0.96 ≈ **1.01**
3. **Poisson** → (via la matrice) Over 2.5 ≈ **52 %**, victoire A ≈ 55 %, etc.
4. **Pricing** : fair odds Over 2.5 = 1 / 0.52 = **1.92**.
5. **Value** : le marché paie Over 2.5 à **2.10**.
   - proba implicite = 1 / 2.10 = 47.6 %
   - EDGE = 52 % − 47.6 % = **+4.4 %** ✅ (au-dessus du seuil)
   - ROI espéré = (0.52 × 2.10) − 1 = **+9.2 %**
6. **Conseil** : Contrarian OK (cote 2.10 > fair 1.92), First Principles OK (edge
   réel, pas juste proba haute). **Verdict : BET.**
7. **Mise** : Kelly = 0.044 / (2.10−1) = 0.04 → ¼ Kelly = **1 % de bankroll.**

Si le marché payait Over 2.5 à 1.80 : proba implicite 55.6 % > 52 % → edge négatif
→ **NO BET**, malgré une « bonne intuition ». C'est tout l'intérêt de la méthode.

---

## Les 10 commandements APEX

1. NO BET est le verdict par défaut, pas l'exception.
2. Pas de données fiables (≥ 0.60) → pas de pari.
3. La value (edge > seuil), jamais la confiance.
4. Probabilité élevée ≠ bon pari.
5. Toujours chercher la meilleure cote (best price).
6. Jamais plus de 1–2 % de bankroll par pari.
7. Jamais de martingale, jamais « se refaire ».
8. Tenir un journal de chaque pari, sans exception.
9. Mesurer sur 200+ paris, pas sur une soirée.
10. Le jeu est un divertissement à risque, pas un revenu.

---

## Pour aller plus loin

Ce guide décrit la méthode manuelle. Le logiciel **APEX Football Council Analyzer**
automatise les 6 étapes (récupération des données multi-sources, modèle Poisson,
pricing, détection de value, conseil, verdict). Si tu veux l'outil complet, voir la
page produit.

---

*Framework APEX v1.0 — produit éducatif. Pas un conseil financier. Jouer comporte
des risques : endettement, dépendance, isolement. +18. Joueurs Info Service :
09 74 75 13 13 (France).*
