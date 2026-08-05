from fastapi import APIRouter

from app.config import ALLOWED_EXTENSIONS, CHUNK_DURATION, LANGUAGE, client
from app.models.schemas import HealthResponse

router = APIRouter()


@router.get('/health', response_model=HealthResponse)
def health():
    """Endpoint de santé pour le monitoring."""
    return HealthResponse(
        status="ok",
        groq_ready=client is not None,
        language=LANGUAGE,
        chunk_duration_sec=CHUNK_DURATION,
        allowed_extensions=sorted(ALLOWED_EXTENSIONS)
    )
