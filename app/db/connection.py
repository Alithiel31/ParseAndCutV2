"""
Accès SQLite : une connexion par thread (le module sqlite3 interdit par défaut
de partager une connexion entre threads), en mode WAL pour autoriser lecteurs
et écrivain concurrents entre les workers Uvicorn et les threads de traitement.
"""
import os
import sqlite3
import threading

from app import config

_local = threading.local()
BUSY_TIMEOUT_MS = 10_000


def _open(db_path: str) -> sqlite3.Connection:
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    # isolation_level=None : autocommit, les transactions sont explicites
    # (BEGIN/COMMIT) — nécessaire pour les claims atomiques de la file de jobs.
    conn = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_MS / 1000, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    return conn


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Connexion du thread courant vers `db_path` (défaut : config.DB_PATH,
    relu à chaque appel pour que les tests puissent le surcharger)."""
    path = db_path or config.DB_PATH
    cache = getattr(_local, "conns", None)
    if cache is None:
        cache = _local.conns = {}
    conn = cache.get(path)
    if conn is None:
        conn = cache[path] = _open(path)
    return conn


def close_connections() -> None:
    """Ferme les connexions du thread courant (tests, arrêt propre)."""
    for conn in getattr(_local, "conns", {}).values():
        conn.close()
    _local.conns = {}
