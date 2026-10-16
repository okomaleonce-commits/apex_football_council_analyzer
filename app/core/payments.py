"""Paiement mobile money via CinetPay (Orange Money, MTN, Moov, Wave, cartes).

Deux modes (settings.payments_mode) :
  - "demo" : aucun vrai paiement. init_payment renvoie une URL interne de
    simulation ; l'utilisateur « paie » d'un clic. Idéal pour tester le flux.
  - "live" : appelle l'API CinetPay. init_payment ouvre une page de paiement
    hébergée ; CinetPay notifie notre webhook, qu'on vérifie via l'API /check.

On ne manipule JAMAIS les identifiants bancaires/mobile money de l'acheteur :
tout se passe sur la page hébergée du prestataire. On ne fait confiance au
webhook qu'après re-vérification côté serveur (jamais le corps seul).
"""
from __future__ import annotations

import secrets

import httpx


def new_transaction_id() -> str:
    return "APEX-" + secrets.token_hex(10)


async def init_payment(settings, base_url: str, transaction_id: str, amount: int, description: str) -> dict:
    """Renvoie {payment_url, mode}. `base_url` = origine publique du service.

    Lève une exception en cas d'échec live.
    """
    base_url = base_url.rstrip("/")
    if settings.payments_mode != "live" or not (settings.cinetpay_api_key and settings.cinetpay_site_id):
        return {"mode": "demo", "payment_url": f"{base_url}/pay/demo?tx={transaction_id}"}

    payload = {
        "apikey": settings.cinetpay_api_key,
        "site_id": settings.cinetpay_site_id,
        "transaction_id": transaction_id,
        "amount": amount,
        "currency": settings.subscription_currency,
        "description": description,
        "notify_url": f"{base_url}/api/payments/webhook",
        "return_url": f"{base_url}/account",
        "channels": "ALL",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(f"{settings.cinetpay_base_url}/payment", json=payload)
        data = resp.json()
    if str(data.get("code")) != "201":
        raise RuntimeError(f"CinetPay init error: {data.get('message') or data}")
    return {"mode": "live", "payment_url": data["data"]["payment_url"]}


async def verify_payment(settings, transaction_id: str) -> str:
    """Vérifie l'état réel d'une transaction. Renvoie ACCEPTED / REFUSED / PENDING."""
    if settings.payments_mode != "live":
        return "PENDING"  # en démo, la confirmation passe par l'endpoint dédié
    payload = {
        "apikey": settings.cinetpay_api_key,
        "site_id": settings.cinetpay_site_id,
        "transaction_id": transaction_id,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(f"{settings.cinetpay_base_url}/payment/check", json=payload)
        data = resp.json()
    status = (data.get("data") or {}).get("status", "")
    if status == "ACCEPTED":
        return "ACCEPTED"
    if status in ("REFUSED", "CANCELED"):
        return "REFUSED"
    return "PENDING"
