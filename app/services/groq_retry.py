"""
Réessais communs à tous les appels à l'API Groq (Whisper et LLM).
"""
import time
from typing import Callable, Optional, TypeVar

from groq import (
    APIConnectionError,
    APIError,
    InternalServerError,
    RateLimitError,
)

from app.config import logger

T = TypeVar("T")

# Erreurs transitoires : réseau/timeout (APITimeoutError en hérite), quota
# dépassé (429) et erreurs serveur Groq (5xx). Tout le reste (clé invalide,
# fichier refusé…) échouera à l'identique à chaque essai, donc n'est jamais
# retenté.
ERREURS_TRANSITOIRES = (APIConnectionError, RateLimitError, InternalServerError)

MAX_TENTATIVES = 5
ATTENTE_MAX_SEC = 120  # plafond d'une attente, même si Groq demande plus


def delai_attente(exc: APIError, tentative: int) -> float:
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


def executer_avec_reessais(appel: Callable[[], T], description: str, retries: int = MAX_TENTATIVES) -> T:
    """Exécute `appel()` en retentant les erreurs transitoires (timeout, coupure
    réseau, 429, 5xx) en respectant le `retry-after` de Groq quand il est
    fourni, sinon avec backoff exponentiel. Le traitement tourne en tâche de
    fond (jobs asynchrones) : il n'y a plus de limite de réponse HTTP à
    respecter ici.

    Les autres erreurs de l'API sont relancées telles quelles ; après
    `retries` échecs transitoires, lève RuntimeError(description…).
    """
    dernière_erreur: Optional[Exception] = None

    for attempt in range(retries):
        try:
            return appel()

        except ERREURS_TRANSITOIRES as e:
            dernière_erreur = e
            if attempt + 1 >= retries:
                break
            wait = delai_attente(e, attempt)
            logger.warning(
                f"  {type(e).__name__} ({description}), "
                f"tentative {attempt + 1}/{retries} — attente {wait:.0f}s"
            )
            time.sleep(wait)

        except APIError as e:
            logger.error(f"  Erreur API Groq (non récupérable): {e}")
            raise

    raise RuntimeError(
        f"{description} : échec après {retries} tentatives ({type(dernière_erreur).__name__})"
    )
