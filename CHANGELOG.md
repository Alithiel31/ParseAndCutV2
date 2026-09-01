# Changelog

All notable changes to this project are documented here.
Format inspired by [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). This project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- French/English UI language support: a `lang` field (`fr`/`en`, default `fr`) on `/process` and
  `/api/transcribe` drives the LLM structuring prompt's output language and the localized HTTP
  error messages (`app/i18n.py`); Whisper transcription now always auto-detects the spoken
  language (`language=None`), decoupled from the requested output language. The frontend gets a
  language switcher (header, persisted in `localStorage`, defaults to the browser's language on
  first visit) translating the whole UI, including the CGU/privacy policy/legal notice pages
- Local notifications: an opt-in "notify me when done" checkbox on the home page triggers a
  device notification via `ServiceWorkerRegistration.showNotification()` once a transcription
  finishes — useful if the tab is backgrounded or the screen is locked while waiting. No server
  push/VAPID/subscription storage involved, purely client-side
- Rate limiting on `/process` and `/api/transcribe` (`slowapi`, default `5/minute` per IP,
  configurable via `RATE_LIMIT_PROCESS`) to protect Groq API credits and the Raspberry Pi from
  anonymous abuse
- Explicit server-side upload size limit (`MAX_UPLOAD_SIZE_MB`, default 100), enforced by
  streaming the upload to disk in chunks and aborting past the limit — previously only nginx's
  `client_max_body_size` (500 MB) bounded upload size. The 100 MB default matches Cloudflare's own
  request size ceiling on Free/Pro plans for traffic proxied through it (Tunnel included): a
  larger file is silently dropped by Cloudflare before ever reaching the Pi, so a more permissive
  backend/nginx limit only delays the failure instead of preventing it — see
  [`docs/Troubleshooting.md`](./docs/Troubleshooting.md)
- `.github/dependabot.yml`: weekly dependency update PRs for pip, npm (root and `frontend/`)
  and GitHub Actions
- `docs/SECURITY.md` / `docs/SECURITY.fr.md`: vulnerability disclosure policy
- Docker image now runs as a non-root `appuser` instead of root

### Changed

- `CORS_ORIGINS` now defaults to `https://parseandcut.alithiel31.dev` instead of `*` — the
  wildcard let any third-party site's JavaScript call the public API directly through visitors'
  browsers; local dev still overrides it to the Vite origin
- `LANGUAGE` env var now means the *default output language* used when a request omits `lang`
  (e.g. an old cached PWA client), not the language forced onto Whisper's transcription
- `/health`'s `language` field renamed to `default_language` to match `LANGUAGE`'s new meaning

## [1.1.0] - 2026-08-17

### Added

- A `mode` option (`summary` or `transcript`) on `/process` and `/api/transcribe`, exposed in
  the UI as a choice between the AI-structured study sheet (unchanged default) and the raw
  Whisper transcript. Selecting `transcript` skips the LLM structuring call entirely
- Per-segment timestamps (`[mm:ss]`, or `[h:mm:ss]` past one hour) on the raw transcript
  (`mode=transcript`), using Groq Whisper's `verbose_json` response format
- Legal pages served by the PWA at `/cgu`, `/politique-de-confidentialite` and
  `/mentions-legales`, plus a footer linking to them. The privacy policy documents the only
  third party the audio reaches (Groq, in the United States), the fact that uploads are deleted
  at the end of each request, and the absence of accounts, cookies and analytics — it also
  provides the public URL the Play Store listing requires
- `react-router-dom` and a `pages/` directory: `App.tsx` becomes the shared layout (header,
  footer, service-worker update banner, scroll reset) and the transcription view moves to
  `pages/Home.tsx`
- `LICENSE` file (MIT, already declared in `package.json` but not versioned until now)

### Fixed

- Long URLs no longer widen the page on narrow screens (`overflow-wrap` on links and inline
  code inside `.markdown-body`)
- `/process` and `/api/transcribe` returning 500 on any platform without a `/tmp` directory
  (Windows) — temp file paths were hardcoded instead of using `tempfile.gettempdir()`
- The AI structuring call (`mode=summary`) failing with a 502 since Groq deprecated
  `llama-3.3-70b-versatile` — replaced by `openai/gpt-oss-120b`
- `mode=transcript` returning 500 on real (non-mocked) transcriptions — the Groq SDK returns
  Whisper's `verbose_json` segments as raw dicts, not attribute-accessible objects
- Uploads over 1 MB rejected with a 413, and long transcriptions with a 504, due to Nginx's
  default `client_max_body_size` and `proxy_read_timeout` — both raised in `nginx.conf`
- Nginx's `proxy_read_timeout`/`proxy_send_timeout` raised from 300s to 600s: the Groq client
  timeout (240s per call) combined with `transcrire_chunk`'s up-to-2 retries on timeout could
  reach ~480s for a single chunk, leaving too little headroom under the previous 300s budget

### Security

- The generated notes are now sanitized with DOMPurify before being injected into the page.
  `marked` dropped its `sanitize` option in v5, so raw HTML in the Markdown reached the DOM
  untouched — and that Markdown comes from the LLM, hence indirectly from the uploaded audio.
  A payload such as `<img src=x onerror=…>` executed in the page; it no longer does, and the
  legitimate Markdown rendering is unchanged

## [1.0.0] - 2026-08-05

Monorepo release: the backend is restructured into a layered (MVC-style) package, and the
frontend PWA is merged into this repository. Breaking change on the deployment side (embedded
UI route removed, entry point renamed) — no change to the public JSON API (`/health`,
`/api/transcribe`, `/process`).

### Added

