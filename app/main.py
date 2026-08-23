"""
Point d'entrée FastAPI. Backend API pur — le frontend (PWA) est un repo séparé
(ParseAndCutPWA) qui consomme cette API via /api/transcribe (cf. app/config.py CORS_ORIGINS).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.config import CORS_ORIGINS, PORT
from app.limiter import limiter
from app.routers import health, transcribe

app = FastAPI()

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(transcribe.router)

# Le backend n'est jamais exposé directement à Internet : sur le Pi, nginx
# (frontend/nginx.conf) reverse-proxy same-origin vers ce service via le réseau
# Docker interne (aucun port publié dans docker-compose.yml) ; sur Railway, seule
# la couche d'edge de la plateforme peut atteindre le conteneur. Sans ce
# middleware, request.client.host — utilisé comme clé par le rate limiter
# (app/limiter.py) — vaudrait toujours l'IP du proxy amont pour toutes les
# requêtes : un seul quota partagé par tous les utilisateurs au lieu d'un quota
# par IP réelle. trusted_hosts="*" est sûr ici car seul ce proxy de confiance
# peut parler au conteneur.
app = ProxyHeadersMiddleware(app, trusted_hosts="*")


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=PORT)
