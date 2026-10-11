# Développement local

🇬🇧 [English version](./development.md)

[Retour au README](../README.fr.md)

## Backend (port 5000)

Prérequis : Python 3.10 et FFmpeg (`ffmpeg -version`).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ".env exemple" .env     # puis renseigner GROQ_API_KEY
python -m app.main         # Uvicorn sur :5000
# ou, avec rechargement automatique :
uvicorn app.main:app --reload --port 5000
```

Le backend est une API pure : il ne sert aucun HTML. Sans Docker, lancer le frontend à côté (voir
plus bas). `.env exemple` fixe déjà `CORS_ORIGINS=http://localhost:5173` pour cette configuration.

### Routes

| Route                                      | Description                                                                                                                       |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| `GET /health`                              | État du service : `groq_ready`, langue par défaut, durée des chunks, extensions acceptées                                          |
| `POST /api/transcribe/start`               | Multipart `audio` + `mode` (`summary`/`transcript`) + `lang` (`fr`/`en`). Répond `202 {job_id}`                                   |
| `GET /api/transcribe/status/{job_id}`      | `processing` (étape et compteurs), `done` (résultat) ou l'erreur stockée. Un statut terminal n'est lisible qu'**une fois**        |
| `POST /api/recordings`                     | Crée un enregistrement par segments → `201 {recording_id, segment_seconds, max_segment_mb}`                                        |
| `GET /api/recordings/{id}`                 | Indices des segments déjà reçus et état de clôture (reprise après plantage)                                                       |
| `POST /api/recordings/{id}/segments/{n}`   | Envoie le segment `n` (idempotent). Répond les indices reçus jusqu'ici                                                            |
| `POST /api/recordings/{id}/finish`         | Vérifie que la suite est complète puis lance le job → `202 {job_id}` ; `409` + `missing` s'il manque des segments                 |
| `POST /api/recordings/{id}/cancel`         | Abandonne l'enregistrement et supprime son audio (sans effet une fois le traitement lancé)                                         |

Seules les méthodes `GET` et `POST` sont utilisées, car ce sont les seules autorisées par la config
CORS (`app/main.py`). FastAPI sert aussi sa documentation interactive sur `/docs` et `/redoc`, et le
document OpenAPI sur `/openapi.json`, quand on joint directement le backend (elles ne sont pas sous
`/api/`, nginx ne les expose donc pas).

```bash
curl -s localhost:5000/health
curl -s -F audio=@cours.mp3 -F mode=summary -F lang=fr localhost:5000/api/transcribe/start
curl -s "localhost:5000/api/transcribe/status/<job_id>?lang=fr"
```

### Codes d'erreur

| Code  | Signification                                                                              |
| ----- | ------------------------------------------------------------------------------------------ |
| `400` | Fichier absent, `lang`/`mode` invalide, indice de segment hors plage, enregistrement vide  |
| `404` | Job inconnu (jamais créé, déjà lu ou expiré) ou enregistrement inconnu                     |
| `409` | Segments manquants à `finish`, ou segment envoyé après la clôture de l'enregistrement      |
| `413` | Fichier, segment ou enregistrement au-delà de son plafond de taille                        |
| `415` | Extension audio non prise en charge                                                        |
| `422` | Audio illisible, enregistrement silencieux ou transcription vide                           |
| `429` | Limite de débit dépassée                                                                   |
| `502` | Erreur Groq (après réessais)                                                               |
| `503` | `GROQ_API_KEY` non configurée                                                              |
| `504` | Délai FFmpeg dépassé                                                                       |

Les erreurs ont la forme `{"detail": "…"}`, traduites selon `lang` (fr/en, catalogue dans
`app/i18n.py`). Un job en échec dont les premiers chunks ont été transcrits renvoie aussi
`partial_transcript`.

### Logs

Le backend journalise chaque étape en préfixant l'identifiant du job (`[job <id>] …`) : nombre de
chunks, progression de Whisper, mode de résumé et ratio final (durée audio ÷ temps de traitement).
Pour suivre un job signalé par un utilisateur :

```bash
docker compose logs backend | grep <job_id>
```

`scripts/benchmark_transcription.py` mesure ce ratio sur un ensemble d'enregistrements de test.

## Tests (backend)

```bash
pytest
```

