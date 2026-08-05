"""
Point d'entrée FastAPI. Backend API pur — le frontend (PWA) est un repo séparé
(ParseAndCutPWA) qui consomme cette API via /api/transcribe (cf. app/config.py CORS_ORIGINS).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS, PORT
from app.routers import health, transcribe

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(transcribe.router)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=PORT)
