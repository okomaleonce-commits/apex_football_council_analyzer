# Déploiement en ligne (Render)

Ce guide met la plateforme APEX en ligne sur une vraie URL publique. Tout est déjà
configuré dans `render.yaml` — tu n'as que des clics à faire.

## Avant de commencer

- Un compte **GitHub** avec ce dépôt poussé (c'est fait).
- Un compte **Render** gratuit → https://render.com (connecte-le à GitHub).

> ℹ️ Le plan `starter` (~7 $/mois) est utilisé car il permet le **disque
> persistant**, indispensable pour que les comptes et abonnements survivent aux
> redéploiements. Le plan gratuit efface le disque à chaque redémarrage — à éviter
> pour une base de données.

## Étape 1 — Créer le service (Blueprint)

1. Sur Render : **New → Blueprint**.
2. Sélectionne ce dépôt GitHub (`apex_football_council_analyzer`), branche de ton
   choix.
3. Render lit `render.yaml` automatiquement et propose de créer le service
   `apex-football-council-analyzer` **avec son disque persistant**.
4. Clique **Apply**. Le build démarre (installe les dépendances, lance uvicorn).

Le `SECRET_KEY` est généré automatiquement par Render (sécurisé). Le `DB_PATH`
pointe déjà sur le disque persistant (`/var/data/apex.db`).

## Étape 2 — Vérifier

Quand le déploiement est « Live », ouvre l'URL fournie par Render
(ex. `https://apex-football-council-analyzer.onrender.com`) :

- `/platform` → la vitrine
- `/board`, `/predictions`, `/coupons`, `/montante` → les 4 modules
- `/account` → crée un compte, teste l'abonnement en **mode démo**
  (paiement simulé, l'abonnement s'active).

Le `/health` doit répondre `{"status":"ok"}` (c'est le health check de Render).

> L'URL publique est **auto-détectée** : rien à configurer pour que le paiement
> démo et les retours fonctionnent. (Pour un domaine personnalisé, renseigne
> `APP_BASE_URL`.)

## Étape 3 — Passer le paiement en RÉEL (quand tu veux encaisser)

Tant que `PAYMENTS_MODE=demo`, les paiements sont simulés. Pour encaisser vraiment
via mobile money :

1. Crée un compte marchand **CinetPay** → https://cinetpay.com (Orange Money, MTN,
   Moov, Wave, cartes). Récupère ton `API_KEY` et ton `SITE_ID`.
2. Sur Render → ton service → **Environment** :
   - `PAYMENTS_MODE` = `live`
   - `CINETPAY_API_KEY` = ta clé
   - `CINETPAY_SITE_ID` = ton site id
3. **Save, rebuild**. C'est tout — le code bascule du simulé au réel.
4. Dans ton tableau de bord CinetPay, l'URL de notification (webhook) est
   `https://TON-URL/api/payments/webhook` (déjà envoyée automatiquement à chaque
   paiement).

## Étape 4 (optionnel) — Cotes en direct

Pour que le Value Scanner passe de « démo » à « en direct » :

1. Clé gratuite sur https://the-odds-api.com
2. Sur Render → Environment → `ODDS_API_KEY` = ta clé → rebuild.

## Réglages utiles (Environment)

| Variable | Rôle | Défaut |
|---|---|---|
| `SUBSCRIPTION_PRICE` | Prix de l'abonnement | `5000` |
| `SUBSCRIPTION_CURRENCY` | Devise | `XOF` (FCFA) |
| `SUBSCRIPTION_DAYS` | Durée en jours | `30` |
| `PAYMENTS_MODE` | `demo` ou `live` | `demo` |

## Mettre à jour le site

Chaque `git push` sur la branche déployée redéclenche automatiquement un build
Render. Les comptes et abonnements sont conservés (disque persistant).

## Rappels

- Sauvegarde régulièrement `/var/data/apex.db` (Render permet des snapshots de
  disque) — c'est toute ta base clients.
- Reste en **mode éducatif** : pas de promesse de gain, mentions +18 et jeu
  responsable (déjà présentes sur chaque page).
