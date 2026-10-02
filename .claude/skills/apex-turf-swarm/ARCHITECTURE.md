# APEX-TURF SWARM — architecture

## Origine

Construit le 02/10/2026, sur demande de reproduire pour les courses de chevaux l'équipe
d'agents décrite comme « APEX WORM » et « APEX MI SWARM ».

**Ces deux noms n'existent nulle part dans cet environnement.** Recherche faite sur le
dépôt entier et sur les 60 skills synchronisés : zéro occurrence. Ce qui existe est la
chaîne football `apex-s0-orchestrator` → S1…S8 → conseil des 5 → pre-flight gate.

Le swarm turf est donc construit sur **l'architecture APEX réellement présente**, avec les
deux noms demandés rattachés aux deux fonctions qu'ils désignent :

| Nom demandé | Interprétation retenue | Où |
|---|---|---|
| **WORM** | Write Once, Read Many — registre scellé en écriture unique | `scripts/worm.py`, agent `turf-t9-worm` |
| **MI SWARM** | l'essaim d'agents, dont l'étage Market Intelligence | `.claude/agents/turf-t*.md`, agent `turf-t6-market` |

Si ces noms recouvrent autre chose dans un autre environnement, le dire : la structure
ci-dessous est adaptable, la couche WORM et les gates de discipline ne le sont pas.

## Correspondance avec la chaîne football

| Football | Turf | Changement |
|---|---|---|
| `apex-scraper-data-harvesting` + S1 | `turf-t1-data` | fusionnés : une seule source, l'API PMU |
| routage de ligue dans S4 | `turf-t2-router` | **promu en étage à part et durci** : pas de repli générique |
| S2 contexte et motivation | — | **supprimé** : pas d'équivalent mesurable (pas de « dead rubber » hippique mesuré) |
| S3 matchup tactique | `turf-t3-form` | remplacé par le longitudinal + contrôle de fuite |
| S4 pricing statistique | `turf-t4-pricing` | logit conditionnel à la place de Dixon-Coles |
| S5 contrôle de volatilité | `turf-t5-sim` | remplacé par la simulation Monte-Carlo de l'arrivée complète |
| S6 intelligence de marché | `turf-t6-market` | adapté au **pari mutuel** : pas de comparaison entre opérateurs |
| S7 décision et mise | `turf-t7-decision` | Kelly remplacé par mise plate |
| S8 conseil des 5 | `turf-t8-council` | 5 examinateurs refaits pour le turf |
| `apex-preflight-gate` + journal | `turf-t9-worm` | **le journal éditable devient un registre chaîné** |

## Les quatre écarts qui ne sont pas cosmétiques

**1. Pas de repli générique.** S0 route vers un moteur générique avec DCS −5 et Kelly ×0,70
quand la ligue n'est pas couverte. Interdit ici : les paramètres turf s'inversent entre
disciplines (`cf` 0,0 en trot contre 0,4 en obstacle ; la règle du top 3 change de camp).
Un moteur hors discipline ne donne pas un résultat moins précis, il en donne un de signe
faux. **Le plat sort en ABORT.**

**2. Le pari est l'exception.** Le PMU est en pari mutuel : la cote est la même partout,
elle bouge jusqu'au départ, et l'espérance au prix du marché vaut 1/overround < 1. Les deux
gates de pari sont fermées par le backtest. La sortie normale est un INDICATIF calibré.

**3. Le registre s'impose par le code.** `worm.py` détecte la falsification d'un
enregistrement ancien, la suppression d'une ligne, l'antidatage, et refuse une prévision
pour une course dont le résultat est déjà scellé. 18 tests dans `scripts/test_worm.py`.
C'est le seul composant du swarm qu'on ne peut pas contourner en lisant mal une consigne.

**4. Parallélisme réel.** S0 est séquentiel et le reconnaît comme une limite. Ici
`turf-t5-sim` ∥ `turf-t6-market`, et les 5 examinateurs de T8 ∥, parce que le graphe de
dépendances le permet.

## Le registre

```
.claude/skills/apex-turf-swarm/registre/turf.jsonl
```

Une ligne par enregistrement, JSONL append-only :

```json
{"seq":0,"ts":"...Z","prev_hash":"<hash de seq-1>","payload":{...},"hash":"sha256(seq|ts|prev_hash|payload canonique)"}
```

Cinq `kind` : `prevision`, `resultat`, `correction`, `audit`, `note`.

```bash
python3 scripts/worm.py verify .claude/skills/apex-turf-swarm/registre/turf.jsonl
python3 scripts/worm.py course <registre> 26092026-R4C6
python3 scripts/worm.py seal   <registre> prevision.json prevision
python3 scripts/test_worm.py
```

### Ce que la chaîne prouve, et ce qu'elle ne prouve pas

Elle prouve qu'**aucun enregistrement n'a bougé depuis son écriture**. Elle ne prouve pas
qu'un enregistrement a été écrit avant un événement extérieur : l'horodatage vient de
l'horloge locale.

Les deux premiers enregistrements du registre sont donc marqués `importe: true`. La
prévision R4C6 a bien été produite 15 minutes avant le départ, mais scellée hors de ce
registre, qui n'existait pas encore — son antériorité repose sur l'horodatage du commit
git, pas sur le chaînage. **Toute prévision suivante est scellée en direct**, et son
antériorité est alors garantie par la chaîne.

Cette distinction est écrite dans le registre lui-même (enregistrement 0). Un registre qui
mélangerait importations et scellements en direct sans le dire serait pire qu'absent : il
donnerait une apparence de preuve.

## État du registre à l'ouverture

| seq | kind | course | contenu |
|---|---|---|---|
| 0 | `note` | 26092026-R4C6 | ouverture, avertissement d'importation, SHA-256 des deux fichiers, commit git |
| 1 | `prevision` | 26092026-R4C6 | importée — 14 partants, DCS 82, NO_BET par G-TROT-4 |
| 2 | `resultat` | 26092026-R4C6 | arrivée 5-8-6-10-15, 5 non-finissants, 1 non-partant |
| 3 | `audit` | 26092026-R4C6 | AUC porte de faute 0,822 — 3 hypothèses à tester |

## Limites, non corrigées

1. Aucun moteur de plat — et le plat est la majorité du programme français.
2. Pas de bande d'incertitude de modèle en trot (`beta_boot_trot.pkl` absent).
3. Aucun rapport historique Couplé/Trio/Tiercé collecté : combinés en INDICATIF seulement.
4. La référence « marché » du backtest est mal spécifiée (EV = 1/overround < 1).
5. Les expositions de scénario sont des hypothèses structurelles, non estimées.
6. Bootstrap de modèle à 20 refits, en obstacle seulement.
7. **L'orchestration reste déclarative.** Seul le registre s'impose par le code.
