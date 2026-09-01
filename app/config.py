"""
Configuration centrale : variables d'environnement, logging, client Groq.
"""
import os
import logging

from dotenv import load_dotenv
from groq import Groq

# --- LOGGING STRUCTURÉ ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
if not os.getenv("RAILWAY_ENVIRONMENT"):
    load_dotenv()

# --- CORS (pour le frontend PWA séparé, ex: ParseAndCutPWA) ---
# CORS_ORIGINS : liste d'origines séparées par des virgules (ex: "https://monapp.netlify.app,http://localhost:5173")
# Par défaut : le domaine de prod (same-origin via nginx). En dev local, surcharger
# avec l'origine Vite (ex: http://localhost:5173) via la variable d'env.
_cors_origins_env = os.getenv("CORS_ORIGINS", "https://parseandcut.alithiel31.dev")
CORS_ORIGINS = [o.strip() for o in _cors_origins_env.split(",")] if _cors_origins_env != "*" else ["*"]

# Extensions audio autorisées
ALLOWED_EXTENSIONS = {'mp3', 'mp4', 'wav', 'm4a', 'ogg', 'webm', 'flac', 'aac', 'opus'}

PORT             = int(os.getenv("PORT", 5000))
FFMPEG_PATH      = os.getenv("FFMPEG_PATH", "ffmpeg")
# Langue de sortie par défaut (fiche + messages d'erreur) si une requête
# n'envoie pas le champ `lang` (ex. anciens clients PWA en cache). Ne force
# plus la langue attendue par Whisper, qui auto-détecte toujours la langue
# parlée (voir app/services/transcription.py).
LANGUAGE         = os.getenv("LANGUAGE", "fr")
CHUNK_DURATION   = int(os.getenv("CHUNK_DURATION_SEC", 600))  # 10 min par chunk

# Taille max d'upload en Mo, vérifiée côté backend en plus du client_max_body_size
# de nginx (500 Mo) — protège le déploiement direct (dev, ou si nginx est contourné).
# Alignée sur le plafond réel de Cloudflare (Tunnel inclus) pour les requêtes
# proxyées : 100 Mo sur les plans Free/Pro. Un backend/nginx plus permissif ne
# sert à rien tant que Cloudflare bloque avant d'atteindre le Pi — un upload
# au-delà de cette taille reste silencieusement bloqué en amont, hors du
# contrôle de l'appli (passer à un plan Business/Enterprise lève ce plafond).
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", 100))

# Limite de requêtes sur /process (slowapi), au format "N/period" (ex: "5/minute").
# Protège les crédits Groq et les ressources du Raspberry Pi contre les abus anonymes.
RATE_LIMIT_PROCESS = os.getenv("RATE_LIMIT_PROCESS", "5/minute")

# --- INITIALISATION GROQ ---
api_key = os.environ.get("GROQ_API_KEY")
client  = None

if api_key:
    try:
        # 240s par appel, jusqu'à 2 tentatives sur timeout (transcrire_chunk) : ~480s
        # dans le pire cas pour un seul chunk. Le proxy Nginx en amont (frontend/
        # nginx.conf) laisse 600s pour absorber ce cas, plus quelques chunks
        # supplémentaires traités normalement.
        client = Groq(api_key=api_key, timeout=240.0)
        logger.info("✅ Groq Client initialisé")
    except Exception as e:
        logger.error(f"❌ Erreur init Groq: {e}")
else:
    logger.warning("⚠️ GROQ_API_KEY manquante")
