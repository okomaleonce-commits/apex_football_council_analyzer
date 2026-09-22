# 22/09/2026 — screening du jour : NO BET

211 matchs au programme, **aucun marché recommandable**. Décision et motifs.

## Composition de la carte

| Bloc | Matchs | Nature |
|---|---|---|
| Ligue des Champions féminine | 5 | J1 du nouveau format à 18 équipes |
| Coupe KNVB, 2e tour préliminaire | 14 | clubs amateurs (ACV, Eemdijk, Kloetinge, Spakenburg…) |
| EFL Trophy, phase de groupes | 23 | League One/Two contre équipes U21 de Premier League |
| Challenge Cup écossaise | 18 | divisions inférieures + équipes B (Aberdeen II, Hibernian II) |
| Iran Division 1 | 5 | **deuxième division** |
| Qatar QSL Cup, Algérie L1 | 4 | coupe / ligue sans moteur |
| Colombie, Brésil Série B | 3 | après minuit (01h00–03h00 CEST) |

## Motif de rejet, bloc par bloc

**Ligue des Champions féminine.** `apex-engine-uefa` est calibré sur le football masculin
(backtest 150 matchs 2024-25 + 30 UCL 2025-26). Aucun de mes jeux de données ne couvre le
football féminin — football-data.co.uk est exclusivement masculin. S'y ajoute une J1 d'un
format inédit : zéro échantillon dans le format. Tout chiffre que je produirais serait inventé.

**KNVB Cup, EFL Trophy, Challenge Cup.** Trois compétitions qui cumulent tout ce que S5
bloque : rotation massive, équipes U21 et B sans enjeu de classement, clubs amateurs, et
pour l'EFL Trophy des tirs au but qui distribuent des points bonus. Aucune donnée, aucun
moteur, volatilité EXTRÊME par construction.

**Iran D1, Qatar Cup, Algérie.** Aucun moteur `apex-engine-*`, aucune couverture de données.
L'Iran est de surcroît une deuxième division.

**Dernier recours vérifié et fermé.** Allsvenskan (moteur v2.0 recalibré sur 162 matchs),
Eliteserien et Veikkausliiga sont les seules ligues où j'aurais eu moteur **et** données.
Dernier match joué le 19-20/09, **rien de programmé** : la trêve XL couvre toutes les
nations UEFA.

## Ce que cette journée a de particulier

Ce n'est pas une carte pauvre, c'est une carte **structurellement adverse**. Un mardi de
trêve internationale ne laisse que des tours préliminaires de coupe et des équipes
réserves — exactement le profil de matchs où le bookmaker a peu d'information mais où
l'analyste en a encore moins. L'asymétrie joue contre le parieur.

## Prochaine échéance exploitable

| Date | Slate | État |
|---|---|---|
| 24/09 | Seattle – Real Salt Lake (MLS) | prix d'entrée déjà calculés |
| 27/09 | 14 matchs MLS | prix d'entrée déjà calculés, cotes pas encore ouvertes |
| ~10/10 | reprise des championnats européens | moteurs pleinement applicables |

Rappel de l'audit du 21/09 : sur la MLS le modèle est battu par le marché hors-échantillon
(ROI −14.7 %). Les prix d'entrée du 27/09 sont des repères de comparaison, pas des signaux.
