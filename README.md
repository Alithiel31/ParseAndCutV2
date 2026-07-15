# 🎓 Meetup Killer — Assistant de Cours IA

[![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-blue?logo=docker)](https://www.docker.com/)
[![Groq](https://img.shields.io/badge/Powered%20by-Groq-orange)](https://groq.com/)
[![Déployé](https://img.shields.io/badge/Déployé-parseandcut.alithiel31.dev-blue)](https://parseandcut.alithiel31.dev)
[![Cloudflare](https://img.shields.io/badge/Tunnel-Cloudflare-orange?logo=cloudflare)](https://www.cloudflare.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 🚀 **Service en ligne** : [parseandcut.alithiel31.dev](https://parseandcut.alithiel31.dev)

---

## 🇫🇷 Français

### À propos

**Meetup Killer** transforme vos enregistrements audio de cours ou de réunions en fiches de révision structurées au format Markdown.

Conçu pour tourner sur **Raspberry Pi**, il est déployé via **Docker** (conteneur backend + conteneur frontend [ParseAndCutPWA](../ParseAndCutPWA), orchestrés par `docker-compose.yml`), exposé publiquement via un **tunnel Cloudflare** — aucun port ouvert sur le routeur. Le traitement lourd est délégué à l'API **Groq** pour des performances maximales :

- **Transcription** : Whisper Large V3 — précision maximale, multilingue
- **Structuration** : Llama 3.3 (70B) — résumé, titres, définitions en Markdown

### Fonctionnalités

| Fonctionnalité | Détail |
|---|---|
| 🎙️ Transcription longue durée | Découpage automatique en chunks de 10 min — **supporte les audios > 1h** |
| 🧠 Fiche structurée | Résumé, titres hiérarchiques, mots-clés en gras, blocs définition |
| 🌐 Interface moderne | Drag & drop, barre de progression par étape, affichage des stats |
| ✅ Validation robuste | Vérification type + taille côté client ET serveur |
| 🔁 Retry automatique | Relance Whisper en cas de timeout réseau (backoff exponentiel) |
| 🐳 Docker ready | FFmpeg + Gunicorn pré-configurés, image légère `python:3.10-slim` |
| 📊 Endpoint `/health` | Monitoring : état Groq, langue, extensions supportées |

### Formats audio supportés

`mp3` · `mp4` · `wav` · `m4a` · `ogg` · `webm` · `flac` · `aac` · `opus`

### Architecture
```
Audio (upload)
    │
    ▼
[Validation] → type, taille, extension
    │
    ▼
[FFmpeg] → découpage en chunks de 10 min
    │
    ▼
[Groq Whisper Large V3] → transcription chunk par chunk
    │
    ▼
[Groq Llama 3.3 70B] → structuration Markdown
    │
    ▼
Fiche de révision ✅
```

### Variables d'environnement

| Variable | Obligatoire | Défaut | Description |
|---|---|---|---|
| `GROQ_API_KEY` | ✅ | — | Clé API Groq |
| `LANGUAGE` | ❌ | `fr` | Langue de transcription Whisper |
| `CHUNK_DURATION_SEC` | ❌ | `600` | Durée des chunks en secondes |
| `FFMPEG_PATH` | ❌ | `ffmpeg` | Chemin vers le binaire FFmpeg |
| `FLASK_DEBUG` | ❌ | `false` | Mode debug (dev uniquement) |

### Installation locale

1. **Cloner le dépôt**
```bash
   git clone https://github.com/Alithiel31/meetup-killer.git
   cd meetup-killer
```

2. **Configurer le `.env`**
```env
   GROQ_API_KEY=votre_cle_api
   LANGUAGE=fr
   # Optionnel :
   # CHUNK_DURATION_SEC=600
```

3. **Lancer avec Docker**
```bash
   docker build -t meetup-killer .
   docker run -d -p 8080:8080 --name meetup-app --env-file .env meetup-killer
```

4. **Accéder à l'outil**

   Ouvrez [http://localhost:8080](http://localhost:8080)

   > Sur Raspberry Pi, remplacez `localhost` par l'IP locale de votre machine.

### Déploiement (Docker + Raspberry Pi)

C'est la méthode utilisée en production. Le `docker-compose.yml` de ce dépôt lance le
backend (réseau interne, port **5000**) et le frontend [ParseAndCutPWA](../ParseAndCutPWA)
(nginx, port **8091**) — voir [`DEPLOY_PI.md`](./DEPLOY_PI.md) pour la procédure complète
(création du `docker context` vers le Pi, build, configuration de l'ingress Cloudflare).

```bash
docker context use rpi
docker compose up --build -d
```

Nginx (conteneur frontend) sert les fichiers statiques du PWA et reverse-proxy `/api/`
vers le backend — same-origin, pas de CORS à gérer. Le tunnel Cloudflare gère le HTTPS
et le nom de domaine `parseandcut.alithiel31.dev` — aucun certificat à gérer manuellement.

L'endpoint [`/health`](https://parseandcut.alithiel31.dev/api/health) permet de vérifier l'état du service à tout moment.

---

## 🇬🇧 English

### About

**Meetup Killer** converts audio recordings of lectures or meetings into structured Markdown study notes.

Built to run on a **Raspberry Pi**, it is deployed via **Docker** (backend container + frontend container [ParseAndCutPWA](../ParseAndCutPWA), orchestrated by `docker-compose.yml`), exposed publicly through a **Cloudflare Tunnel** — no port forwarding needed. Heavy processing is offloaded to the **Groq API**:

- **Transcription**: Whisper Large V3 — maximum accuracy, multilingual
- **Structuring**: Llama 3.3 (70B) — summary, headings, keywords, definition blocks

### Features

| Feature | Detail |
|---|---|
| 🎙️ Long audio support | Auto-split into 10-min chunks — **handles recordings over 1 hour** |
| 🧠 Structured notes | Summary, hierarchical headings, bold keywords, definition blocks |
| 🌐 Modern UI | Drag & drop, step-by-step progress bar, processing stats |
| ✅ Robust validation | File type + size checked both client-side and server-side |
| 🔁 Auto retry | Whisper retried on network timeout with exponential backoff |
| 🐳 Docker ready | FFmpeg + Gunicorn pre-configured, lightweight `python:3.10-slim` image |
| 📊 `/health` endpoint | Monitoring: Groq status, language, supported formats |

### Supported formats

`mp3` · `mp4` · `wav` · `m4a` · `ogg` · `webm` · `flac` · `aac` · `opus`

### Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | ✅ | — | Groq API key |
| `LANGUAGE` | ❌ | `fr` | Whisper transcription language |
| `CHUNK_DURATION_SEC` | ❌ | `600` | Chunk duration in seconds |
| `FFMPEG_PATH` | ❌ | `ffmpeg` | Path to FFmpeg binary |
| `FLASK_DEBUG` | ❌ | `false` | Debug mode (dev only) |

### Local setup

1. **Clone the repository**
```bash
   git clone https://github.com/Alithiel31/meetup-killer.git
   cd meetup-killer
```

2. **Create your `.env` file**
```env
   GROQ_API_KEY=your_api_key
   LANGUAGE=fr
```

3. **Run with Docker**
```bash
   docker build -t meetup-killer .
   docker run -d -p 8080:8080 --name meetup-app --env-file .env meetup-killer
```

4. **Open the app** at [http://localhost:8080](http://localhost:8080)

   > On Raspberry Pi, replace `localhost` with your device's local IP address.

### Deployment (Docker + Raspberry Pi)

This is the production setup. This repo's `docker-compose.yml` runs the backend
(internal network, port **5000**) and the [ParseAndCutPWA](../ParseAndCutPWA) frontend
(nginx, port **8091**) — see [`DEPLOY_PI.md`](./DEPLOY_PI.md) for the full procedure
(creating the `docker context` to the Pi, building, configuring the Cloudflare ingress).

```bash
docker context use rpi
docker compose up --build -d
```

Nginx (frontend container) serves the PWA static files and reverse-proxies `/api/` to
the backend — same-origin, no CORS to manage. The Cloudflare Tunnel handles HTTPS and
the `parseandcut.alithiel31.dev` domain name — no certificate to manage manually.

Check the [`/health`](https://parseandcut.alithiel31.dev/api/health) endpoint anytime to verify service status.

---

## Stack

| Couche | Technologie |
|---|---|
| Backend | FastAPI + Uvicorn · Python 3.10 |
| Audio | FFmpeg |
| IA | Groq API — Whisper Large V3 + Llama 3.3 70B |
| Frontend | [ParseAndCutPWA](../ParseAndCutPWA) — React + Vite (PWA) |
| Infra | Docker · Raspberry Pi · Cloudflare Tunnel |