- `app/` package replacing the single-file `meetupKiller.py`: `config.py` (env vars, logging,
  Groq client), `models/schemas.py` (Pydantic models), `services/` (`audio.py`,
  `transcription.py`, `prompt.py`), `routers/` (`health.py`, `transcribe.py`), `main.py`
  (FastAPI app + CORS + router wiring)
- `frontend/` — the PWA (React + Vite + TWA scaffold), copied in from the former
  `ParseAndCutPWA` repository so the whole project now lives in a single place
- `docs/` folder grouping `CONTRIBUTING.md`/`.fr.md`, `Troubleshooting.md`/`.fr.md` and
  `DEPLOY_PI.md`
- `.dockerignore` (root and `frontend/`): excludes `.git`, `node_modules`, `frontend/`
  (from the backend context) and dev-only files, fixing a very slow `docker compose build`
  caused by the backend context otherwise including the whole `frontend/node_modules` tree

### Changed

- Tests split to mirror the new backend structure: `tests/test_audio.py`,
  `tests/test_prompt.py`, `tests/test_health.py`, `tests/test_transcribe.py`
  (replacing `tests/test_meetupkiller.py`)
- `Dockerfile` entry point: `uvicorn meetupKiller:app` → `uvicorn app.main:app`
- `docker-compose.yml` frontend build context: absolute path to the external
  `ParseAndCutPWA` repo → relative `./frontend`
- `requirements.txt`: dropped `jinja2` (no more server-rendered templates)
- CI workflows (`lint.yml`, `integration.yml`) updated for the new layout; JS/CSS linting
  steps removed (no static assets left to lint in this repo)
- `Troubleshooting.en.md` / `Troubleshooting.md` renamed to `Troubleshooting.md` /
  `Troubleshooting.fr.md` to match the `.md` = English / `.fr.md` = French convention
  already used by `README`/`CONTRIBUTING`
- Documentation links updated across `README.md`/`.fr.md` and the GitHub issue templates

### Removed

- `meetupKiller.py`, `templates/`, `static/` — the legacy server-rendered UI and its routes
  (`GET /`, `/static/*`); the PWA in `frontend/` is now the only frontend

## [0.5.0] - 2026-08-05

Documentation release: no change to the application itself.

### Added

- Bilingual `README.md` (English, main) / `README.fr.md` (French), replacing the previous single file with inline FR/EN sections — table of contents, architecture diagram, stack & skills section
- `CONTRIBUTING.md` / `CONTRIBUTING.fr.md`: dev environment, how to reproduce CI checks locally, PR format, and the release/tagging procedure below
- `CHANGELOG.md`, reconstructed from the git history (Flask → FastAPI migration, Railway → Docker/Pi migration)
- `Troubleshooting.md` / `Troubleshooting.en.md`: the `GROQ_API_KEY` loading issue on Railway, reconstructed from the `c37f8ba`/`db7cfa6` commits
- GitHub issue forms (`.github/ISSUE_TEMPLATE/`): bug report, change/improvement request, and links to the troubleshooting notes

## [0.4.0] - 2026-07-14

Backend rewrite and move to self-hosted deployment: Railway is dropped in favor of Docker on a Raspberry Pi, fronted by a Cloudflare Tunnel. The frontend becomes a separate PWA repository ([ParseAndCutPWA](../ParseAndCutPWA)), also packaged as an Android TWA.

### Added

- Docker Compose orchestration (`docker-compose.yml`): backend container (FastAPI, internal network) + frontend container (nginx serving [ParseAndCutPWA](../ParseAndCutPWA), reverse-proxying `/api/*`)
- `DEPLOY_PI.md`: full Raspberry Pi deployment procedure (`docker context`, build, Cloudflare Tunnel ingress configuration)
- TWA (Trusted Web Activity) scaffold for packaging the PWA as an Android app
- `CORS_ORIGINS` environment variable for local dev (Vite on `:5173` calling Uvicorn on `:5000`) — not needed in production since nginx serves same-origin

### Changed

- Migrated the backend from Flask to **FastAPI + Uvicorn**, with Pydantic response models (`/health`) and `UploadFile` for uploads
- CI workflow split in two (`ab6124c`): linting (`lint.yml`) and integration tests (`integration.yml`) now run as separate jobs instead of one
- Dependency versions pinned in `requirements.txt`
- `PORT` moved into `.env` instead of being hardcoded

## [0.3.0] - 2026-03-26

### Changed

- General refactor of `meetupKiller.py` for efficiency (`c11d5c5`)
- Linter issues fixed (`e23a4f5`) and CI workflow reworked (`b87eb2e`)

## [0.2.0] - 2026-03-06

Backend hardening after production incidents on Railway — see [`Troubleshooting.en.md`](./Troubleshooting.en.md).

### Added

- GitHub Actions workflow (`tests.yml`, later split into `lint.yml`/`integration.yml`) running lint and route tests on every push/PR
- Defensive initialization of the Groq client: the app no longer crashes on boot when `GROQ_API_KEY` is missing or not yet visible to the process — `/process` now returns a clear `503` instead

### Fixed

- `GROQ_API_KEY` intermittently unavailable to the Python process on Railway at boot time — worked around by reading the key with `os.environ.get` instead of `os.getenv` and deferring the Groq client instantiation instead of failing at import time (`c37f8ba`, `db7cfa6`)
- `main.js` fixes on the upload/progress flow (`3be4d40`)

## [0.1.0] - 2026-02-27 to 2026-03-05

### Added

- First working version: Flask backend, Whisper (via Groq) transcription, Llama 3 structuring into Markdown
- Initial `README.md` with project details and setup instructions
- Railway hosting environment configuration
