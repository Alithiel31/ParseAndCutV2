import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client_app():
    return TestClient(app)


class TestHealthRoute:
    def test_health_ok(self, client_app):
        resp = client_app.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "groq_ready" in data
        assert "allowed_extensions" in data
