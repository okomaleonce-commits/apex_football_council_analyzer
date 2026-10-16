# Produit numérique — Framework APEX

Ce dossier contient un **produit numérique prêt à vendre**, construit à partir de la
méthode d'analyse de ton moteur APEX. Modèle économique : tu le crées une fois, tu
le vends en boucle. C'est la forme de revenu la plus proche du « passif » — peu
d'infrastructure, pas de livraison manuelle.

## Contenu

```
product/
  guide/APEX-Framework-Guide.md        ← LE produit (à exporter en PDF)
  templates/match-analysis-worksheet.csv ← bonus livré avec
  sales-page/index.html                ← page de vente déployable
  README.md                            ← ce playbook
```

---

## Pourquoi « semi-passif » et pas « passif »

Sois lucide : le travail n'est pas nul, il est **concentré au début**.

- **Effort initial** : finaliser le contenu, le mettre en page, créer la page de
  vente, configurer la plateforme de paiement. ~1 à 2 week-ends.
- **Effort continu** : répondre à quelques e-mails clients, améliorer le produit,
  et surtout **amener du trafic** (c'est là que 90 % du vrai travail se cache).

Une fois en place, la vente et la livraison, elles, sont automatiques. C'est ça le
« passif » : le mécanisme de vente tourne sans toi, pas l'acquisition de clients.

---

## Étape 1 — Finaliser le produit (livrable)

1. **Relis et personnalise** `guide/APEX-Framework-Guide.md` (ton nom, ta marque,
   ajoute tes propres exemples pour le rendre unique).
2. **Construis le pack automatiquement** :
   ```bash
   pip install -r product/requirements-build.txt   # weasyprint (une fois)
   python product/build.py
   ```
   Le script génère le PDF stylé et assemble `product/dist/APEX-Framework-Pack.zip`
   (PDF + worksheet). Il te faut `pandoc` installé au niveau système
   (https://pandoc.org/installing.html). Sans moteur PDF, le pack contient le HTML :
   ouvre-le et fais « Imprimer → Enregistrer en PDF ».
3. Le ZIP est prêt à uploader — c'est le fichier que tes clients recevront.

## Étape 2 — Mettre en vente (le « moteur »)

**Choisis la plateforme selon ta région** : ce qui compte, ce n'est pas la carte
mais la capacité de la plateforme à te *verser* l'argent là où tu vis.

- **Europe / Amérique du N.** : Lemon Squeezy ou Gumroad (gèrent TVA + livraison).
- **Afrique francophone** : **Selar** (⭐ conçu pour les créateurs africains, paie
  sur compte bancaire local + Mobile Money) ou **Flutterwave** (cartes locales,
  Mobile Money, virements). Gumroad et Stripe ne versent pas dans la plupart de ces
  pays — ne perds pas de temps avec eux. Payhip marche seulement si ton PayPal peut
  *recevoir* (variable selon le pays).

Quelle que soit la plateforme, le principe est identique :
1. Crée un compte → nouveau produit → produit numérique.
2. Upload `APEX-Framework-Pack.zip`.
3. Prix de départ suggéré : **~10 000 FCFA / 19 €** (voir pricing ci-dessous).
4. Récupère l'URL publique du produit.
5. **Colle cette URL** dans `sales-page/index.html` (commentaire
   `REMPLACE l'URL ci-dessous`, bouton « Acheter maintenant ») **et** dans
   `traffic-engine/content_generator.py` (variable `PRODUCT_URL`).

## Étape 3 — Publier la page de vente

`sales-page/index.html` est un fichier statique autonome. Déploie-le gratuitement :

- **Netlify Drop** (glisser-déposer le dossier `sales-page/`), ou
- **GitHub Pages** (le dossier `sales-page/` → settings Pages), ou
- **Cloudflare Pages / Vercel**.

Ou intègre-la à ton app FastAPI existante (tu sers déjà du statique dans
`app/static/`). Tu peux aussi laisser Gumroad héberger sa propre page et utiliser
celle-ci comme landing page marketing qui pointe vers Gumroad.

## Étape 4 — Amener du trafic (le vrai travail continu)

Sans trafic, zéro vente. Le canal le plus cohérent avec ce produit :

- **Contenu analytique public** : poste tes analyses APEX sur X/Threads/TikTok
  (comme les slides qui t'ont inspiré). Chaque analyse montre la méthode → renvoie
  vers le guide. C'est la boucle « contenu → produit » qui rend tout cela durable.
- **SEO** : un article de blog « comment détecter un value bet » qui pointe vers le
  produit.
- **Communautés** : Reddit/Discord paris sportifs (en apportant de la valeur, pas
  du spam — tu te feras bannir sinon).

---

## Pricing : la logique

| Prix | Positionnement | Volume pour ~300 000 FCFA (≈500 €)/mois |
|---|---|---|
| ~5 000 FCFA (9 €) | Impulsion, gros volume | ~55 ventes/mois |
| **~10 000 FCFA (19 €)** | **Recommandé pour lancer** | ~26 ventes/mois |
| ~20 000 FCFA (39 €) | Premium, moins de volume | ~13 ventes/mois |

Commence à 19 €, lance en « early bird » à prix barré (39 € → 19 €) pour créer de
l'urgence. Monte le prix quand tu auras des avis clients.

---

## Attentes réalistes (lis ça deux fois)

- Les **premières semaines font souvent 0 vente.** Normal. Le produit ne se vend pas,
  c'est le trafic qui vend.
- Un produit numérique sans audience existante converti typiquement **1 à 3 %** des
  visiteurs. 1000 visiteurs → 10 à 30 ventes.
- Le levier n°1 n'est pas le produit, c'est **la distribution** (ton audience). Si
  tu n'as pas d'audience, le plan « contenu + affiliation » est le préalable à
  celui-ci.
- « Passif » ≠ « sans effort ». Ça veut dire « l'effort est découplé du temps » : un
  guide écrit une fois peut se vendre 1000 fois.

---

## Checklist de lancement

- [ ] Guide personnalisé et exporté en PDF
- [ ] Pack ZIP créé (PDF + worksheet)
- [ ] Produit créé sur Gumroad/Lemon Squeezy, fichier uploadé, prix fixé
- [ ] URL du produit collée dans `sales-page/index.html`
- [ ] Page de vente déployée (Netlify/Pages)
- [ ] Mentions légales + avertissements jeu présents (déjà inclus dans la page)
- [ ] 3 contenus publics préparés qui renvoient vers le produit
- [ ] Journal de ventes + feedback clients en place

---

## Conformité (important)

- **Pas de promesse de gain**, pas de « pronostics garantis ». C'est de l'éducation.
- **Avertissement jeu responsable** et **+18** sur chaque support (déjà dans le guide
  et la page).
- Vérifie la **réglementation publicité paris** de ton pays (en France, encadrée par
  l'ANJ). Vendre une *méthode éducative* est différent de vendre des *pronostics* ou
  de faire de la *pub pour un bookmaker* — reste du côté éducatif.
- Mentions légales vendeur (identité, remboursement, contact) exigées par la plupart
  des plateformes et par la loi — Gumroad/Lemon Squeezy en fournissent le cadre.

---

*Produit éducatif. Pas un conseil financier. Jouer comporte des risques. +18.*
