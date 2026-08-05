from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    groq_ready: bool
    language: str
    chunk_duration_sec: int
    allowed_extensions: list[str]
