-- Schéma initial : Document → Transcript → Segments → Notes, plus la file de jobs.
-- Horodatages : secondes epoch (REAL), comme l'ancien store de jobs (time.time()).
-- owner_id : point d'ancrage de la future authentification (voir app/auth.py).

CREATE TABLE documents (
    id                 TEXT PRIMARY KEY,
    owner_id           TEXT NOT NULL,
    title              TEXT NOT NULL DEFAULT '',
    source_filename    TEXT,
    audio_path         TEXT,
    audio_duration_sec REAL,
    lang               TEXT NOT NULL DEFAULT 'fr',
    status             TEXT NOT NULL DEFAULT 'processing'
                       CHECK (status IN ('processing', 'ready', 'error')),
    -- 1 = créé par l'ancien flux /api/transcribe/start : supprimé à la lecture du résultat
    ephemeral          INTEGER NOT NULL DEFAULT 0 CHECK (ephemeral IN (0, 1)),
    created_at         REAL NOT NULL,
    updated_at         REAL NOT NULL
);
CREATE INDEX idx_documents_owner_created ON documents (owner_id, created_at DESC);

CREATE TABLE jobs (
    id            TEXT PRIMARY KEY,
    document_id   TEXT NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    owner_id      TEXT NOT NULL,
    type          TEXT NOT NULL DEFAULT 'process',
    status        TEXT NOT NULL DEFAULT 'queued'
                  CHECK (status IN ('queued', 'running', 'done', 'error', 'cancelled')),
    step          TEXT CHECK (step IS NULL OR step IN
                  ('validating', 'converting', 'transcribing', 'structuring', 'finalizing')),
    progress      INTEGER NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    chunk_current INTEGER,
    chunk_total   INTEGER,
    options_json  TEXT NOT NULL DEFAULT '{}',
    error_code    TEXT,
    error_detail  TEXT,
    http_status   INTEGER,
    attempts      INTEGER NOT NULL DEFAULT 0,
    heartbeat_at  REAL,
    created_at    REAL NOT NULL,
    started_at    REAL,
    finished_at   REAL
);
CREATE INDEX idx_jobs_status_created ON jobs (status, created_at);
CREATE INDEX idx_jobs_document ON jobs (document_id);
CREATE INDEX idx_jobs_owner ON jobs (owner_id, created_at DESC);

CREATE TABLE transcripts (
    id          TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    provider    TEXT NOT NULL,
    model       TEXT,
    language    TEXT,
    full_text   TEXT NOT NULL DEFAULT '',
    created_at  REAL NOT NULL
);
CREATE INDEX idx_transcripts_document ON transcripts (document_id);

CREATE TABLE segments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    transcript_id TEXT NOT NULL REFERENCES transcripts (id) ON DELETE CASCADE,
    idx           INTEGER NOT NULL,
    start_sec     REAL NOT NULL,
    end_sec       REAL NOT NULL,
    speaker       TEXT,  -- NULL tant que la diarisation n'est pas implémentée (Phase 4)
    text          TEXT NOT NULL,
    UNIQUE (transcript_id, idx)
);

CREATE TABLE notes (
    id              TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    transcript_id   TEXT REFERENCES transcripts (id) ON DELETE SET NULL,
    format          TEXT NOT NULL DEFAULT 'markdown',
    content_md      TEXT NOT NULL,
    structured_json TEXT,
    provider        TEXT,
    model           TEXT,
    lang            TEXT,
    created_at      REAL NOT NULL
);
CREATE INDEX idx_notes_document ON notes (document_id);
