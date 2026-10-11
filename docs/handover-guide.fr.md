# Guide de reprise

🇬🇧 [English version](./handover-guide.md)

[Retour au README](../README.fr.md)

Meetup Killer (ParseAndCutV2) a un seul mainteneur réel (**Jacques Duchamplecheval**, alias GitHub
`Alithiel31`). Ce document existe pour qu'une autre personne — ou Jacques lui-même après une longue
coupure — puisse reprendre le projet sans devoir reconstituer de mémoire ce qui est documenté
ailleurs, dispersé, ou seulement connu du mainteneur. Il pointe vers la documentation existante
plutôt que de la dupliquer, et liste ce qu'il faut *avoir accès à* pour agir, pas seulement ce qu'il
faut *comprendre*.

---

## 1. Comprendre le projet — ordre de lecture recommandé

1. [README.fr.md](../README.fr.md) — vue d'ensemble, fonctionnalités, stack
2. [architecture.fr.md](./architecture.fr.md) — le modèle de job asynchrone, le pipeline, l'enregistrement par segments
3. [environment.fr.md](./environment.fr.md) — toutes les variables de configuration et constantes codées en dur
4. [development.fr.md](./development.fr.md) — lancer le projet en local, routes, codes d'erreur, tests, CI
5. [DEPLOY_PI.md](./DEPLOY_PI.md) — docker context, Traefik, ingress Cloudflare, Infisical
6. [Troubleshooting.fr.md](./Troubleshooting.fr.md), [SECURITY.fr.md](./SECURITY.fr.md), [CONTRIBUTING.fr.md](./CONTRIBUTING.fr.md)
7. [CHANGELOG.md](../CHANGELOG.md) — historique détaillé des décisions

---

## 2. Ce qui tourne, et où

