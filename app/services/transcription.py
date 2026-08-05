"""
Transcription des chunks audio via l'API Groq Whisper.
"""
import os
import time

from groq import APIError, APITimeoutError

from app.config import LANGUAGE, client, logger


def transcrire_chunk(path: str, retries: int = 2) -> str:
    """
    Transcrit un chunk audio via Groq Whisper.
    Retente automatiquement avec backoff exponentiel en cas de timeout.
    2 tentatives max pour rester dans le timeout serveur (300s).
    """
    for attempt in range(retries):
        try:
            with open(path, "rb") as f:
                result = client.audio.transcriptions.create(
                    file=(os.path.basename(path), f.read()),
                    model="whisper-large-v3",
                    language=LANGUAGE,
                    response_format="text"
                )
            return result

        except APITimeoutError:
            wait = 2 ** attempt  # 1s puis 2s
            logger.warning(
                f"  Timeout chunk {os.path.basename(path)}, "
                f"tentative {attempt + 1}/{retries} — attente {wait}s"
            )
            time.sleep(wait)

        except APIError as e:
            logger.error(f"  Erreur API Groq (non récupérable): {e}")
            raise

    raise RuntimeError(
        f"Transcription échouée après {retries} tentatives pour {os.path.basename(path)}"
    )
