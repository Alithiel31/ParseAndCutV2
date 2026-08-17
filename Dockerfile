FROM python:3.10-slim

# FFmpeg + nettoyage cache en une seule couche (réduit la taille de l'image)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1
# Évite d'écrire des .pyc inutiles
ENV PYTHONDONTWRITEBYTECODE=1
# Port par défaut (Railway le surchargeait via $PORT ; utile en local/Pi sans plateforme externe)
ENV PORT=5000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Utilisateur non-root : évite qu'un process compromis (ex: via FFmpeg) ait les
# droits root dans le conteneur. /tmp reste accessible en écriture par défaut.
RUN useradd --create-home --shell /bin/false appuser
USER appuser

# Uvicorn sert l'application ASGI FastAPI (remplace Gunicorn+Flask)
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
