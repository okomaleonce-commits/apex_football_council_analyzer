# Transplantation dans Apex-TSS — FAITE

> **02/10/2026, 21h50 UTC.** L'utilisateur a autorisé l'écriture. Le travail est poussé
> sur **`okomaleonce-commits/Apex-TSS`, branche `claude/apex-turf-worm-mi`**, basée sur
> `3fa33dd` (dernier commit de la branche de vos deux sessions). Zéro collision de nom.
>
> Une **branche dédiée** et non `claude/agents-protocole-apex-gsq9k6` : deux sessions
> commitent sur celle-là (`APEX TSS — WORM SCANNER 24H`, `APEX Market Intelligence
> Swarm`), et pousser là serait entré en course avec elles. La branche se fusionne
> proprement puisqu'elle part de leur pointe.
>
> Trois ajustements faits **pendant** la transplantation, pour coller à l'état réel du
> dépôt plutôt qu'à celui que j'avais lu trois heures plus tôt :
>
> 1. **Pont aligné sur trois axes.** Leur pont football avait gagné `BLOWOUT_WATCH` en
>    miroir d'`UPSET_WATCH` (commit `3fa33dd`, 21h15). Le pont turf avait un seul axe ; il
>    en a maintenant trois — `OUTSIDER_WATCH` et `FAVORI_WATCH` (miroirs exacts) plus
>    `NON_PARTANT_WATCH`, propre au turf.
> 2. **Email ajouté aux deux cellules.** Leur `CLAUDE.md` porte une règle absolue : « un
>    passage sans email envoyé est INCOMPLET ». Mes cellules n'avaient pas d'email, elles
>    étaient donc non conformes. `scan` construit désormais le digest en fin de passage et
>    `finalize` toujours ; aucun des deux n'envoie, l'envoi passe par le connecteur Gmail.
> 3. **Défaut du registre corrigé.** `scan --date 03102026` écrivait dans le registre du
>    jour du scan et non du programme scanné : `report --date 2026-10-03` ne trouvait rien
>    et le registre se mélangeait.
>
> `CLAUDE.md` et `.gitignore` d'`Apex-TSS` sont à jour, selon leurs conventions
> (`data/turf_worm/` et `reports/turf_worm/` ignorés en entier, `runs_turf_mi/*` avec son
> `.gitkeep`, comme `data/worm/` et `runs_mi/*`).
>
> Ce qui suit est la note d'origine, conservée pour l'inventaire des fichiers.

---

## Pourquoi ce fichier existe

Ces deux cellules appartiennent à **`okomaleonce-commits/Apex-TSS`**, branche
`claude/agents-protocole-apex-gsq9k6` — c'est là que vivent `apex-worm-scanner`,
`apex-market-intel-team`, `apex-turf-team` et les outils `tools/apex_*.py`.

Elles ont d'abord été écrites ici parce que l'écriture sur `Apex-TSS` était refusée. Elle
a ensuite été autorisée, et le transfert est fait. Les fichiers restent présents ici à
l'identique : les chemins sont ceux d'`Apex-TSS`, donc la copie était directe.

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
