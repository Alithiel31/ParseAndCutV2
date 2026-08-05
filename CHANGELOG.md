# Changelog

All notable changes to this project are documented here.
Format inspired by [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). This project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### To do

- Add a `LICENSE` file (the `MIT` license is already declared in `package.json` but not versioned as a file)
- Tag the releases below retroactively (`v0.1.0` … `v0.4.0`) so GitHub Releases match this changelog
- Add English/French bilingual `README.md` review pass now that the format has changed from inline sections to separate files

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
