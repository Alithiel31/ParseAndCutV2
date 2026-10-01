"""
Migrations SQL versionnées : fichiers `app/db/migrations/NNNN_nom.sql`,
appliqués dans l'ordre, chacun dans sa propre transaction, et tracés dans la
table `schema_version`. Idempotent et sûr si plusieurs workers Uvicorn
démarrent en même temps.
"""
import os
import re
import sqlite3
import time

from app.config import logger
from app.db.connection import get_connection

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")
_FILE_RE = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")


def _discover() -> list[tuple[int, str, str]]:
    found = []
    for filename in sorted(os.listdir(MIGRATIONS_DIR)):
        match = _FILE_RE.match(filename)
        if match:
            found.append((int(match.group(1)), match.group(2), os.path.join(MIGRATIONS_DIR, filename)))
    return found


def _applied(conn: sqlite3.Connection) -> set[int]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version ("
        " version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at REAL NOT NULL)"
    )
    return {row["version"] for row in conn.execute("SELECT version FROM schema_version")}


def migrate(db_path: str | None = None) -> list[int]:
    """Applique les migrations manquantes ; retourne les versions appliquées."""
    conn = get_connection(db_path)
    applied = _applied(conn)
    done = []
    for version, name, path in _discover():
        if version in applied:
            continue
        with open(path, "r", encoding="utf-8") as f:
            sql = f.read()
        script = (
            "BEGIN IMMEDIATE;\n" + sql + "\n"
            f"INSERT INTO schema_version (version, name, applied_at) VALUES ({version}, '{name}', {time.time()});\n"
            "COMMIT;"
        )
        try:
            conn.executescript(script)
        except sqlite3.Error:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            # Un autre worker a pu appliquer la migration entre-temps.
            if version in _applied(conn):
                applied.add(version)
                continue
            raise
        logger.info(f"🗄️  Migration {version:04d}_{name} appliquée")
        done.append(version)
    return done
