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
_cors_origins_env = os.getenv("CORS_ORIGINS", "*")
CORS_ORIGINS = [o.strip() for o in _cors_origins_env.split(",")] if _cors_origins_env != "*" else ["*"]

# Extensions audio autorisées
ALLOWED_EXTENSIONS = {'mp3', 'mp4', 'wav', 'm4a', 'ogg', 'webm', 'flac', 'aac', 'opus'}

PORT           = int(os.getenv("PORT", 5000))
FFMPEG_PATH    = os.getenv("FFMPEG_PATH", "ffmpeg")
LANGUAGE       = os.getenv("LANGUAGE", "fr")
CHUNK_DURATION = int(os.getenv("CHUNK_DURATION_SEC", 600))  # 10 min par chunk

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
