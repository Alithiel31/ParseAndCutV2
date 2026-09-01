# Troubleshooting

🇫🇷 [Version française](./Troubleshooting.fr.md)

This document goes back over a real incident hit during the project's first hosting setup (Railway), reconstructed from the git history (`c37f8ba`, `db7cfa6`, `bdd1e6d`). The commit messages from that time are terse; what follows describes what is confirmed by the code diff versus what remains a hypothesis.

---

## 1. `GROQ_API_KEY` invisible to the Python process on Railway

### Symptom

On startup on Railway, the Groq API key was not being read correctly by the application: the boot log showed the error defined in the code at the time (`CRITICAL ERROR: GROQ_API_KEY is not set in environment variables.`) even though the variable was correctly configured on the Railway dashboard.

### What was tried

The code was changed in several successive passes (commits `db7cfa6` "deploy troubleshooting" then `c37f8ba` "troubleshooting railway"):

1. Switched from `os.getenv("GROQ_API_KEY")` to `os.environ.get("GROQ_API_KEY")` to read the key.
2. Added a log printing the first 5 characters of the key when it is read successfully, to visually confirm in the Railway logs that the variable reaches the process.
3. **Defensive Groq client initialization**: the client is no longer instantiated at module load time when the key is missing — the app no longer crashes on boot, and a missing client is handled explicitly in the `/process` route (a clear error is returned instead of a crash).

```python
# before
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("CRITICAL ERROR: GROQ_API_KEY is not set in environment variables.")
    client = None
else:
    print(f"Succès : Clé chargée (début: {api_key[:5]})")
client = Groq(api_key=api_key)  # instantiated even if the key is empty!

# after
api_key = os.environ.get("GROQ_API_KEY")
client = None
if api_key:
    try:
        client = Groq(api_key=api_key)
        print(f"✅ Groq Client initialisé (Clé: {api_key[:5]}...)")
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation Groq: {e}")
else:
    print("⚠️ WARNING: GROQ_API_KEY est toujours invisible pour Python.")
```

### Root cause

**Not conclusively confirmed in the available history.** The diff fixes a real logic bug (`client = Groq(api_key=api_key)` was executed even inside the `if not api_key` branch, which could raise an unhandled exception at module load time and crash the app before it even reached the routes). Whether the Railway variable itself was being propagated incorrectly to the process (propagation delay, wrong environment/service targeted) is not documented with certainty — only the defensive code fix is traced.

### What resolved it

No longer instantiating `Groq(...)` unconditionally removed the boot crash, regardless of the exact root cause on Railway's side. The project later moved off Railway to a self-hosted Docker + Raspberry Pi deployment (see [`DEPLOY_PI.md`](./DEPLOY_PI.md)), which no longer depends on a third-party platform injecting environment variables.

### Note for the current deployment

On the current Docker/Pi deployment, `GROQ_API_KEY` is read from the local `.env` file via `docker-compose.yml` (`env_file: .env`) — a different, more direct mechanism, which has not reproduced this issue since the migration.

---

## 2. Large uploads (>100 MB) hang indefinitely behind Cloudflare

### Symptom

Uploading a large audio file (e.g. 174 MB) through the public domain
(`parseandcut.alithiel31.dev`, behind Cloudflare Tunnel) leaves the UI stuck on the "Transcription
Whisper…" step indefinitely. `docker compose logs -f backend` never shows a `📥 Fichier reçu` line
for that request, and `docker compose logs -f frontend` (nginx access log) never shows the
matching `POST /api/transcribe` either — the request never reaches the Pi at all. A small file
(a few MB) through the exact same code path completes normally in a few seconds.

### Root cause

Cloudflare enforces its own maximum request body size for any traffic proxied through its edge —
Tunnel included, since a Tunnel has no public IP to bypass the proxy with a DNS-only record. That
ceiling is **100 MB on Free and Pro plans**, 200 MB on Business, 500 MB+ on Enterprise (see
[Cloudflare's upload limits docs](https://developers.cloudflare.com/cache/concepts/default-cache-behavior/#upload-limits)).
Before this was diagnosed, `MAX_UPLOAD_SIZE_MB` (backend) and the frontend's own size check had
both been raised to 300 MB, letting users pick and start uploading files Cloudflare would then
silently drop before they ever reached nginx or the backend — with no error surfaced to the user,
just an indefinitely spinning progress indicator.

### What resolved it

`MAX_UPLOAD_SIZE_MB` and the frontend's `MAX_SIZE_MB` were both brought back down to **100 MB**,
matching the actual Cloudflare Free/Pro ceiling, so oversized files are rejected immediately with
a clear error instead of silently hanging.

### Note for the current deployment

Nginx's own `client_max_body_size` (500 MB, `frontend/nginx.conf`) is deliberately left higher —
it isn't the binding constraint here and doesn't need to track Cloudflare's limit. If a higher
upload ceiling is ever needed, the only real options are upgrading the Cloudflare plan (Business →
200 MB) or splitting the upload into smaller chunks client-side; unproxying the domain (DNS-only)
is not compatible with Cloudflare Tunnel.

---

## Reporting a new problem

If your issue is not the one documented above, open an issue using the provided template. Include the relevant logs (`docker logs <container>` in prod, console output locally) and never paste a real `GROQ_API_KEY` value.