| Composant              | Où                                                                       | Comment y accéder                                                                                                                        |
| ---------------------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Application            | `parseandcut.alithiel31.dev`                                             | Domaine public, HTTPS via un tunnel Cloudflare                                                                                            |
| Hébergement            | Un **Raspberry Pi** physique (nom d'hôte `Caesura`)                      | Accès réseau via **Tailscale**                                                                                                            |
| Conteneurs             | `docker-compose.yml` à la racine (`backend`, `frontend`)                 | `docker compose ps` sur le Pi, ou depuis une machine avec le docker context `rpi`                                                         |
| Reverse proxy          | **Traefik**, partagé avec les autres projets du Pi                       | Non géré par ce dépôt ; `frontend` rejoint son réseau `traefik-net` et porte les labels de routage                                         |
| Déploiement            | **Manuel** : `bash deploy.sh` depuis une machine dont le docker context vise le Pi | Pas de déploiement continu pour la partie web ; seul le build Android tourne dans GitHub Actions                              |
| Secrets (clé Groq)     | **Infisical**, projet *Shared Keys*, joint via Tailscale                 | `deploy.sh` utilise la Machine Identity `parseandcut-deploy` (rôle Viewer)                                                                |
| Domaine / tunnel       | `alithiel31.dev` — compte Cloudflare                                      | La règle d'ingress `cloudflared` est décrite dans [DEPLOY_PI.md](./DEPLOY_PI.md)                                                           |
| Application Android    | Package `dev.alithiel31.parseandcut` (Trusted Web Activity)              | `frontend/twa-parseandcut/`, workflows `build-twa.yml` / `deploy-twa.yml`                                                                 |

---

## 3. Secrets et accès nécessaires pour agir

Aucun secret réel n'est stocké dans ce dépôt (voir `.gitignore` et [SECURITY.fr.md](./SECURITY.fr.md)).
Pour reprendre le projet en pratique, il faut obtenir l'accès aux éléments suivants — **à compléter
par le mainteneur actuel** (gestionnaire de mots de passe utilisé, ou tout autre moyen de
transmission sécurisée) :

- **Accès administrateur au dépôt GitHub** [`Alithiel31/ParseAndCutV2`](https://github.com/Alithiel31/ParseAndCutV2) (secrets Actions, réglages des branches)
- **Un compte Groq** et la clé API (`GROQ_API_KEY`) — la facturation et les quotas sont le principal coût d'exploitation, voir [Risques](#5-risques-connus-à-garder-en-tête)
- **Accès à Infisical** — le projet *Shared Keys* et la Machine Identity `parseandcut-deploy`, dont le client id/secret vont dans `.infisical-identity.env` (modèle : `.infisical-identity.env.example`)
- **Compte Cloudflare** (tunnel et domaine `alithiel31.dev`)
- **Compte Tailscale** (chemin réseau vers le Raspberry Pi et vers Infisical)
- **Accès physique ou SSH au Raspberry Pi** qui héberge les conteneurs, Traefik et `cloudflared`
- **Keystore de signature Android** (`frontend/twa-parseandcut/*.keystore`, ignoré par git) et ses mots de passe, conservés dans les secrets du dépôt `KEYSTORE_BASE64`, `KEYSTORE_PASSWORD`, `KEY_PASSWORD`
- **Compte Google Play Console** et **compte de service** (`PLAY_SERVICE_ACCOUNT_JSON`) utilisé par `deploy-twa.yml`
- **Boîte courriel `contact@alithiel31.dev`** (signalements de sécurité, voir [SECURITY.fr.md](./SECURITY.fr.md))

> Sans le keystore Android et son mot de passe, l'application ne peut **pas** être remplacée par une
> nouvelle version : Google Play refuse un bundle signé par une clé différente. Sa perte est
> irréversible pour l'application déjà publiée.

---

## 4. Remettre le service en marche à partir de zéro

Si le Raspberry Pi est perdu ou remplacé mais que le code et les secrets ci-dessus sont disponibles :

1. Installer Docker et Docker Compose sur la nouvelle machine, ainsi que Tailscale.
2. Démarrer un **Traefik** partagé avec le provider Docker et un entrypoint `web` sur le port
   **8000**, puis créer le réseau : `docker network create traefik-net`.
3. Installer `cloudflared`, recréer le tunnel et ajouter la règle d'ingress
   `parseandcut.alithiel31.dev` vers `http://localhost:8000` (voir [DEPLOY_PI.md](./DEPLOY_PI.md),
   section 3), ainsi que sa route DNS.
4. Créer le docker context depuis le poste de travail (`docker context create rpi --docker "host=ssh://<user>@<ip>"`).
5. Reconstituer `.env` (à partir de `".env exemple"`) et `.infisical-identity.env`.
6. `bash deploy.sh` — il récupère `GROQ_API_KEY` dans Infisical et lance `docker compose up -d --build`.
7. Vérifier : `docker compose ps`, puis l'état du backend depuis l'intérieur du réseau :
   `docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:5000/health').read())"`
   doit indiquer `"groq_ready": true`. Terminer par un court envoi réel via le domaine public.

Si Infisical lui-même est injoignable, `GROQ_API_KEY` peut être exportée à la main avant
`docker compose up -d --build` — le fichier compose la lit dans l'environnement.

---

## 5. Risques connus à garder en tête

- **Mainteneur unique** — ce document réduit le risque mais ne le supprime pas ; envisager, à terme,
  de donner un accès en lecture à la liste des secrets à une seconde personne de confiance.
- **Dépendance à Groq** — la transcription (`whisper-large-v3`) et les résumés
  (`openai/gpt-oss-120b`) passent par un seul fournisseur. Un nom de modèle retiré ou un quota modifié
  casse le pipeline, et la clé API est une surface de coût : les limites de débit
  (`RATE_LIMIT_PROCESS`, `RATE_LIMIT_SEGMENTS`) et les plafonds de taille sont la seule protection
  contre l'abus par des utilisateurs anonymes.
- **Limites Cloudflare** — 100 s par réponse et 100 Mo par requête en Free/Pro. La première explique
  le traitement asynchrone ; la seconde plafonne `MAX_UPLOAD_SIZE_MB`.
- **Aucune persistance** — les jobs et les enregistrements en cours vivent dans le `/tmp` du
  conteneur. Un déploiement ou un redémarrage pendant une longue réunion perd la copie serveur (le
  navigateur garde sa copie locale et peut renvoyer les segments).
- **Point unique matériel** — l'hébergement dépend d'un Raspberry Pi personnel ; ni redondance ni plan
  de bascule.
- **Perte du keystore Android** — irréversible pour l'application déjà publiée (voir section 3).

---

## À compléter par le mainteneur

Les champs suivants sont volontairement laissés vides — ils touchent à des informations personnelles
ou à des identifiants qui n'ont pas leur place dans un dépôt :

- [ ] Où sont stockés les secrets listés en section 3 (gestionnaire de mots de passe, coffre-fort numérique…) et qui d'autre y a accès
- [ ] Registrar du domaine `alithiel31.dev` et identifiants du compte
- [ ] Personne(s) de confiance à contacter en cas d'indisponibilité prolongée du mainteneur
- [ ] Emplacement physique du Raspberry Pi et modalités d'accès en cas d'urgence
- [ ] État actuel de la fiche Google Play de `dev.alithiel31.parseandcut` (en test, publiée, pas encore créée)
