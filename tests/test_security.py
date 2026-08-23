"""
Tests des durcissements sécurité : CORS par défaut, rate limiting sur
/process, et limite de taille d'upload côté backend.

Lancer avec :  pytest
"""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import app.routers.transcribe as transcribe
from app.main import app


@pytest.fixture
def client_app():
    return TestClient(app)


class TestCorsDefault:
    def test_origine_autorisee_reflectee(self, client_app):
        resp = client_app.get(
            "/health", headers={"Origin": "https://parseandcut.alithiel31.dev"}
        )
        assert resp.headers.get("access-control-allow-origin") == "https://parseandcut.alithiel31.dev"

    def test_origine_non_autorisee_rejetee(self, client_app):
        resp = client_app.get("/health", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in resp.headers


class TestRateLimit:
    def test_depassement_rate_limit_sur_process(self, client_app):
        # RATE_LIMIT_PROCESS par défaut : 5/minute. Le statut exact des 5
        # premiers appels n'importe pas (client Groq non configuré en test) :
        # seul compte le fait que la 6e requête soit bloquée par le rate limit.
        for _ in range(5):
            resp = client_app.post("/process")
            assert resp.status_code != 429

        resp = client_app.post("/process")
        assert resp.status_code == 429


class TestRateLimitPerRealClientIp:
    def test_quota_par_ip_forwardee_pas_mutualise(self, client_app):
        # Le backend est toujours derrière un reverse proxy de confiance (nginx
        # sur le Pi, edge Railway) : sans ProxyHeadersMiddleware (app/main.py),
        # request.client.host vaudrait l'IP du proxy pour toutes les requêtes et
        # le quota 5/minute serait partagé par tous les visiteurs. On vérifie ici
        # que deux IP transmises via X-Forwarded-For ont bien des quotas distincts.
        for _ in range(5):
            resp = client_app.post("/process", headers={"X-Forwarded-For": "1.1.1.1"})
            assert resp.status_code != 429

        resp = client_app.post("/process", headers={"X-Forwarded-For": "1.1.1.1"})
        assert resp.status_code == 429

        resp_autre_ip = client_app.post("/process", headers={"X-Forwarded-For": "2.2.2.2"})
        assert resp_autre_ip.status_code != 429


class TestUploadSizeLimit:
    def test_fichier_trop_gros_rejete(self, client_app, monkeypatch):
        monkeypatch.setattr(transcribe, "client", MagicMock())
        monkeypatch.setattr(transcribe, "MAX_UPLOAD_SIZE_BYTES", 100)

        contenu = b"x" * 500  # dépasse largement la limite de test (100 octets)
        files = {"audio": ("cours.mp3", contenu, "audio/mpeg")}
        resp = client_app.post("/process", files=files)

        assert resp.status_code == 413
