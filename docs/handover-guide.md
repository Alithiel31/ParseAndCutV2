# Handover guide

🇫🇷 [Version française](./handover-guide.fr.md)

[Back to the README](../README.md)

Meetup Killer (ParseAndCutV2) has a single real maintainer (**Jacques Duchamplecheval**, GitHub
alias `Alithiel31`). This document exists so that someone else — or Jacques himself after a long
break — can take the project over without rebuilding from memory what is documented elsewhere,
scattered, or known only to the maintainer. It points to the existing documentation rather than
duplicating it, and lists what you need to *have access to* in order to act, not just to
*understand*.

---

## 1. Understanding the project — suggested reading order

1. [README.md](../README.md) — overview, features, stack
2. [architecture.md](./architecture.md) — the asynchronous job model, the pipeline, segmented recording
3. [environment.md](./environment.md) — every configuration variable and hard-coded constant
4. [development.md](./development.md) — run it locally, routes, error codes, tests, CI
5. [DEPLOY_PI.md](./DEPLOY_PI.md) — docker context, Traefik, Cloudflare ingress, Infisical
6. [Troubleshooting.md](./Troubleshooting.md), [SECURITY.md](./SECURITY.md), [CONTRIBUTING.md](./CONTRIBUTING.md)
7. [CHANGELOG.md](../CHANGELOG.md) — detailed history of the decisions

---

## 2. What runs, and where

| Component            | Where                                                                  | How to reach it                                                                                                                      |
| -------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Application          | `parseandcut.alithiel31.dev`                                           | Public domain, HTTPS through a Cloudflare Tunnel                                                                                      |
| Hosting              | A physical **Raspberry Pi** (host name `Caesura`)                      | Network access through **Tailscale**                                                                                                  |
| Containers           | `docker-compose.yml` at the root (`backend`, `frontend`)               | `docker compose ps` on the Pi, or from a machine with the `rpi` docker context                                                        |
| Reverse proxy        | **Traefik**, shared with the other projects of the Pi                  | Not managed by this repository; `frontend` joins its `traefik-net` network and carries the routing labels                              |
| Deployment           | **Manual**: `bash deploy.sh` from a machine whose docker context targets the Pi | There is no continuous deployment for the web part; only the Android build runs in GitHub Actions                              |
| Secrets (Groq key)   | **Infisical**, project *Shared Keys*, reached over Tailscale           | `deploy.sh` uses the `parseandcut-deploy` Machine Identity (Viewer role)                                                              |
| Domain / tunnel      | `alithiel31.dev` — Cloudflare account                                   | The `cloudflared` ingress rule is described in [DEPLOY_PI.md](./DEPLOY_PI.md)                                                         |
| Android application  | Package `dev.alithiel31.parseandcut` (Trusted Web Activity)            | `frontend/twa-parseandcut/`, workflows `build-twa.yml` / `deploy-twa.yml`                                                             |

---

## 3. Secrets and access needed to act

No real secret is stored in this repository (see `.gitignore` and [SECURITY.md](./SECURITY.md)).
To take the project over in practice you need access to the following — **to be completed by the
current maintainer** (password manager in use, or any other secure way of handing them over):

- **Administrator access to the GitHub repository** [`Alithiel31/ParseAndCutV2`](https://github.com/Alithiel31/ParseAndCutV2) (Actions secrets, branch settings)
- **A Groq account** and the API key (`GROQ_API_KEY`) — billing and quotas are the main operating cost, see [Risks](#5-known-risks-to-keep-in-mind)
- **Infisical access** — the *Shared Keys* project and the `parseandcut-deploy` Machine Identity whose client id/secret go into `.infisical-identity.env` (template: `.infisical-identity.env.example`)
- **Cloudflare account** (tunnel and domain `alithiel31.dev`)
- **Tailscale account** (network path to the Raspberry Pi and to Infisical)
- **Physical or SSH access to the Raspberry Pi** hosting the containers, Traefik and `cloudflared`
- **Android signing keystore** (`frontend/twa-parseandcut/*.keystore`, ignored by git) and its passwords, stored in the repository secrets `KEYSTORE_BASE64`, `KEYSTORE_PASSWORD`, `KEY_PASSWORD`
- **Google Play Console account** and the **service account** (`PLAY_SERVICE_ACCOUNT_JSON`) used by `deploy-twa.yml`
- **The mailbox `contact@alithiel31.dev`** (security reports, see [SECURITY.md](./SECURITY.md))

> Without the Android keystore and its password, the application **cannot** be replaced by a new
> version: Google Play rejects a bundle signed with a different key. Losing it is irreversible
> for the published application.

---

## 4. Bringing the service back from scratch

If the Raspberry Pi is lost or replaced but the code and the secrets above are available:

1. Install Docker and Docker Compose on the new machine, and Tailscale.
2. Start a shared **Traefik** with the Docker provider and an `web` entrypoint on port **8000**,
   and create the network: `docker network create traefik-net`.
3. Install `cloudflared`, recreate the tunnel and add the `parseandcut.alithiel31.dev` ingress rule
   pointing to `http://localhost:8000` (see [DEPLOY_PI.md](./DEPLOY_PI.md), section 3), plus its DNS route.
4. Create the docker context from your workstation (`docker context create rpi --docker "host=ssh://<user>@<ip>"`).
5. Restore `.env` (from `".env exemple"`) and `.infisical-identity.env`.
6. `bash deploy.sh` — it fetches `GROQ_API_KEY` from Infisical and runs `docker compose up -d --build`.
7. Verify: `docker compose ps`, then the backend status from inside the network:
   `docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:5000/health').read())"`
   should report `"groq_ready": true`. Finish with a short real upload through the public domain.

If Infisical itself is unreachable, `GROQ_API_KEY` can be exported by hand before
`docker compose up -d --build` — the compose file reads it from the environment.

---

## 5. Known risks to keep in mind

- **Single maintainer** — this document reduces the risk without removing it; consider eventually
  sharing read access to the list of secrets with a second trusted person.
- **Dependency on Groq** — transcription (`whisper-large-v3`) and summaries (`openai/gpt-oss-120b`)
  both go through one provider. A retired model name or a changed quota breaks the pipeline, and
  the API key is a cost surface: the rate limits (`RATE_LIMIT_PROCESS`, `RATE_LIMIT_SEGMENTS`) and
  the size caps are the only protection against abuse by anonymous users.
- **Cloudflare limits** — 100 s per response and 100 MB per request on Free/Pro. The first is why
  processing is asynchronous; the second caps `MAX_UPLOAD_SIZE_MB`.
- **No persistence** — jobs and in-progress recordings live in the container's `/tmp`. A deployment
  or a restart during a long meeting loses the server copy (the browser keeps its local copy and
  can resend the segments).
- **Single hardware point** — hosting depends on one personal Raspberry Pi; there is no redundancy
  or failover plan.
- **Loss of the Android keystore** — irreversible for the already published application (see section 3).

---

## To be completed by the maintainer

These fields are deliberately left empty — they concern personal information or credentials that do
not belong in a repository:

- [ ] Where the secrets listed in section 3 are stored (password manager, digital vault…) and who else can reach them
- [ ] Registrar of the domain `alithiel31.dev` and the account credentials
- [ ] Trusted person(s) to contact if the maintainer is unavailable for a long time
- [ ] Physical location of the Raspberry Pi and how to access it in an emergency
- [ ] Current state of the Google Play listing for `dev.alithiel31.parseandcut` (in testing, published, not yet created)
