"""Authentification : hachage de mot de passe et sessions par cookie.

Sans dépendance externe : PBKDF2-HMAC-SHA256 (stdlib) pour les mots de passe,
jetons de session aléatoires stockés hachés en base. Le cookie est httponly.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from app.core import db

_PBKDF2_ROUNDS = 200_000
SESSION_COOKIE = "apex_session"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${_PBKDF2_ROUNDS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, rounds, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_session(user_id: int, days: int) -> str:
    """Crée une session et renvoie le jeton en clair (à poser en cookie)."""
    token = secrets.token_urlsafe(32)
    db.create_session(_token_hash(token), user_id, days)
    return token


def user_from_token(token: str | None):
    if not token:
        return None
    return db.get_session_user(_token_hash(token))


def revoke(token: str | None) -> None:
    if token:
        db.delete_session(_token_hash(token))


def is_subscribed(user_row) -> bool:
    if not user_row or not user_row["subscription_until"]:
        return False
    return datetime.fromisoformat(user_row["subscription_until"]) > datetime.now(timezone.utc)


def extend_subscription(user_id: int, days: int):
    now = datetime.now(timezone.utc)
    current = db.get_user_by_id(user_id)
    base = now
    if current and current["subscription_until"]:
        existing = datetime.fromisoformat(current["subscription_until"])
        if existing > now:
            base = existing
    until = base + timedelta(days=days)
    db.set_subscription_until(user_id, until)
    return until
