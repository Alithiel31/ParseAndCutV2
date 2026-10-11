# Local development

🇫🇷 [Version française](./development.fr.md)

[Back to the README](../README.md)

## Backend (port 5000)

Prerequisites: Python 3.10 and FFmpeg (`ffmpeg -version`).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ".env exemple" .env     # then fill in GROQ_API_KEY
python -m app.main         # Uvicorn on :5000
# or, with auto-reload:
uvicorn app.main:app --reload --port 5000
```

The backend is an API only — it serves no HTML. Without Docker, run the frontend next to it (see
below). `.env exemple` already sets `CORS_ORIGINS=http://localhost:5173` for that setup.

### Routes

| Route                                      | Description                                                                                                                  |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| `GET /health`                              | Service status: `groq_ready`, default language, chunk duration, accepted extensions                                          |
| `POST /api/transcribe/start`               | Multipart `audio` + `mode` (`summary`/`transcript`) + `lang` (`fr`/`en`). Answers `202 {job_id}`                              |
| `GET /api/transcribe/status/{job_id}`      | `processing` (step and counters), `done` (result), or the stored error. A terminal status is readable **once**               |
| `POST /api/recordings`                     | Creates a segmented recording → `201 {recording_id, segment_seconds, max_segment_mb}`                                         |
| `GET /api/recordings/{id}`                 | Segment indices already received, and whether the recording is finished (resume after a crash)                               |
| `POST /api/recordings/{id}/segments/{n}`   | Uploads segment `n` (idempotent). Answers the indices received so far                                                        |
| `POST /api/recordings/{id}/finish`         | Checks the sequence is complete, then starts the job → `202 {job_id}`; `409` + `missing` if segments are absent              |
| `POST /api/recordings/{id}/cancel`         | Abandons the recording and deletes its audio (no effect once processing has started)                                         |

Only `GET` and `POST` are used, because they are the only methods the CORS configuration allows
(`app/main.py`). FastAPI also serves its interactive documentation on `/docs` and `/redoc`, and the
OpenAPI document on `/openapi.json`, when you reach the backend directly (they are not under
`/api/`, so nginx does not expose them).

```bash
curl -s localhost:5000/health
curl -s -F audio=@lecture.mp3 -F mode=summary -F lang=en localhost:5000/api/transcribe/start
curl -s "localhost:5000/api/transcribe/status/<job_id>?lang=en"
```

### Error codes

| Code  | Meaning                                                                                  |
| ----- | ---------------------------------------------------------------------------------------- |
| `400` | Missing file, invalid `lang`/`mode`, segment index out of range, empty recording         |
| `404` | Unknown job (never created, already read, or expired) or recording                       |
| `409` | Segments missing at `finish`, or a segment sent after the recording was finished         |
| `413` | File, segment or recording over its size cap                                             |
| `415` | Unsupported audio extension                                                              |
| `422` | Unreadable audio, silent recording, or empty transcription                               |
| `429` | Rate limit exceeded                                                                      |
| `502` | Groq error (after retries)                                                               |
| `503` | `GROQ_API_KEY` not configured                                                            |
| `504` | FFmpeg timed out                                                                         |

Errors have the shape `{"detail": "…"}`, translated according to `lang` (fr/en, catalogue in
`app/i18n.py`). A failed job whose first chunks were transcribed also returns `partial_transcript`.

### Logs

The backend logs every stage with the job id as a prefix (`[job <id>] …`): chunk count, Whisper
progress, summary mode, and the final ratio (audio duration ÷ processing time). To follow a job
reported by a user:

```bash
docker compose logs backend | grep <job_id>
```

`scripts/benchmark_transcription.py` measures that ratio over a set of test recordings.

## Tests (backend)

```bash
pytest
```

| File                       | Covers                                                                                  |
| -------------------------- | --------------------------------------------------------------------------------------- |
| `test_transcribe.py`       | Upload validation and the error paths of `/api/transcribe/start`                         |
| `test_transcribe_async.py` | Job life cycle: start, polling, single read, partial transcript, error translation       |
| `test_recordings.py`       | Segment store, idempotency, missing segments, early transcription, cleanup               |
| `test_transcription.py`    | Whisper call, retries, hallucination filter                                              |
| `test_summary.py`          | Single-pass vs block-wise summary, block splitting                                       |
| `test_audio.py`, `test_prompt.py`, `test_health.py` | Extension check and silence detection, prompts, `/health`    |
| `test_security.py`         | CORS defaults, rate limiting, upload size cap                                            |

No test calls Groq or needs FFmpeg to succeed: both are mocked. `conftest.py` forces
`RAILWAY_ENVIRONMENT` (so a local `.env` and its real API key are never loaded), turns early
transcription off by default (its threads would reorder the mocked calls), and resets the rate
limiter between tests since the test client always shares the same IP.

## Frontend (port 5173)

```bash
cd frontend
npm install
cp .env.example .env     # VITE_API_URL=http://localhost:5000
npm run dev
```

Open `http://localhost:5173`. There is no Vite proxy: the browser calls Uvicorn directly, which is
why `CORS_ORIGINS` must include `http://localhost:5173`. In production `VITE_API_URL` stays empty
and nginx proxies `/api/*`.

| Command           | What it does                                                    |
| ----------------- | --------------------------------------------------------------- |
| `npm run dev`     | Vite dev server (the service worker is enabled in development)  |
| `npm run build`   | `tsc -b` then `vite build` → `dist/` with manifest and `sw.js`  |
| `npm run preview` | Serves the build                                                |
| `npm run lint`    | oxlint                                                          |

The frontend has no test suite: `tsc -b` (strict type-check) and oxlint are its safety net, and both
run in CI.

All calls to the backend go through `frontend/src/api.ts`. The service worker (`vite-plugin-pwa`,
`registerType: 'prompt'`) precaches the app shell, never caches `/api/*` (`NetworkOnly`) and
excludes it from the navigation fallback; the user gets an update banner when a new version is
deployed.

## Continuous integration

Two workflows run on every push and pull request to `main`:

- **CI Lint** (`lint.yml`) — `flake8 app` (config in `.flake8`, line length 120), then for the
  frontend `npm ci`, `oxlint` and `npm run build`.
- **CI Integration** (`integration.yml`) — installs FFmpeg, runs `pytest -v`, checks that
  `app.main` imports, then **starts the app** and checks `/health` and the `400` of
  `/api/transcribe/start` without a file. The Groq key comes from the `GROQ_API_KEY` secret, or a
  dummy value when the secret is not exposed (Dependabot pull requests).

Android: `build-twa.yml` (on changes under `frontend/twa-parseandcut/`, or manually) builds the
signed bundle; `deploy-twa.yml` publishes it to Google Play once the build succeeds. Dependabot
watches pip, both npm trees and the GitHub Actions weekly.

Reproduce the checks before pushing:

```bash
flake8 app
pytest
cd frontend && npm run lint && npm run build
```

A `.pre-commit-config.yaml` runs flake8 on commit (`pre-commit install`).

## Docker and deployment

```bash
docker compose up --build      # backend + frontend; the frontend needs the external traefik-net network
```

`docker-compose.yml` declares `traefik-net` as `external: true`, so on a machine without Traefik
create it first (`docker network create traefik-net`) — nothing is published on a host port, so
you would then reach the frontend through the container IP, or add a `ports:` mapping to your
local copy. To run the backend alone: `docker build -t meetup-killer . && docker run -p 5000:5000
--env-file .env meetup-killer`.

For production, see [DEPLOY_PI.md](./DEPLOY_PI.md) (docker context, Traefik, Cloudflare ingress,
Infisical).
