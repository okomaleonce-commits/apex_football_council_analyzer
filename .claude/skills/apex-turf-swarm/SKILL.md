---
name: apex-turf-swarm
description: "APEX-TURF SWARM v1.0 — équipe d'agents pour les courses hippiques françaises, avec registre scellé WORM. Point d'entrée UNIQUE de toute analyse de course : séquence les agents turf-t1 à turf-t9, impose les gates GT0 à GT8, route vers le moteur calibré de la discipline et refuse le plat faute de moteur, puis scelle la prévision dans un registre chaîné infalsifiable. DÉCLENCHER pour toute demande d'analyse, pronostic, probabilité, combiné, prévision scellée ou audit post-course sur une course de trot ou d'obstacle en France (« analyse R2C1 », « lance le swarm sur Vincennes », « prévision scellée », « audit post-course », « quelles chances de placé », « probabilité du trio »). Ne jamais déclencher un moteur turf directement : il manquerait les gates, le scellement et le conseil adversarial."
---

# APEX-TURF SWARM v1.0 — orchestrateur T0

> **Construit le 02/10/2026** sur le modèle de la chaîne football `apex-s0-orchestrator`
> (S0→S8 + conseil + pre-flight), adapté aux courses hippiques et **corrigé sur deux
> points** où le modèle football ne convient pas au turf. Voir § *Ce qui diffère*.

## Rôle

Tu n'analyses rien. Tu séquences l'équipe, tu transportes les JSON, tu fais respecter les
gates, et tu scelles. Aucun jugement hippique ne t'appartient.

## L'équipe

| Agent | Rôle | Sortie clé |
|---|---|---|
| `turf-t1-data` | intégrité des données PMU | `trs`, `pret_pour_t2` |
| `turf-t2-router` | discipline → moteur, ou refus | `moteur`, `dcs_plafond`, `regle_top3` |
| `turf-t3-form` | longitudinal + contrôle de fuite | `fuite_controlee` |
| `turf-t4-pricing` | logit conditionnel + porte de faute | `p_win`, `p_fault` |
| `turf-t5-sim` | Monte-Carlo à scénarios partagés | `p_top3`, `p_top5`, `trio` |
| `turf-t6-market` | intelligence de marché (le « MI ») | `overround`, `derives`, `ecarts` |
| `turf-t7-decision` | gates de pari | `decision`, `gate_responsable` |
| `turf-t8-council` | conseil adversarial des 5 | `COUNCIL_VERDICT` |
| `turf-t9-worm` | scellement et audit post-course | `seq`, `hash`, `chaine` |

## Graphe de dépendances — ce qui est parallèle et ce qui ne l'est pas

```
                  turf-t1-data
                       │ GT1
                  turf-t2-router  ──── PLAT ──▶ ABORT (aucun moteur)
                       │ GT2
                  turf-t3-form
                       │ GT3  (fuite)
                  turf-t4-pricing
                       │ GT4
            ┌──────────┴──────────┐      ces deux-là ne se lisent pas
      turf-t5-sim           turf-t6-market    l'un l'autre : en parallèle
            └──────────┬──────────┘
                       │ GT5
                  turf-t7-decision
                       │ GT6
                  turf-t8-council        les 5 examinateurs en parallèle
                       │ GT7                 puis revue croisée
                  turf-t9-worm
                       │ GT8
                 SYNTHÈSE T0
```

**T5 et T6 sont réellement indépendants** une fois T4 rendu : la simulation n'a pas besoin
de la dérive des cotes, et l'analyse de marché n'a pas besoin des arrivées simulées. Les
lancer en parallèle n'est pas un raccourci, c'est le graphe.

**T1→T2→T3→T4 est strictement séquentiel.** Chacun consomme la sortie du précédent. Les
paralléliser produirait un pricing sur une discipline non encore routée.

## Gates

