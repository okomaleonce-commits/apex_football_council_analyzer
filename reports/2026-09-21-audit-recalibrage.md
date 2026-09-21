# Audit post-match, recalibrage et application — 21 septembre 2026

> Skills : `football-league-backtester` v1.0 (phases 0→5), `apex-s4-statistical-pricing`.
> Sources : football-data.co.uk (résultats + cotes de clôture + xG), ESPN, Wikipédia.

## Périmètre — à lire en premier

**Il n'existe aucune analyse de la semaine dernière à auditer.** Le seul rapport au
dossier est `2026-08-30-analyse-jour.md`, vieux de trois semaines. C'est donc lui qui est
audité. L'audit porte sur **6 décisions** — un échantillon qui, seul, n'autorise
**aucun** recalibrage (règle backtester : < 10 matchs = ABORT, < 50 = analyse seule).

Pour obtenir le droit de recalibrer, un second échantillon a été constitué :
**202 matchs** de la saison 2026/27 en cours, dont **116 exploitables hors-échantillon**
(EPL + Serie A + Ligue 1, priors = tables finales 2025/26 uniquement, aucune fuite).

---

## Partie A — Audit des 6 décisions du 30/08

| Match | Prédit (H/D/A) | Marché | Score réel | Issue |
|---|---|---|---|---|
| Chelsea–Brighton | 51.6 / 21.4 / 27.0 | 50.9 / 25.4 / 23.8 | **4-3** | H |
| Man Utd–Ipswich | 65.8 / 17.6 / 16.6 | 69.4 / 18.7 / 11.9 | **5-2** | H |
| Napoli–Como | 34.8 / 23.0 / 42.2 | 38.2 / 31.4 / 30.4 | **1-2** | A |
| Lazio–Genoa | 41.1 / 23.9 / 34.9 | 43.3 / 32.1 / 24.5 | **1-0** | H |
| Monaco–Marseille | 47.6 / 20.8 / 31.6 | 40.9 / 26.7 / 32.4 | **2-0** | H |

### Décisions, une par une

| Décision du 30/08 | Verdict | P&L réel |
|---|---|---|
| **Monaco (1) @ 2.28** — seul candidat retenu | ✅ **GAGNÉ** | **+1.28 u** |
| Over 2.5 Monaco–OM @ 1.53 — rejeté (seuil λ 3.38 > empirique 3.26) | ✅ rejet correct | 0 u (aurait perdu) |
| Ipswich (2) @ 8.00, edge +38.9% — rejeté (sensibilité 40 pts) | ✅ rejet correct | 0 u (aurait perdu) |
| Genoa (2) @ 3.80, edge +42.5% — rejeté (sensibilité 46 pts) | ✅ rejet correct | 0 u (aurait perdu) |
| Brighton (2) @ 4.00, edge +12.9% — rejeté | ✅ rejet correct | 0 u (aurait perdu) |
| Como (2) @ 3.05, edge +38.7% — rejeté (sensibilité 22 pts) | ❌ **rejet à tort** | 0 u (aurait gagné +2.05) |

**Le filtre de sensibilité a rejeté 4 perdants et 1 gagnant** : il a protégé 4.00 u et
coûté 2.05 u, soit **+1.95 u net**. C'est sa première validation empirique.

### Ce qu'il ne faut PAS conclure

Le modèle affiche Brier 0.396 vs 0.449 pour le marché et 5/5 sur les issues. **C'est du
bruit.** Sur les 116 matchs hors-échantillon, le Brier réel du marché est **0.597** — le
0.449 du 30/08 était un tirage favorable. Cinq matchs ne prouvent rien, et une réussite
de 5/5 sur des probabilités moyennes de ~50 % est simplement de la chance.

Les buts : 20 réels contre 14.75 prédits (ratio 1.36). Écart-type de Poisson sur la
somme = 3.84, donc **z = +1.37 — non significatif**. Aucune correction à en tirer.

---

## Partie B — Recalibrage sur 202 matchs

### Paramètres réels de la saison en cours

| Ligue | N | buts/match | param moteur | écart | dom/ext | O2.5 |
|---|---|---|---|---|---|---|
| Premier League | 40 | 2.85 | 2.89 | −0.04 ✅ | 1.073 | 52.5% |
| Serie A | 40 | **3.02** | **2.45** | **+0.57** ⚠ | 0.952 | 57.5% |
| Ligue 1 | 36 | 2.75 | 2.78 | −0.03 ✅ | 1.020 | 52.8% |
| La Liga | 59 | 3.05 | — | — | 1.278 | 55.9% |
| Bundesliga | 27 | **3.85** | **3.10** | **+0.75** ⚠ | 1.600 | 81.5% |

### La faute du 30/08 : k = 1.140

Le rapport du 30/08 a diagnostiqué un biais domicile de −8.62 points et imposé une
correction **k = 1.140, fittée sur 5 matchs**. Testée hors-échantillon sur 116 matchs, la
courbe de log-loss est **monotone croissante** :

| k | LogLoss | |
|---|---|---|
| **1.00** | **1.0048** | ← optimum |
| 1.08 | 1.0198 | |
| **1.14** | **1.0377** | ← valeur appliquée le 30/08, **+3.3 % pire** |
| 1.20 | 1.0604 | |

