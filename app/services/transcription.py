"""
Transcription des chunks audio via l'API Groq Whisper.
"""
import os
import time
from typing import Optional

from groq import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

from app.config import client, logger

# Erreurs transitoires : réseau/timeout, quota dépassé (429) et erreurs serveur
# Groq (5xx). Tout le reste (clé invalide, fichier refusé…) échouera à
# l'identique à chaque essai, donc n'est jamais retenté.
_ERREURS_TRANSITOIRES = (APIConnectionError, RateLimitError, InternalServerError)

MAX_TENTATIVES = 5
ATTENTE_MAX_SEC = 120  # plafond d'une attente, même si Groq demande plus


def _delai_attente(exc: APIError, tentative: int) -> float:
    """Délai avant la prochaine tentative : `retry-after` de Groq s'il est
    fourni (cas d'un 429), sinon backoff exponentiel (1s, 2s, 4s…). Plafonné à
    ATTENTE_MAX_SEC pour qu'un job ne reste pas bloqué indéfiniment."""
    retry_after: Optional[str] = None
    response = getattr(exc, "response", None)
    if response is not None:
        retry_after = response.headers.get("retry-after")
    try:
        delai = float(retry_after) if retry_after is not None else 2 ** tentative
    except ValueError:
        delai = 2 ** tentative
    return min(max(delai, 1.0), ATTENTE_MAX_SEC)


def transcrire_chunk(path: str, retries: int = MAX_TENTATIVES) -> tuple[str, list[dict]]:
    """
    Transcrit un chunk audio via Groq Whisper.
    Retente automatiquement (timeout, coupure réseau, 429, 5xx) en respectant
    le `retry-after` de Groq quand il est fourni, sinon avec backoff
    exponentiel. Le traitement tourne en tâche de fond (jobs asynchrones) :
    il n'y a plus de limite de réponse HTTP à respecter ici.

    La langue parlée est toujours auto-détectée par Whisper (language=None),
    indépendamment de la langue de sortie choisie par l'utilisateur pour la
    fiche générée (voir app.services.prompt) : ce sont deux réglages
    indépendants.

    Retourne (texte_complet, segments) où segments est la liste des
    passages horodatés : [{"start": float, "end": float, "text": str}, ...]
    (temps en secondes, relatifs au début de ce chunk).
    """
    nom = os.path.basename(path)
    dernière_erreur: Optional[Exception] = None

    for attempt in range(retries):
        try:
            with open(path, "rb") as f:
                result = client.audio.transcriptions.create(
                    file=(nom, f.read()),
                    model="whisper-large-v3",
                    language=None,
                    response_format="verbose_json"
                )
            # "segments" n'est pas un champ typé du modèle Transcription du SDK Groq
            # (extra="allow") : c'est du JSON brut désérialisé en dicts, pas en objets.
            segments = [
                {"start": seg["start"], "end": seg["end"], "text": seg["text"].strip()}
                for seg in result.segments
            ]
            return result.text, segments

        except (APITimeoutError, *_ERREURS_TRANSITOIRES) as e:
            dernière_erreur = e
            if attempt + 1 >= retries:
                break
            wait = _delai_attente(e, attempt)
            logger.warning(
                f"  {type(e).__name__} sur le chunk {nom}, "
                f"tentative {attempt + 1}/{retries} — attente {wait:.0f}s"
            )
            time.sleep(wait)

        except APIError as e:
            logger.error(f"  Erreur API Groq (non récupérable): {e}")
            raise

    raise RuntimeError(
        f"Transcription échouée après {retries} tentatives pour {nom} "
        f"({type(dernière_erreur).__name__})"
    )
