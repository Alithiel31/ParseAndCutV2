# Contributing

🇫🇷 [Version française](./CONTRIBUTING.fr.md)

Thanks for your interest in this project. **Meetup Killer** is a FastAPI backend that transcribes and structures audio recordings via the Groq API; any contribution that fixes a bug, improves the deployment, or improves the documentation is welcome.

## Before you start

- Open an issue to discuss the change you have in mind, except for trivial fixes (typo, broken link).
- Check the "To do" items in [`CHANGELOG.md`](./CHANGELOG.md) — your idea may already be planned.

## Development environment

```bash
git clone https://github.com/Alithiel31/ParseAndCutV2.git
cd ParseAndCutV2
cp ".env exemple" .env
# fill in GROQ_API_KEY (get one at https://console.groq.com/)

pip install -r requirements.txt
npm install
```

FFmpeg must be installed locally (`ffmpeg -version`) to run the app outside Docker.

## Reproducing the CI checks locally

```bash
# Linting (Python) — same as .github/workflows/lint.yml
npm run lint
npm run lint:py    # flake8 app

# Unit tests
pytest

# Integration checks — same steps as .github/workflows/integration.yml
python -m app.main &
curl -sf http://127.0.0.1:5000/health
```

## Opening a Pull Request

1. Create a branch from `main` (`git checkout -b fix/my-change`).
2. Commit with a clear message, ideally in the `type: description` format (`fix:`, `feat:`, `docs:`, `chore:`...).
3. Update [`CHANGELOG.md`](./CHANGELOG.md) in the `[Unreleased]` section if the change is notable for a user.
4. Check that both CI workflows pass (`CI Lint`, `CI Integration`).
5. Open the PR against `main`.

## Releases

Releases follow [Semantic Versioning](https://semver.org/) and are cut from `main` once the `[Unreleased]` section of `CHANGELOG.md` is ready to ship:

1. Move the `[Unreleased]` entries under a new `## [X.Y.Z] - YYYY-MM-DD` heading.
2. Commit that change (`chore: release vX.Y.Z`).
3. Tag it and push the tag:

   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin main vX.Y.Z
   ```

4. Create a GitHub Release from the tag, pasting in the matching `CHANGELOG.md` section.

Version bump guide: **MAJOR** for a breaking API/config change (env var renamed, route removed...), **MINOR** for a backward-compatible feature, **PATCH** for a fix or docs-only change.

## Reporting a problem

Check [`Troubleshooting.md`](./Troubleshooting.md) before opening an issue — known incidents (Railway env var loading, Docker/Pi migration) may already cover it. Never paste a real `GROQ_API_KEY` in an issue; redact it from any log or config you copy in.

## Secrets

Never commit `.env` or any real value of `GROQ_API_KEY`. Only the `.env exemple` template should be versioned.
