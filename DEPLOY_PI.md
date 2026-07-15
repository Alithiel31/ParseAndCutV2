# Déploiement sur le Raspberry Pi (docker context + cloudflared)

## 1. Créer le docker context vers le Pi

Depuis ta machine Windows (une seule fois) :

```bash
docker context create rpi --docker "host=ssh://<user>@<ip-du-pi>"
docker context use rpi
```

Vérifier que ça pointe bien sur le Pi :

```bash
docker context ls
docker info   # doit afficher l'OS/l'arch du Pi
```

## 2. Build + run

Depuis ce dossier (`ParseAndCutV2`), avec le context `rpi` actif :

```bash
docker compose up --build -d
```

Docker envoie le contexte de build (fichiers locaux des deux repos) au démon distant
du Pi — pas besoin de cloner quoi que ce soit sur le Pi. Le frontend sera exposé sur
le port **8091** du Pi (`http://<ip-du-pi>:8091`), le backend n'est joignable qu'en
interne via le réseau Docker (`backend:5000`).

Pour repasser en local ensuite : `docker context use default`.

## 3. Exposer via cloudflared

cloudflared tourne déjà sur le Pi. Éditer sa config du tunnel (généralement
`~/.cloudflared/config.yml`) pour ajouter une entrée d'ingress **avant** la règle
catch-all `service: http_status:404` :

```yaml
ingress:
  - hostname: parseandcut.alithiel31.dev
    service: http://localhost:8091
  # ... autres hostnames existants (ex: qcweather.alithiel31.dev) ...
  - service: http_status:404
```

Puis, sur le Pi :

```bash
cloudflared tunnel route dns <nom-du-tunnel> parseandcut.alithiel31.dev
sudo systemctl restart cloudflared
```

Vérifier que `https://parseandcut.alithiel31.dev` répond et que `/api/transcribe`
passe bien à travers le proxy nginx → backend.

## 4. Variables d'environnement

Le backend lit `.env` (déjà présent dans ce repo, non versionné) : `GROQ_API_KEY`,
`LANGUAGE`, `CHUNK_DURATION_SEC`, etc. Rien à changer pour le déploiement Pi, à part
vérifier que `GROQ_API_KEY` y est bien renseigné.