| Fichier                    | Couvre                                                                                  |
| -------------------------- | --------------------------------------------------------------------------------------- |
| `test_transcribe.py`       | Validation de l'upload et chemins d'erreur de `/api/transcribe/start`                    |
| `test_transcribe_async.py` | Cycle de vie d'un job : démarrage, sondage, lecture unique, transcription partielle, traduction des erreurs |
| `test_recordings.py`       | Store de segments, idempotence, segments manquants, transcription anticipée, nettoyage   |
| `test_transcription.py`    | Appel Whisper, réessais, filtre d'hallucinations                                         |
| `test_summary.py`          | Résumé en une passe ou par blocs, découpe en blocs                                       |
| `test_audio.py`, `test_prompt.py`, `test_health.py` | Contrôle d'extension et détection de silence, prompts, `/health`   |
| `test_security.py`         | CORS par défaut, limitation de débit, plafond de taille d'upload                         |

Aucun test n'appelle Groq ni n'exige qu'FFmpeg réussisse : les deux sont simulés. `conftest.py`
force `RAILWAY_ENVIRONMENT` (un `.env` local et sa vraie clé API ne sont donc jamais chargés),
désactive par défaut la transcription anticipée (ses threads feraient varier l'ordre des appels
simulés) et réinitialise le limiteur entre les tests, le client de test partageant toujours la même
IP.

## Frontend (port 5173)

```bash
cd frontend
npm install
cp .env.example .env     # VITE_API_URL=http://localhost:5000
npm run dev
```

Ouvrir `http://localhost:5173`. Il n'y a pas de proxy Vite : le navigateur appelle Uvicorn
directement, d'où la nécessité que `CORS_ORIGINS` contienne `http://localhost:5173`. En production,
`VITE_API_URL` reste vide et nginx proxifie `/api/*`.

| Commande          | Effet                                                              |
| ----------------- | ------------------------------------------------------------------ |
| `npm run dev`     | Serveur de développement Vite (le service worker y est activé)     |
| `npm run build`   | `tsc -b` puis `vite build` → `dist/` avec manifeste et `sw.js`     |
| `npm run preview` | Sert le build                                                      |
| `npm run lint`    | oxlint                                                             |

Le frontend n'a pas de suite de tests : `tsc -b` (typage strict) et oxlint font office de filet, et
tournent tous deux en CI.

Tous les appels au backend passent par `frontend/src/api.ts`. Le service worker (`vite-plugin-pwa`,
`registerType: 'prompt'`) précache la coquille applicative, ne met jamais `/api/*` en cache
(`NetworkOnly`) et l'exclut du repli de navigation ; une bannière de mise à jour s'affiche quand une
nouvelle version est déployée.

## Intégration continue

Deux workflows tournent à chaque push et pull request vers `main` :

- **CI Lint** (`lint.yml`) — `flake8 app` (config dans `.flake8`, lignes de 120 caractères), puis,
  pour le frontend, `npm ci`, `oxlint` et `npm run build`.
- **CI Integration** (`integration.yml`) — installe FFmpeg, lance `pytest -v`, vérifie que
  `app.main` s'importe, puis **démarre l'application** et contrôle `/health` et le `400` de
  `/api/transcribe/start` sans fichier. La clé Groq vient du secret `GROQ_API_KEY`, ou d'une valeur
  factice quand le secret n'est pas exposé (pull requests Dependabot).

Android : `build-twa.yml` (sur modification de `frontend/twa-parseandcut/`, ou à la main) construit
le bundle signé ; `deploy-twa.yml` le publie sur Google Play une fois le build réussi. Dependabot
surveille chaque semaine pip, les deux arbres npm et les GitHub Actions.

Reproduire les contrôles avant de pousser :

```bash
flake8 app
pytest
cd frontend && npm run lint && npm run build
```

Un `.pre-commit-config.yaml` lance flake8 à chaque commit (`pre-commit install`).

## Docker et déploiement

```bash
docker compose up --build      # backend + frontend ; le frontend exige le réseau externe traefik-net
```

`docker-compose.yml` déclare `traefik-net` en `external: true` : sur une machine sans Traefik, le
créer d'abord (`docker network create traefik-net`). Aucun port d'hôte n'est publié ; on joint alors
le frontend par l'IP du conteneur, ou on ajoute un `ports:` dans sa copie locale. Pour lancer le
backend seul : `docker build -t meetup-killer . && docker run -p 5000:5000 --env-file .env meetup-killer`.

Pour la production, voir [DEPLOY_PI.md](./DEPLOY_PI.md) (docker context, Traefik, ingress
Cloudflare, Infisical).
