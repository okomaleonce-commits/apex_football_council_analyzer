# Matchs du 21/09/2026 — pronostic en aveugle et vérification

Le calendrier du 21/09 ne comptait que **2 matchs**, joués tous deux dans la nuit
(00h30 et 01h00 heure de Paris). Le protocole a donc été exécuté en aveugle : les
modèles sont construits sur les données arrêtées au **16/09** (Brésil, 267 matchs) et
au **14/09** (MLS, 372 matchs) — aucun des deux matchs testés n'y figure.

## 1. Athletico-PR – Bahia · Brasileirão J28 · 00h30

| | Athletico-PR (dom, 13 m) | Bahia (ext, 13 m) |
|---|---|---|
| Marque | 1.77 | 1.54 |
| Encaisse | 0.77 | 1.46 |

λ **1.70 – 1.03** (total 2.73) · Modèle **54.6 % / 21.2 % / 24.2 %** · Marché 40.3 / 29.0 / 30.7

**Score anticipé : 1-0** (12.4 %) — top 5 : 1-0, 1-1, 2-1, 2-0, 0-1
**Pari : Athletico (1) @ 2.48**, edge +35.4 %

La lecture : Athletico n'encaisse que **0.77 but par match à domicile**, meilleure défense
à domicile du lot, pendant que Bahia en prend 1.46 à l'extérieur. Le marché les séparait
de 40 % à 31 % ; le modèle voyait 55/24. Confrontation directe pour le G-4.

→ **Résultat réel : 2-1. Pari GAGNÉ, +1.48 u.** Score exact raté (1-0 annoncé).

## 2. Inter Miami – San Diego FC · MLS · 01h00

| | Inter Miami (dom, 12 m) | San Diego (ext, 11 m) |
|---|---|---|
| Marque | 2.75 | 0.91 |
| Encaisse | 2.00 | 1.64 |

λ **2.47 – 1.32** (total 3.79) · Modèle **62.5 % / 18.4 % / 19.2 %** · Marché 70.5 / 16.0 / 13.5

**Score anticipé : 2-1** (9.1 %) — top 5 : 2-1, 3-1, 1-1, 2-0, 2-2
**Pari : San Diego (2) @ 7.40**, edge +41.9 %

La lecture : Miami marque énormément à domicile (2.75) mais **encaisse 2.00 par match** —
défense la plus poreuse parmi les prétendants. Le marché la donnait à 1.42, le modèle la
jugeait surcotée. Diagnostic juste sur le fond, mauvais choix de camp.

→ **Résultat réel : 2-2** (doublé de Dreyer, 101e but de Messi). **Pari PERDU, −1.00 u.**
Le nul, flaggé à +14.7 % d'edge, aurait rapporté +5.25 u à la cote 6.25.

## Bilan

| Élément | Résultat |
|---|---|
| Paris émis | 2 |
| Gagnés | 1 |
| **P&L** | **+0.48 u** |
| Issues correctes (favori modèle) | 1/2 |
| Scores exacts | 0/2 |
| **Over/Under 2.5** | **2/2** ✅ |

## La réserve qui compte

**Les deux signaux dépassaient 15 % d'edge — donc tous deux flaggés `SUSPICIOUS_EDGE` par
la règle S6.** Appliqué strictement, le protocole aurait émis **NO BET sur les deux** et le
P&L serait de 0.

L'audit du matin même a montré que les gros edges sont les moins fiables (ROI −10.1 % au-delà
de 15 % sur 87 paris européens). Ces deux matchs ne contredisent pas ce constat : ils le
sous-échantillonnent. **n = 2 ne prouve rien**, ni dans un sens ni dans l'autre.

## Une convergence notable

| Ligue | HOME_ADV mesuré |
|---|---|
| **MLS** | **1.329** (372 matchs) |
| **Brasileirão** | **1.319** (267 matchs) |
| Ligue 1 | 1.020 |
| Premier League | 1.073 |

Les deux ligues des Amériques écrasent les européennes sur l'avantage du terrain — cohérent
avec les distances continentales. Le moteur `apex-engine-brasileirao` annonce 1.22 ; la
mesure 2026 donne **1.319**, soit **+0.10 au-dessus du paramètre**. Signalé, pas corrigé :
267 matchs sur une ligue n'autorisent qu'un recalibrage FAIBLE, et la règle du backtester
impose une validation hors-échantillon avant tout déploiement.
