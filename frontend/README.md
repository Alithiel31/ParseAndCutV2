# ParseAndCutPWA

Frontend PWA (React + Vite + TypeScript) pour [ParseAndCutV2](../ParseAndCutV2) — transcription et structuration de cours audio via l'API Groq (Whisper + Llama 3).

Ce projet consomme l'API JSON exposée par le backend FastAPI de ParseAndCutV2 (endpoint `POST /api/transcribe`). Il ne contient aucune logique de transcription : c'est uniquement l'interface, installable et fonctionnant partiellement hors-ligne (app shell mis en cache).

## Déploiement

En ligne : **https://parseandcut.alithiel31.dev**, auto-hébergé sur Raspberry Pi via Docker.

Le frontend (ce repo) et le backend ([ParseAndCutV2](../ParseAndCutV2)) tournent chacun
dans leur conteneur, orchestrés par le `docker-compose.yml` du repo backend. Le conteneur
nginx du frontend sert le build statique ET reverse-proxy `/api/*` vers le conteneur
backend (réseau Docker interne, `backend:5000`) — **same-origin**, pas de CORS à gérer.
Le tout est exposé via un tunnel Cloudflare (`cloudflared`), sans port ouvert sur le routeur.

## Démarrage

```bash
npm install
cp .env.example .env   # laisser VITE_API_URL vide en prod (same-origin via nginx)
npm run dev
```

## Build de production

```bash
npm run build
npm run preview
```

Génère `dist/` avec le manifest PWA (`manifest.webmanifest`) et le service worker (`sw.js`) via `vite-plugin-pwa` / Workbox.

## Variables d'environnement

| Variable | Description |
|---|---|
| `VITE_API_URL` | Vide en prod (same-origin via nginx). En dev local, pointer directement sur uvicorn : `http://localhost:5000`. |

## Déploiement (Docker)

Build et run se pilotent depuis [ParseAndCutV2](../ParseAndCutV2) (`docker-compose.yml`
y réunit les deux services). Depuis une machine avec Docker CLI configuré sur un
`docker context` pointant vers le Pi :

```bash
docker context use rpi
cd ../ParseAndCutV2
docker compose up --build -d
```

Voir `ParseAndCutV2/DEPLOY_PI.md` pour la procédure complète (création du context,
config de l'ingress cloudflared).

## Fonctionnement PWA

- App shell (HTML/CSS/JS/icônes) mis en cache par le service worker pour un chargement instantané et un fonctionnement hors-ligne de l'interface.
- Les appels à `/api/*` (transcription) ne sont **jamais** mis en cache (`NetworkOnly`) — la transcription nécessite toujours une connexion, car elle est déléguée à l'API Groq côté serveur.
- Bannière de mise à jour automatique quand une nouvelle version de l'app est déployée.
- Installable sur mobile/desktop (manifest + icônes 192/512 + apple-touch-icon).

## Android (TWA)

Publication prévue sur le Play Store sous forme de TWA. Package ID : `dev.alithiel31.parseandcut`
— sources et procédure dans [`twa-parseandcut/`](./twa-parseandcut).

## Structure

```
src/
  api.ts                  # client API (fetch vers le backend)
  App.tsx                 # état de l'app (upload, progression, résultat)
  components/
    DropZone.tsx           # zone de drag & drop / sélection fichier
    ProgressSteps.tsx       # badges d'étapes pendant le traitement
    ResultView.tsx          # rendu markdown du résultat + copie
    UpdateBanner.tsx        # bannière "nouvelle version disponible"
```