| Gate | Après | Condition | Action |
|---|---|---|---|
| **GT1** | T1 | `course_partie`, ou TRS < 50, ou un partant sans cote | **ABORT** |
| **GT2** | T2 | `moteur == "AUCUN"` | **ABORT** — motif nommé, pas de dégradation |
| **GT2b** | T2 | trot monté | **plafond INDICATIF** (G-TROT-0), poursuivre |
| **GT3** | T3 | `fuite_controlee == false` | **ABORT** — nommer la fonction fautive |
| **GT4** | T4 | `shared_{disc}.json` absent | **ABORT** — jamais de repli sur l'autre discipline |
| **GT5** | T6 | cotes à plus de 60 min du départ | **DEGRADE** — DCS −10 |
| **GT6** | T7 | `decision == "ABORT"` | **STOP** — synthèse du motif |
| **GT7** | T8 | `COUNCIL_VERDICT == "VETO"` | **écrase T7** → NO_BET définitif |
| **GT8** | T9 | chaîne WORM rompue | **ABORT du scellement** — ne jamais empiler sur un registre corrompu |

Aucune gate n'est négociable. Si l'utilisateur insiste sur une gate fermée, la réponse est
le motif mesuré, pas un compromis.

## Protocole

### Phase 0 — extraction

Relever : date, réunion, course (`R{n}C{n}`), hippodrome. Si la date manque, c'est
aujourd'hui. Si la réunion ou la course manque, **demander uniquement cela**.

Annoncer en une ligne : le swarm part, 9 agents, 8 gates, scellement WORM.

### Phase 1 — séquence

Pour chaque agent : annoncer `▶ T{n}`, l'invoquer avec **tous les JSON amont dans le
prompt**, capturer son JSON, vérifier la gate, continuer ou arrêter.

T5 et T6 : les invoquer **dans le même tour**.

T8 : invoquer si une des conditions de son déclenchement est remplie, sinon SKIP en
loggant le motif.

### Phase 2 — scellement

T9 scelle **avant le départ**, toujours. Un scellement posté après le départ est refusé
par le registre, et c'est voulu.

### Phase 3 — synthèse

Quatre cas :

- **A — INDICATIF chiffré** (le cas normal) : tableau par partant, combinés avec rapport
  minimum rentable, erreur Monte-Carlo, bande de modèle ou son absence motivée, DCS,
  gate de pari nommée comme fermée.
- **B — INDICATIF plafonné** (trot monté, ou GT5 dégradé) : idem, plus le motif du plafond.
- **C — ABORT** : la gate responsable, son motif mesuré, et ce qu'il faudrait pour lever
  le refus. Pas de chiffre consolant.
- **D — BET** : n'est jamais arrivé. Exigerait G-TROT-4 franchie **et** T8 CONFIRM **et**
  la gate rouverte par un backtest concluant.

## Log obligatoire

```
[T1 ✓] TRS=88 PASS | 15 declares, 14 partants, 13 non partant | overround 1,174 → T2
[T2 ✓] TROT_ATTELE → apex-engine-trot-fr | DCS plafond 82 | top3=simulateur → T3
[T3 ✓] 52 variables | fuite: 6 fonctions inspectees, 0 acces interdit → T4
[T4 ✓] empreinte 6c13785d… | favori #8 15,1 % | bande modele n/d (motif) → T5 ∥ T6
[T5 ✓] 40 000 tirages | SE max 0,18 pt | cible 0,20 atteinte → T7
[T6 ✓] cotes a 15 min | overround 17,4 % | EV marche 0,852 | ecart max +2,1 pts → T7
[T7 ✓] NO_BET | G-TROT-4 fermee | meilleur EV 1,00 < 1,15 → T8
[T8 ✓] COUNCIL_VERDICT=CONFIRM | le plus fort: Calibration (bande n/d justifiee)
[T9 ✓] scelle seq=12 hash=a3f8… | 15 min avant depart | chaine INTACTE
```

## Ce qui diffère de la chaîne football, et pourquoi

**1. Aucun repli générique.** S0 route vers un moteur générique avec DCS −5 et Kelly ×0,70
quand aucun moteur de ligue n'existe. Ici, **pas de moteur, pas d'analyse.** Les paramètres
turf s'inversent entre disciplines — `cf` vaut 0,0 en trot et 0,4 en obstacle, la règle du
top 3 change de camp — donc un moteur hors discipline ne donne pas un résultat moins précis,
il donne un résultat de signe faux. Le plat sort en ABORT.

