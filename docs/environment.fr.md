# Variables d'environnement

🇬🇧 [English version](./environment.md)

[Retour au README](../README.fr.md)

## Backend

Lues par `app/config.py`. En local, elles viennent d'un fichier `.env` (copier `".env exemple"`) ;
en production, tout vient de ce même `.env` sauf `GROQ_API_KEY`, injectée par `deploy.sh` (voir
plus bas).

| Variable                        | Obligatoire | Défaut                               | Description                                                                                                                                                  |
| ------------------------------- | ----------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `GROQ_API_KEY`                  | ✅          | —                                    | Clé API Groq ([console.groq.com](https://console.groq.com/)). Sans elle, le serveur démarre, `/health` indique `groq_ready: false` et tout démarrage de job répond `503`. |
| `LANGUAGE`                      | ❌          | `fr`                                 | Langue de sortie par défaut (`fr`/`en`) quand une requête omet `lang`. Ne force **pas** la langue d'entrée de Whisper, qui auto-détecte toujours.             |
| `PORT`                          | ❌          | `5000`                               | Port d'écoute du backend (repris par le `CMD` du `Dockerfile`).                                                                                              |
| `CHUNK_DURATION_SEC`            | ❌          | `600`                                | Durée d'un chunk audio envoyé à Whisper. 10 min à 128 kbit/s ≈ 9,6 Mo, très en dessous de la limite de 25 Mo de Groq.                                        |
| `FFMPEG_PATH`                   | ❌          | `ffmpeg`                             | Chemin du binaire FFmpeg.                                                                                                                                    |
| `CORS_ORIGINS`                  | ❌          | `https://parseandcut.alithiel31.dev` | Origines autorisées séparées par des virgules, ou `*`. Ne compte qu'hors du same-origin nginx — à régler sur `http://localhost:5173` en développement local.  |
| `MAX_UPLOAD_SIZE_MB`            | ❌          | `100`                                | Taille maximale d'upload imposée par le backend (`413` au-delà). Alignée sur le plafond de Cloudflare en Free/Pro ; le `client_max_body_size` de nginx est plus large (500 Mo). |
| `RATE_LIMIT_PROCESS`            | ❌          | `5/minute`                           | Limite par IP sur le démarrage d'un job et sur la création/clôture d'un enregistrement par segments. Format `N/period` (slowapi).                            |
| `RATE_LIMIT_SEGMENTS`           | ❌          | `60/minute`                          | Limite par IP sur l'envoi des segments, un compteur unique partagé par tous les segments.                                                                    |
| `RECORDING_SEGMENT_SEC`         | ❌          | `300`                                | Durée d'un segment d'enregistrement, annoncée au navigateur à la création de l'enregistrement.                                                               |
| `RECORDING_EARLY_TRANSCRIPTION` | ❌          | `1`                                  | Transcrire chaque segment dès son arrivée, pendant que la réunion continue. `0`, `false` ou `no` traite tout à la fin.                                       |
| `MAX_SEGMENT_SIZE_MB`           | ❌          | `50`                                 | Taille maximale d'un segment envoyé (`413` au-delà).                                                                                                         |
| `MAX_RECORDING_SIZE_MB`         | ❌          | `300`                                | Taille cumulée maximale de tous les segments d'un enregistrement (`413` au-delà).                                                                            |
| `MAX_SEGMENTS`                  | ❌          | `500`                                | Nombre maximal de segments d'un enregistrement (≈ 41 h à 5 min).                                                                                             |
| `RAILWAY_ENVIRONMENT`           | ❌          | —                                    | Héritage de l'hébergement Railway. Quand elle a une valeur non vide, `app/config.py` n'appelle **pas** `load_dotenv()`. La CI et `conftest.py` s'en servent pour rendre les tests indépendants d'un `.env` local. Ne pas la définir en production. |
| `FLASK_DEBUG`                   | —           | —                                    | Citée dans le README mais **lue nulle part dans le code** (reliquat de la version Flask). Sans effet.                                                        |

> Une valeur non entière (par exemple `PORT=abc`) fait échouer l'import de `app/config.py` avec une
> `ValueError` : le conteneur s'arrête au démarrage au lieu de tourner avec un mauvais réglage.

### Constantes qui ne sont pas des variables d'environnement

Elles vivent dans le code : les changer demande une modification et un déploiement.

| Constante                                     | Où                           | Valeur                      |
| --------------------------------------------- | ---------------------------- | --------------------------- |
| Timeout par appel Groq                        | `app/config.py`              | 240 s                       |
| Tentatives / attente maximale                 | `app/services/groq_retry.py` | 5 / 120 s                   |
| Seuil de silence                              | `app/services/audio.py`      | −70 dB                      |
| Seuil de résumé en une passe / taille de bloc | `app/services/summary.py`    | 30 000 / 20 000 caractères  |
| Nettoyage des jobs périmés                    | `app/services/jobs.py`       | 2 h                         |
| Nettoyage d'un enregistrement abandonné       | `app/services/recordings.py` | 6 h                         |
| Attente des transcriptions anticipées         | `app/services/pipeline.py`   | 300 s                       |
| `proxy_read_timeout` de nginx                 | `frontend/nginx.conf`        | 600 s                       |

## Secrets de déploiement (`deploy.sh`)

`GROQ_API_KEY` n'est pas stockée sur le Pi. Elle vit dans Infisical (projet **Shared Keys**, partagé
avec d'autres services) et `deploy.sh` la récupère avec une Machine Identity dédiée
(`parseandcut-deploy`, rôle Viewer) avant de lancer `docker compose up -d --build`.

| Variable                                 | Où                                         | Description                          |
| ---------------------------------------- | ------------------------------------------ | ------------------------------------ |
| `INFISICAL_UNIVERSAL_AUTH_CLIENT_ID`     | `.infisical-identity.env` (ignoré par git) | Client ID de la Machine Identity     |
| `INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET` | `.infisical-identity.env` (ignoré par git) | Client secret de la Machine Identity |

Copier `.infisical-identity.env.example` et le remplir pour déployer depuis une nouvelle machine.
Le domaine Infisical, l'identifiant du projet et l'environnement (`prod`) sont écrits en dur en
tête de `deploy.sh`.

## Frontend (au build)

| Variable       | Obligatoire | Défaut                      | Description                                                                                                                                                                         |
| -------------- | ----------- | --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VITE_API_URL` | ❌          | `""` (relative, en prod)    | URL de base du backend. **À laisser vide en production** : nginx sert l'app et proxifie `/api/*`, les requêtes restent en same-origin. `http://localhost:5000` pour viser Uvicorn directement en développement. |

Elle est embarquée dans le bundle JavaScript par Vite à la construction de l'image : la changer
demande un rebuild, pas un simple redémarrage. `frontend/.env.example` fournit la valeur de
développement.

## Secrets GitHub Actions (Android)

Utilisés par `build-twa.yml` et `deploy-twa.yml` (voir `frontend/twa-parseandcut/README.md`) :

| Secret                      | Description                                                                              |
| --------------------------- | ---------------------------------------------------------------------------------------- |
| `KEYSTORE_BASE64`           | Keystore de signature Android, encodé en base64                                          |
| `KEYSTORE_PASSWORD`         | Mot de passe du keystore                                                                 |
| `KEY_PASSWORD`              | Mot de passe de la clé de signature                                                      |
| `PLAY_SERVICE_ACCOUNT_JSON` | Compte de service Google Play utilisé pour publier le bundle                             |
| `GROQ_API_KEY`              | Facultatif. `integration.yml` se rabat sur une fausse clé ; aucun vrai appel Groq n'est fait en CI |
