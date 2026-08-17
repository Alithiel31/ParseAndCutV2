"""
Tests des routes /process et /api/transcribe (app.routers.transcribe).

Aucun fichier audio réel n'est nécessaire : les fonctions qui appellent
FFmpeg (découper_audio) et l'API Groq (transcrire_chunk, client.chat.*)
sont mockées. On vérifie le comportement des routes et l'orchestration,
pas l'intégration réelle avec FFmpeg/Groq.

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


class TestProcessRouteValidation:
    def test_sans_fichier(self, client_app, monkeypatch):
        # Le client Groq doit être "prêt" pour dépasser la vérification 503
        # et atteindre la vérification de présence du fichier.
        monkeypatch.setattr(transcribe, "client", MagicMock())

        resp = client_app.post("/process")
        assert resp.status_code == 400

    def test_extension_refusee(self, client_app, monkeypatch):
        # Le client Groq doit être "prêt" pour dépasser la vérification 503
        # et atteindre la vérification d'extension.
        monkeypatch.setattr(transcribe, "client", MagicMock())

        files = {"audio": ("notes.txt", b"pas de l'audio", "text/plain")}
        resp = client_app.post("/process", files=files)
        assert resp.status_code == 415

    def test_groq_non_configure(self, client_app, monkeypatch):
        monkeypatch.setattr(transcribe, "client", None)

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/process", files=files)
        assert resp.status_code == 503


class TestProcessRouteFlow:
    """Simule le pipeline complet sans FFmpeg ni appel réseau réel."""

    def test_succes(self, client_app, monkeypatch, tmp_path):
        # Chunk factice sur disque (découper_audio est mocké, mais process()
        # doit pouvoir faire os.remove() dessus une fois "transcrit").
        fake_chunk = tmp_path / "chunk_0.mp3"
        fake_chunk.write_bytes(b"faux audio")

        monkeypatch.setattr(
            transcribe, "découper_audio", lambda *a, **k: [str(fake_chunk)]
        )
        monkeypatch.setattr(
            transcribe, "transcrire_chunk", lambda path, retries=2: "Texte transcrit. "
        )

        fake_groq_client = MagicMock()
        fake_completion = MagicMock()
        fake_completion.choices[0].message.content = "# Fiche générée"
        fake_groq_client.chat.completions.create.return_value = fake_completion
        monkeypatch.setattr(transcribe, "client", fake_groq_client)

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/process", files=files)

        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "summary"
        assert data["markdown"] == "# Fiche générée"
        assert data["stats"]["chunks"] == 1
        assert data["stats"]["transcription_chars"] > 0

    def test_succes_mode_transcript(self, client_app, monkeypatch, tmp_path):
        fake_chunk = tmp_path / "chunk_0.mp3"
        fake_chunk.write_bytes(b"faux audio")

        monkeypatch.setattr(
            transcribe, "découper_audio", lambda *a, **k: [str(fake_chunk)]
        )
        monkeypatch.setattr(
            transcribe, "transcrire_chunk", lambda path, retries=2: "Texte transcrit. "
        )

        fake_groq_client = MagicMock()
        monkeypatch.setattr(transcribe, "client", fake_groq_client)

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/process", files=files, data={"mode": "transcript"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "transcript"
        assert data["transcript"] == "Texte transcrit."
        assert "markdown" not in data
        assert data["stats"]["chunks"] == 1
        assert data["stats"]["transcription_chars"] > 0
        fake_groq_client.chat.completions.create.assert_not_called()

    def test_mode_invalide(self, client_app, monkeypatch):
        monkeypatch.setattr(transcribe, "client", MagicMock())

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/process", files=files, data={"mode": "bogus"})
        assert resp.status_code == 400

    def test_decoupage_echoue(self, client_app, monkeypatch):
        # découper_audio ne produit aucun chunk (fichier vide/corrompu)
        monkeypatch.setattr(transcribe, "découper_audio", lambda *a, **k: [])
        monkeypatch.setattr(transcribe, "client", MagicMock())

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/process", files=files)
        assert resp.status_code == 422

    def test_transcription_echoue(self, client_app, monkeypatch, tmp_path):
        fake_chunk = tmp_path / "chunk_0.mp3"
        fake_chunk.write_bytes(b"faux audio")

        monkeypatch.setattr(
            transcribe, "découper_audio", lambda *a, **k: [str(fake_chunk)]
        )

        def _raise(*a, **k):
            raise RuntimeError("Transcription échouée après 2 tentatives")

        monkeypatch.setattr(transcribe, "transcrire_chunk", _raise)
        monkeypatch.setattr(transcribe, "client", MagicMock())

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/process", files=files)
        assert resp.status_code == 502
