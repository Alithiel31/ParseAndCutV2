import sqlite3
import threading

import pytest

from app.db.connection import close_connections, get_connection
from app.db.migrate import migrate


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    yield path
    close_connections()


def _doc(conn, doc_id="d1", owner="o1"):
    conn.execute(
        "INSERT INTO documents (id, owner_id, created_at, updated_at) VALUES (?, ?, 1, 1)",
        (doc_id, owner),
    )


class TestMigrations:
    def test_applique_le_schema_initial(self, db_path):
        assert migrate(db_path) == [1]
        conn = get_connection(db_path)
        tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"documents", "jobs", "transcripts", "segments", "notes", "schema_version"} <= tables

    def test_idempotent(self, db_path):
        migrate(db_path)
        assert migrate(db_path) == []
        rows = get_connection(db_path).execute("SELECT version FROM schema_version").fetchall()
        assert [r["version"] for r in rows] == [1]

    def test_demarrages_concurrents(self, db_path):
        errors = []

        def run():
            try:
                migrate(db_path)
            except Exception as e:  # pragma: no cover
                errors.append(e)
            finally:
                close_connections()

        threads = [threading.Thread(target=run) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        rows = get_connection(db_path).execute("SELECT version FROM schema_version").fetchall()
        assert [r["version"] for r in rows] == [1]


class TestConnection:
    def test_pragmas(self, db_path):
        conn = get_connection(db_path)
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    def test_une_connexion_par_thread(self, db_path):
        main_conn = get_connection(db_path)
        other = []
        t = threading.Thread(target=lambda: other.append(get_connection(db_path)))
        t.start()
        t.join()
        assert other[0] is not main_conn
        assert get_connection(db_path) is main_conn


class TestSchema:
    def test_suppression_en_cascade(self, db_path):
        migrate(db_path)
        conn = get_connection(db_path)
        _doc(conn)
        conn.execute("INSERT INTO jobs (id, document_id, owner_id, created_at) VALUES ('j1', 'd1', 'o1', 1)")
        conn.execute("INSERT INTO transcripts (id, document_id, provider, created_at) VALUES ('t1', 'd1', 'groq', 1)")
        conn.execute(
            "INSERT INTO segments (transcript_id, idx, start_sec, end_sec, text) VALUES ('t1', 0, 0, 1.5, 'salut')"
        )
        conn.execute(
            "INSERT INTO notes (id, document_id, transcript_id, content_md, created_at) VALUES ('n1', 'd1', 't1', '# x', 1)"
        )
        conn.execute("DELETE FROM documents WHERE id='d1'")
        for table in ("jobs", "transcripts", "segments", "notes"):
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0

    def test_cle_etrangere_imposee(self, db_path):
        migrate(db_path)
        with pytest.raises(sqlite3.IntegrityError):
            get_connection(db_path).execute(
                "INSERT INTO jobs (id, document_id, owner_id, created_at) VALUES ('j1', 'absent', 'o1', 1)"
            )

    def test_statut_job_invalide_refuse(self, db_path):
        migrate(db_path)
        conn = get_connection(db_path)
        _doc(conn)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO jobs (id, document_id, owner_id, status, created_at) VALUES ('j1', 'd1', 'o1', 'bogus', 1)"
            )

    def test_segment_unique_par_transcript_et_index(self, db_path):
        migrate(db_path)
        conn = get_connection(db_path)
        _doc(conn)
        conn.execute("INSERT INTO transcripts (id, document_id, provider, created_at) VALUES ('t1', 'd1', 'groq', 1)")
        ins = "INSERT INTO segments (transcript_id, idx, start_sec, end_sec, text) VALUES ('t1', 0, 0, 1, 'a')"
        conn.execute(ins)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(ins)
