# Contribuer

🇬🇧 [English version](./CONTRIBUTING.md)

Merci de l'intérêt porté à ce projet. **Meetup Killer** est un backend FastAPI qui transcrit et structure des enregistrements audio via l'API Groq ; toute contribution qui corrige un bug, améliore le déploiement, ou améliore la documentation est la bienvenue.

## Avant de commencer

- Ouvrir une issue pour discuter du changement envisagé, sauf pour les corrections triviales (typo, lien cassé).
- Vérifier les items « À faire » du [`CHANGELOG.md`](./CHANGELOG.md) — l'idée est peut-être déjà planifiée.

## Environnement de développement

```bash
git clone https://github.com/Alithiel31/ParseAndCutV2.git
cd ParseAndCutV2
cp ".env exemple" .env
# renseigner GROQ_API_KEY (à obtenir sur https://console.groq.com/)

pip install -r requirements.txt
npm install
```

FFmpeg doit être installé localement (`ffmpeg -version`) pour lancer l'app hors Docker.

## Reproduire les vérifications de la CI en local

```bash
# Lint (Python, JS, CSS) — identique à .github/workflows/lint.yml
npm run lint
npm run lint:py    # flake8 meetupKiller.py
npm run lint:js    # eslint static/js/main.js
npm run lint:css   # stylelint static/css/style.css

# Tests unitaires
pytest

# Vérifications d'intégration — mêmes étapes que .github/workflows/integration.yml
python meetupKiller.py &
curl -sf http://127.0.0.1:5000/health
```

## Faire une Pull Request

1. Créer une branche depuis `main` (`git checkout -b fix/mon-changement`).
2. Committer avec un message clair, idéalement au format `type: description` (`fix:`, `feat:`, `docs:`, `chore:`...).
3. Mettre à jour [`CHANGELOG.md`](./CHANGELOG.md) dans la section `[Unreleased]` si le changement est notable pour un utilisateur.
4. Vérifier que les deux workflows CI passent (`CI Lint`, `CI Integration`).
5. Ouvrir la PR vers `main`.

## Releases

Les releases suivent le [Semantic Versioning](https://semver.org/) et sont taguées depuis `main` une fois la section `[Unreleased]` du `CHANGELOG.md` prête à être publiée :

1. Déplacer les entrées de `[Unreleased]` sous une nouvelle section `## [X.Y.Z] - AAAA-MM-JJ`.
2. Committer ce changement (`chore: release vX.Y.Z`).
3. Créer le tag et le pousser :

   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin main vX.Y.Z
   ```

4. Créer une Release GitHub depuis le tag, en y collant la section correspondante du `CHANGELOG.md`.

Guide de bump de version : **MAJOR** pour un changement cassant (variable d'env renommée, route supprimée...), **MINOR** pour une fonctionnalité rétrocompatible, **PATCH** pour un correctif ou un changement documentation seule.

## Signaler un problème

Voir [`Troubleshooting.md`](./Troubleshooting.md) avant d'ouvrir une issue — les incidents connus (chargement de variable d'env sur Railway, migration Docker/Pi) couvrent peut-être déjà le cas. Ne jamais coller de vraie valeur de `GROQ_API_KEY` dans une issue ; la masquer dans tout log ou config recopié.

## Secrets

Ne jamais committer `.env` ni aucune valeur réelle de `GROQ_API_KEY`. Seul le template `.env exemple` doit être versionné.
