# Moteur de trafic APEX

Le produit numérique ne se vend pas tout seul : il faut des visiteurs sur la page
de vente. Ce moteur fabrique le **carburant** — du contenu social tiré de tes
analyses de matchs, qui montre la méthode et renvoie vers le produit.

C'est la boucle qui rend le modèle durable :

```
match → analyse APEX → post (TikTok/X) → audience → page de vente → ventes
```

## Ce qu'il produit

À partir d'un `AnalysisReport` (la sortie de ton moteur d'analyse) :

1. **Carrousel TikTok / Instagram** — 6 slides (hook → données → modèle → value →
   verdict → CTA), dans l'esprit des slides qui t'ont inspiré.
2. **Thread X / Threads** — la même analyse en format thread.
3. **Slides HTML 9:16** — un fichier prêt à **screenshoter** slide par slide pour
   ton carrousel (pas besoin d'outil de design).

## Utilisation

```bash
# Démo (match fictif, aucune clé API requise)
python product/traffic-engine/content_generator.py --demo

# Démo + génère les slides visuelles
python product/traffic-engine/content_generator.py --demo --html slides.html

# Depuis une vraie analyse exportée en JSON
python product/traffic-engine/content_generator.py --report mon_analyse.json --html slides.html
```

Pour obtenir un `rapport.json` depuis ton app : l'endpoint d'analyse renvoie déjà un
`AnalysisReport` ; sauvegarde sa réponse JSON et passe-la en `--report`.

## À personnaliser

En haut de `content_generator.py` :

- `PRODUCT_URL` → l'URL de ton produit (Gumroad/Lemon Squeezy).
- `BRAND` → le nom affiché en filigrane.
- `DISCLAIMER` → l'avertissement (garde une mention +18 / risque).

## Cadrage (non négociable)

Le contenu est **éducatif** : il montre *comment on raisonne*, pas « parie ça et
gagne ». Même un verdict `NO_BET` fait un excellent post (« voici pourquoi je ne
parie PAS ») — la discipline est ce qui crée la confiance de l'audience, et la
confiance est ce qui vend. Chaque pièce porte un disclaimer +18 / risque de perte.

> ⚠️ Vérifie la réglementation publicité paris de ton pays. Promouvoir une *méthode
> éducative* est différent de pousser des *pronostics* ou de faire la *pub d'un
> bookmaker*. Reste du côté éducatif.

## Idée de cadence (régularité > perfection)

- 3 à 5 posts/semaine, un par match analysé.
- Réutilise : 1 analyse → 1 carrousel + 1 thread + 1 short.
- Épingle ton meilleur post qui pointe vers la page de vente.
