# Environment variables

🇫🇷 [Version française](./environment.fr.md)

[Back to the README](../README.md)

## Backend

Read by `app/config.py`. Locally, they come from a `.env` file (copy `".env exemple"`); in
production, everything except `GROQ_API_KEY` comes from that same `.env` and `GROQ_API_KEY` is
injected by `deploy.sh` (see below).

| Variable                        | Required | Default                              | Description                                                                                                                                                  |
| ------------------------------- | -------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `GROQ_API_KEY`                  | ✅       | —                                    | Groq API key ([console.groq.com](https://console.groq.com/)). Without it the server starts, `/health` reports `groq_ready: false` and every job start answers `503`. |
| `LANGUAGE`                      | ❌       | `fr`                                 | Default output language (`fr`/`en`) when a request omits `lang`. Does **not** force Whisper's input language, which always auto-detects.                       |
| `PORT`                          | ❌       | `5000`                               | Port the backend listens on (also used by the `CMD` of the `Dockerfile`).                                                                                    |
| `CHUNK_DURATION_SEC`            | ❌       | `600`                                | Length of one audio chunk sent to Whisper. 10 min at 128 kbps ≈ 9.6 MB, well below Groq's 25 MB limit.                                                       |
| `FFMPEG_PATH`                   | ❌       | `ffmpeg`                             | Path to the FFmpeg binary.                                                                                                                                   |
| `CORS_ORIGINS`                  | ❌       | `https://parseandcut.alithiel31.dev` | Comma-separated allowed origins, or `*`. Only relevant outside the nginx same-origin setup — set it to `http://localhost:5173` for local development.        |
| `MAX_UPLOAD_SIZE_MB`            | ❌       | `100`                                | Maximum upload size enforced by the backend (`413` above). Matches Cloudflare's own proxy ceiling on Free/Pro; nginx's `client_max_body_size` is looser (500 MB). |
| `RATE_LIMIT_PROCESS`            | ❌       | `5/minute`                           | Per-IP limit on starting a job and on creating/finishing a segmented recording. Format `N/period` (slowapi).                                                  |
| `RATE_LIMIT_SEGMENTS`           | ❌       | `60/minute`                          | Per-IP limit on segment uploads, one counter shared by all segments.                                                                                         |
| `RECORDING_SEGMENT_SEC`         | ❌       | `300`                                | Length of one recording segment, announced to the browser when a recording is created.                                                                        |
| `RECORDING_EARLY_TRANSCRIPTION` | ❌       | `1`                                  | Transcribe each segment as it arrives, while the meeting is still running. `0`, `false` or `no` processes everything at the end.                             |
| `MAX_SEGMENT_SIZE_MB`           | ❌       | `50`                                 | Maximum size of one uploaded segment (`413` above).                                                                                                           |
| `MAX_RECORDING_SIZE_MB`         | ❌       | `300`                                | Maximum cumulated size of all the segments of one recording (`413` above).                                                                                    |
| `MAX_SEGMENTS`                  | ❌       | `500`                                | Maximum number of segments in one recording (≈ 41 h at 5 min).                                                                                                |
| `RAILWAY_ENVIRONMENT`           | ❌       | —                                    | Legacy from the Railway hosting. When set to a non-empty value, `app/config.py` does **not** call `load_dotenv()`. CI and `conftest.py` use it to keep tests independent of a local `.env`. Do not set it in production. |
| `FLASK_DEBUG`                   | —        | —                                    | Listed in the README but **read nowhere in the code** (leftover from the Flask version). It has no effect.                                                    |

> Values that are not integers (for example `PORT=abc`) make the import of `app/config.py` fail
> with a `ValueError`, so the container exits at startup instead of running with a wrong setting.

### Constants that are not environment variables

These live in the code and need a code change (and a deployment) to move:

| Constant                                 | Where                        | Value                      |
| ---------------------------------------- | ---------------------------- | -------------------------- |
| Per-call Groq timeout                    | `app/config.py`              | 240 s                      |
| Retry attempts / maximum wait            | `app/services/groq_retry.py` | 5 / 120 s                  |
| Silence threshold                        | `app/services/audio.py`      | −70 dB                     |
| Single-pass summary threshold / block    | `app/services/summary.py`    | 30,000 / 20,000 characters |
| Stale job cleanup                        | `app/services/jobs.py`       | 2 h                        |
| Abandoned recording cleanup              | `app/services/recordings.py` | 6 h                        |
| Wait for early transcriptions at the end | `app/services/pipeline.py`   | 300 s                      |
| nginx `proxy_read_timeout`               | `frontend/nginx.conf`        | 600 s                      |

## Deployment secrets (`deploy.sh`)

`GROQ_API_KEY` is not stored on the Pi. It lives in Infisical (project **Shared Keys**, shared with
other services) and `deploy.sh` fetches it with a dedicated Machine Identity (`parseandcut-deploy`,
Viewer role) before running `docker compose up -d --build`.

| Variable                               | Where                                       | Description                         |
| -------------------------------------- | ------------------------------------------- | ----------------------------------- |
| `INFISICAL_UNIVERSAL_AUTH_CLIENT_ID`   | `.infisical-identity.env` (git-ignored)     | Client ID of the Machine Identity   |
| `INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET` | `.infisical-identity.env` (git-ignored)   | Client secret of the Machine Identity |

Copy `.infisical-identity.env.example` and fill it in to deploy from a new machine. The Infisical
domain, project id and environment (`prod`) are hard-coded at the top of `deploy.sh`.

## Frontend (build time)

| Variable       | Required | Default                 | Description                                                                                                                                                             |
| -------------- | -------- | ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VITE_API_URL` | ❌       | `""` (relative, in prod) | Backend base URL. **Leave empty in production**: nginx serves the app and proxies `/api/*`, so requests stay same-origin. Set `http://localhost:5000` to hit Uvicorn directly in development. |

It is embedded in the JavaScript bundle by Vite when the image is built — changing it requires a
rebuild, not a restart. `frontend/.env.example` ships the development value.

## GitHub Actions secrets (Android)

Used by `build-twa.yml` and `deploy-twa.yml` (see `frontend/twa-parseandcut/README.md`):

| Secret                      | Description                                                                         |
| --------------------------- | ----------------------------------------------------------------------------------- |
| `KEYSTORE_BASE64`           | Android signing keystore, base64-encoded                                            |
| `KEYSTORE_PASSWORD`         | Keystore password                                                                   |
| `KEY_PASSWORD`              | Signing key password                                                                |
| `PLAY_SERVICE_ACCOUNT_JSON` | Google Play service account used to publish the bundle                              |
| `GROQ_API_KEY`              | Optional. `integration.yml` falls back to a dummy key; no real Groq call is ever made in CI |
