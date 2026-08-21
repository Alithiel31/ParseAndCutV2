"""
Limiter partagé (slowapi) : instancié ici pour éviter un import circulaire
entre app.main (qui l'enregistre sur l'app FastAPI) et les routers (qui
l'utilisent comme décorateur sur leurs routes).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
