FROM python:3.10-slim

# FFmpeg + nettoyage cache en une seule couche (réduit la taille de l'image)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1
# Évite d'écrire des .pyc inutiles
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Uvicorn sert l'application ASGI FastAPI (remplace Gunicorn+Flask)
CMD uvicorn meetupKiller:app --host 0.0.0.0 --port $PORT --workers 2
