# Transplanter APEX-TURF-WORM et APEX-TURF-MI dans Apex-TSS

## Pourquoi ce fichier existe

Ces deux cellules appartiennent à **`okomaleonce-commits/Apex-TSS`**, branche
`claude/agents-protocole-apex-gsq9k6` — c'est là que vivent `apex-worm-scanner`,
`apex-market-intel-team`, `apex-turf-team` et les outils `tools/apex_*.py`.

Elles ont été écrites ici parce que **l'écriture sur `Apex-TSS` m'a été refusée** par le
classificateur de permissions de la session (`add_repo access:"push"` → *Permission Grant*
denied). Les chemins sont donc ceux d'`Apex-TSS`, pas ceux de ce dépôt : le transfert est
une copie, sans réécriture.

## Ce qu'il faut copier

```
tools/apex_turf_worm.py
tools/apex_turf_mi.py
tools/params/turf_worm_quantiles.json
.claude/skills/apex-turf-worm-scanner/SKILL.md
.claude/skills/apex-turf-market-intel-team/SKILL.md
.claude/agents/apex-turf-worm-conductor.md
.claude/agents/apex-turf-worm-market.md
.claude/agents/apex-turf-worm-anomaly.md
.claude/agents/apex-turf-worm-live.md
.claude/agents/apex-tmi-conductor.md
.claude/agents/apex-tmi-odds-flow.md
.claude/agents/apex-tmi-declarations.md
.claude/agents/apex-tmi-late-money.md
.claude/agents/apex-tmi-presse.md
.claude/agents/apex-tmi-synthesizer.md
.claude/agents/apex-tbi-cheval.md
.claude/agents/apex-tbi-driver.md
.claude/agents/apex-tbi-ecurie.md
.claude/agents/apex-tbi-engagement.md
.claude/agents/apex-tbi-piste.md
.claude/agents/apex-tbi-narration.md
.claude/agents/apex-tbi-synthesizer.md
.github/workflows/apex-turf-worm.yml
```

Plus, dans `.gitignore` d'`Apex-TSS` :

```
data/turf_worm/snapshots/*.jsonl
data/turf_worm/mi/*.json
runs_turf_mi/*
!runs_turf_mi/.gitkeep
reports/turf_worm/*
!reports/turf_worm/.gitkeep
```

## Trois points de vigilance au moment de la copie

**1. Aucune collision de nom.** Les 17 agents sont préfixés `apex-turf-worm-*`,
`apex-tmi-*`, `apex-tbi-*` ; aucun n'existe dans `Apex-TSS`. Les deux skills non plus.
Les deux outils non plus. Rien n'est écrasé.

**2. `ROOT` est relatif au fichier.** Les deux outils calculent `ROOT` depuis
`os.path.dirname(os.path.dirname(__file__))`, donc depuis `tools/`. Déposés dans
`Apex-TSS/tools/`, ils écrivent dans `Apex-TSS/data/` et `Apex-TSS/reports/` sans aucune
modification.

**3. Stdlib uniquement.** Aucune ligne à ajouter à `requirements.txt`.

## Ce qui rend ces cellules dépendantes l'une de l'autre

`apex_turf_mi.py oddsflow` **lit les snapshots du WORM** — il ne collecte pas de cote
lui-même. Sans deux passages de `apex_turf_worm.py scan`, il sort `UNAVAILABLE` avec son
motif. L'ordre est donc : WORM d'abord, deux fois, MI ensuite.

## Articulation avec ce qui existe déjà dans Apex-TSS

| Cellule | Rôle | Statut |
|---|---|---|
| `apex-turf-team` (13 agents) | cellule **statistique** — price la course | existait déjà |
| `apex-turf-worm-scanner` (4 agents) | scanner d'**anomalies** horaire | **nouveau** |
| `apex-turf-market-intel-team` (13 agents) | **bruit** de marché et comportemental | **nouveau** |

Les trois sont séparées et ne se mélangent pas. Seule `apex-turf-team` price. Les deux
nouvelles portent `bet_authority = false` et ne peuvent, au mieux, qu'atteindre
`CANDIDATE` : la brique DATA qui mènerait à `CONFIRMED` n'est pas la leur.

## Vérification après copie

```bash
python3 tools/apex_turf_worm.py window
python3 tools/apex_turf_worm.py scan --max-courses 5
python3 tools/apex_turf_worm.py scan --max-courses 5     # un 2e passage, pour le COMPARE
python3 tools/apex_turf_mi.py window
python3 tools/apex_turf_mi.py init --within 180
python3 tools/apex_turf_mi.py oddsflow --course-dir runs_turf_mi/<run>/<course_id>
python3 tools/apex_turf_mi.py worm-hook --within 30
```

Le premier passage ne doit produire **aucun** signal (`PREMIER_PASSAGE` partout) : sans
deuxième relevé il n'y a pas de trajectoire. C'est le comportement correct.

## Si vous préférez que je pousse directement

Deux voies :

1. Autoriser l'écriture sur `Apex-TSS` pour cette session, et je pousse sur une branche
   dédiée — **pas** sur `claude/agents-protocole-apex-gsq9k6`, où deux de vos sessions
   commitent en ce moment (`APEX TSS — WORM SCANNER 24H` était en cours d'exécution et
   `APEX Market Intelligence Swarm` en revue au moment de l'écriture). Pousser là
   entrerait en course avec elles.
2. Me demander de transmettre le travail à l'une de ces deux sessions, qui a déjà le dépôt
   en écriture.