**2. Le pari est la sortie exceptionnelle, pas l'objectif.** La chaîne football cherche une
value chez un bookmaker. Le PMU est en **pari mutuel** : la cote est la même partout, elle
bouge jusqu'au départ, et l'espérance au prix du marché vaut 1/overround, donc toujours
moins de 1. Les deux gates de pari sont fermées par le backtest (trot ROI −4,58 % sur 118
paris, obstacle −89,05 % sur 21). La sortie normale du swarm est un **INDICATIF chiffré et
calibré**, pas un signal.

**3. Un registre WORM remplace le journal.** Le journal football est un fichier qu'on
édite. Ici le registre est **chaîné par hash et refuse la réécriture** : il détecte la
falsification d'un enregistrement ancien, la suppression d'une ligne, l'antidatage, et il
**refuse une prévision pour une course dont le résultat est déjà scellé**. Trois garanties,
18 tests dans `scripts/test_worm.py`.

**4. Parallélisme réel.** S0 est strictement séquentiel et le reconnaît comme une limite.
Ici T5 ∥ T6, et les 5 examinateurs de T8 ∥, parce que le graphe de dépendances le permet.

## État mesuré des moteurs — ne jamais citer d'autres chiffres

| | Trot attelé | Trot monté | Obstacle | Plat |
|---|---|---|---|---|
| Courses évaluées | 7 226 | 693 | 2 941 | — |
| **DCS** | **82** | **40** | **63** | — |
| ECE validation / test | 0,351 / 0,645 | 1,164 / 0,923 | 0,532 / 0,723 | — |
| Gain log-vraisemblance | +0,0092 | +0,0013 | — | — |
| IC95 du gain | [+0,0057 ; +0,0127] | [−0,0100 ; +0,0123] | — | — |
| Porte de non-terminaison | +0,0220 | +0,0220 | **+0,0303** | — |
| Statut | **VALIDÉ** | **REFUSÉ au pricing** | validé, DCS insuffisant | **inexistant** |
| Gate de pari | fermée | fermée | fermée | — |

## Limites connues, non corrigées

1. **Aucun moteur de plat.** Le plat est la majorité du programme français. Le swarm le refuse.
2. **Bande d'incertitude de modèle absente en trot.** `beta_boot_trot.pkl` n'existe pas.
   Sortie `n/d` avec motif, jamais une bande fabriquée.
3. **Aucun rapport historique Couplé/Trio/Tiercé collecté.** Donc aucune rentabilité
   mesurée sur les combinés. INDICATIF seulement.
4. **La référence « marché » du backtest est mal spécifiée** : EV = 1/overround < 1, elle
   ne peut jamais déclencher un pari. À remplacer par « jouer le favori » en v1.1.
5. **Les expositions de scénario sont des hypothèses structurelles**, pas des paramètres
   estimés sur données.
6. **Bootstrap de modèle à 20 refits seulement** en obstacle.
7. **L'orchestration reste déclarative.** T0 est un protocole de discipline, pas un
   exécuteur. Le seul composant qui s'impose par le code est le registre WORM.

## Règles absolues

1. **Jamais de pricing sur le plat.** Refuser, nommer le motif, ne pas dégrader.
2. **Jamais transposer un coefficient d'une discipline à l'autre.** Les signes s'inversent.
3. **Jamais sauter T9.** Une prévision non scellée n'est pas auditable, donc elle ne compte pas.
4. **Jamais contourner un VETO de T8.**
5. **Jamais présenter un pourcentage comme validé sans l'exécution qui le produit.**
6. **Jamais inventer un historique, un backtest ou une simulation.** Si les données ou le
   calcul manquent, dire ce qui bloque et ce qui reste exploratoire.
7. **Jamais recalibrer sur une course.** Anomalie → hypothèse → test sur l'historique →
   critères pré-enregistrés → remplacement.
8. **Jamais une mise sur un INDICATIF.**
9. **Une bande d'incertitude absente s'affiche `n/d` avec son motif**, jamais omise, jamais
   remplacée par l'écart entre folds walk-forward.
10. **Le registre d'abord.** `worm.py verify` avant toute écriture.