Le biais de −8.62 points était du bruit d'échantillonnage. Le HOME_ADV des moteurs suffit :
EPL 1.08 contre un ratio buts dom/ext réellement observé de **1.073**. La correction ne
corrigeait rien — elle dégradait. **C'est précisément l'erreur que le protocole est censé
empêcher, et je l'ai commise puis versée dans l'outil.**

### Modèle vs marché — 116 matchs, k = 1.00

| | Modèle | Marché (clôture) |
|---|---|---|
| Brier | 0.5946 | 0.5970 |
| LogLoss | 1.0048 | **1.0010** |
| Issues correctes | 51.7 % | 50.9 % |
| Buts/match | 2.88 | 2.88 (ratio 1.001) |

**Parité avec le marché.** L'échelle des λ est excellente. Mais parité = aucun edge
systématique à récolter.

### Backtest ROI — cotes de clôture

| Marché | Seuil | Bets | ROI | IC 95 % |
|---|---|---|---|---|
| 1X2 | 3 % | 147 | +0.4 % | [−28.3 ; +29.1] |
| 1X2 | 5 % | 136 | +1.5 % | [−28.8 ; +31.8] |
| 1X2 | 8 % | 118 | −4.6 % | [−37.5 ; +28.4] |
| 1X2 | 15 % | 87 | −10.1 % | [−50.1 ; +29.9] |
| O/U 2.5 | 3 % | 93 | −8.6 % | [−28.9 ; +11.6] |
| O/U 2.5 | 15 % | 30 | +0.9 % | [−39.0 ; +40.7] |

**Aucun ROI n'est significatif.** Les intervalles de confiance font 60 points de large.

Correction d'une lecture trop rapide : en cumulé le ROI semble décroître avec l'edge, ce
qui validerait la règle SUSPICIOUS_EDGE. Mais en **bandes disjointes** le signal disparaît
(3-5 % : −13.6 % · 5-8 % : +41.2 % · 8-12 % : −38.4 % · 12-20 % : +24.3 % · >20 % : −7.3 %).
C'est du bruit, pas une tendance. **Le seuil de 15 % reste donc inchangé** — faute de
preuve, pas par conviction.

---

## Recalibrages appliqués

### R1 — Suppression du coefficient k

```
RÈGLE ACTUELLE   : lambda_home x k, lambda_away / k avec k fitté sur le marché
PROBLÈME OBSERVÉ : k=1.140 fitté sur 5 matchs → +3.3% de log-loss sur 116 matchs
                   hors-échantillon ; courbe monotone, optimum franc à k=1.00
NOUVELLE RÈGLE   : HOME_K = 1.00. fit_home_k() lève ValueError sous 50 matchs.
JUSTIFICATION    : le HOME_ADV des moteurs capture déjà l'avantage domicile réel
                   (EPL 1.08 vs 1.073 observé). Le k était un sur-ajustement.
PRUDENCE         : FAIBLE — preuve directe, 116 matchs, courbe monotone.
```
→ appliqué dans `tools/dixon_coles.py` (constante `HOME_K` + garde-fou `MIN_FIT_SAMPLE`).

### R2 — Dérive des paramètres de ligue : signalée, non corrigée

```
RÈGLE ACTUELLE   : Serie A avg_goals 2.45 ; Bundesliga 3.10
PROBLÈME OBSERVÉ : réel 3.02 (Serie A, 40 matchs) et 3.85 (Bundesliga, 27 matchs)
NOUVELLE RÈGLE   : AUCUNE. Inscription en PARAM_DRIFT_WATCH, revue à 50 matchs.
JUSTIFICATION    : < 50 matchs par ligue = ANALYSE SEULE (règle backtester).
                   Changer un paramètre de ligue sur 27 matchs répéterait
                   exactement l'erreur du k.
PRUDENCE         : ÉLEVÉE
```

### R3 — Défaut NO BET confirmé

```
RÈGLE ACTUELLE   : NO BET par défaut, edge minimum 3%
PROBLÈME OBSERVÉ : aucun — le modèle est à parité avec le marché de clôture
NOUVELLE RÈGLE   : inchangée, désormais justifiée empiriquement
PRUDENCE         : FAIBLE
```

### Non modifié faute de preuve

- **Seuil SUSPICIOUS_EDGE (15 %)** : bandes disjointes non concluantes.
- **Filtre de sensibilité** : 4/5 correct, mais n = 5. À re-mesurer.
- **Gates DCS** : aucune donnée d'audit.

---

## Automatisation

`tools/weekly_audit.py` rejoue toute cette chaîne à la demande :

```bash
python3 tools/weekly_audit.py                 # audit à l'écran
python3 tools/weekly_audit.py --write-report   # + reports/<date>-audit-auto.md
```

Il télécharge les résultats et cotes de clôture, mesure les paramètres réels par ligue,
cherche le k optimal hors-échantillon, backteste le ROI par seuil avec intervalles de
confiance, et **applique lui-même les paliers du backtester** (ABORT < 10, ANALYSE SEULE
< 50, MODÉRÉ 100-300). Il refuse d'appliquer un k sous 50 matchs.

## Validation hors-échantillon exigée

Le backtester impose ≥ 30 nouveaux matchs avant tout déploiement. R1 (k = 1.00) est un
**retour au défaut**, pas un nouvel ajustement : il ne nécessite pas de validation
préalable. R2 reste en observation jusqu'à 50 matchs par ligue.
