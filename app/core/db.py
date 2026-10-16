"""Stockage SQLite : utilisateurs, sessions, paiements.

Volontairement simple (sqlite3 de la stdlib, une connexion par appel). Suffisant
pour un MVP. En production sur un conteneur éphémère, pointe `db_path` vers un
volume persistant (ou migre vers Postgres).
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

_DB_PATH = "apex.db"


def configure(db_path: str) -> None:
    """Configure le chemin de la base. Robuste : crée le dossier si besoin et
    bascule sur une base locale si le chemin visé est inaccessible (ex. disque
    persistant non monté), pour que l'app démarre au lieu de planter (502)."""
    global _DB_PATH
    target = Path(db_path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        _DB_PATH = str(target.resolve())
        init_db()
    except (OSError, sqlite3.Error) as exc:
        fallback = Path(__file__).resolve().parent.parent / "apex.db"
        print(f"[db] chemin '{db_path}' inaccessible ({exc}); repli local sur {fallback}. "
              f"⚠️ Base NON persistante : monte un disque sur ce chemin pour conserver les comptes.")
        _DB_PATH = str(fallback)
        init_db()


@contextmanager
def _conn():
    con = sqlite3.connect(_DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with _conn() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                subscription_until TEXT
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS payments (
                transaction_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                currency TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
        )


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- Utilisateurs -----------------------------------------------------------
def create_user(email: str, password_hash: str) -> int:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO users(email, password_hash, created_at) VALUES(?,?,?)",
            (email.lower().strip(), password_hash, _now().isoformat()),
        )
        return cur.lastrowid


def get_user_by_email(email: str) -> sqlite3.Row | None:
    with _conn() as con:
        return con.execute("SELECT * FROM users WHERE email=?", (email.lower().strip(),)).fetchone()


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    with _conn() as con:
        return con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()


def set_subscription_until(user_id: int, until: datetime) -> None:
    with _conn() as con:
        con.execute("UPDATE users SET subscription_until=? WHERE id=?", (until.isoformat(), user_id))


# --- Sessions ---------------------------------------------------------------
def create_session(token_hash: str, user_id: int, days: int) -> None:
    with _conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO sessions(token_hash, user_id, expires_at) VALUES(?,?,?)",
            (token_hash, user_id, (_now() + timedelta(days=days)).isoformat()),
        )


def get_session_user(token_hash: str) -> sqlite3.Row | None:
    with _conn() as con:
        row = con.execute("SELECT * FROM sessions WHERE token_hash=?", (token_hash,)).fetchone()
        if not row:
            return None
        if datetime.fromisoformat(row["expires_at"]) < _now():
            con.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))
            return None
        return con.execute("SELECT * FROM users WHERE id=?", (row["user_id"],)).fetchone()


def delete_session(token_hash: str) -> None:
    with _conn() as con:
        con.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))


# --- Paiements --------------------------------------------------------------
def create_payment(transaction_id: str, user_id: int, amount: int, currency: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO payments(transaction_id, user_id, amount, currency, status, created_at) VALUES(?,?,?,?,?,?)",
            (transaction_id, user_id, amount, currency, "PENDING", _now().isoformat()),
        )


def get_payment(transaction_id: str) -> sqlite3.Row | None:
    with _conn() as con:
        return con.execute("SELECT * FROM payments WHERE transaction_id=?", (transaction_id,)).fetchone()


def set_payment_status(transaction_id: str, status: str) -> None:
    with _conn() as con:
        con.execute("UPDATE payments SET status=? WHERE transaction_id=?", (status, transaction_id))
