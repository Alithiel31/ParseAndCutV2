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

    def test_langue_invalide(self, client_app, monkeypatch):
        monkeypatch.setattr(transcribe, "client", MagicMock())

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/process", files=files, data={"lang": "de"})
        assert resp.status_code == 400

    def test_message_erreur_traduit_en_anglais(self, client_app, monkeypatch):
        monkeypatch.setattr(transcribe, "client", MagicMock())

        resp = client_app.post("/process", data={"lang": "en"})
        assert resp.status_code == 400
        assert resp.json()["detail"] == "No audio file received"

    def test_message_erreur_par_defaut_en_francais(self, client_app, monkeypatch):
        monkeypatch.setattr(transcribe, "client", MagicMock())

        resp = client_app.post("/process")
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Aucun fichier audio reçu"


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
            transcribe,
            "transcrire_chunk",
            lambda path, retries=2: (
                "Texte transcrit. ",
                [{"start": 0.0, "end": 1.5, "text": "Texte transcrit."}],
            ),
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
            transcribe,
            "transcrire_chunk",
            lambda path, retries=2: (
                "Texte transcrit. ",
                [{"start": 0.0, "end": 1.5, "text": "Texte transcrit."}],
            ),
        )

        fake_groq_client = MagicMock()
        monkeypatch.setattr(transcribe, "client", fake_groq_client)

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/process", files=files, data={"mode": "transcript"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "transcript"
        assert data["transcript"] == "[00:00] Texte transcrit."
        assert "markdown" not in data
        assert data["stats"]["chunks"] == 1
        assert data["stats"]["transcription_chars"] > 0
        fake_groq_client.chat.completions.create.assert_not_called()

    def test_mode_invalide(self, client_app, monkeypatch):
        monkeypatch.setattr(transcribe, "client", MagicMock())

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/process", files=files, data={"mode": "bogus"})
        assert resp.status_code == 400

    def test_succes_lang_anglais_propage_au_prompt(self, client_app, monkeypatch, tmp_path):
        fake_chunk = tmp_path / "chunk_0.mp3"
        fake_chunk.write_bytes(b"faux audio")

        monkeypatch.setattr(
            transcribe, "découper_audio", lambda *a, **k: [str(fake_chunk)]
        )
        monkeypatch.setattr(
            transcribe,
            "transcrire_chunk",
            lambda path, retries=2: (
                "Transcribed text. ",
                [{"start": 0.0, "end": 1.5, "text": "Transcribed text."}],
            ),
        )

        fake_groq_client = MagicMock()
        fake_completion = MagicMock()
        fake_completion.choices[0].message.content = "# Generated sheet"
        fake_groq_client.chat.completions.create.return_value = fake_completion
        monkeypatch.setattr(transcribe, "client", fake_groq_client)

        files = {"audio": ("class.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/process", files=files, data={"lang": "en"})

        assert resp.status_code == 200
        assert resp.json()["markdown"] == "# Generated sheet"
        sent_prompt = fake_groq_client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
        assert "Respond only in English" in sent_prompt

    def test_transcript_horodatage_decale_par_chunk(self, client_app, monkeypatch, tmp_path):
        # Deux chunks : le second doit être décalé de CHUNK_DURATION secondes
        # (les chunks font tous exactement CHUNK_DURATION, sauf le dernier).
        fake_chunk_0 = tmp_path / "chunk_0.mp3"
        fake_chunk_1 = tmp_path / "chunk_1.mp3"
        fake_chunk_0.write_bytes(b"faux audio 0")
        fake_chunk_1.write_bytes(b"faux audio 1")

        monkeypatch.setattr(
            transcribe,
            "découper_audio",
            lambda *a, **k: [str(fake_chunk_0), str(fake_chunk_1)],
        )
        monkeypatch.setattr(transcribe, "CHUNK_DURATION", 3600)  # 1h par chunk

        segments_par_chunk = {
            str(fake_chunk_0): ("Début. ", [{"start": 0.0, "end": 2.0, "text": "Début."}]),
            str(fake_chunk_1): ("Suite. ", [{"start": 5.0, "end": 7.0, "text": "Suite."}]),
        }
        monkeypatch.setattr(
            transcribe, "transcrire_chunk", lambda path, retries=2: segments_par_chunk[path]
        )
        monkeypatch.setattr(transcribe, "client", MagicMock())

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/process", files=files, data={"mode": "transcript"})

        assert resp.status_code == 200
        data = resp.json()
        # Chunk 1 : offset de 3600s (1h) + 5s -> 1:00:05
        assert data["transcript"] == "[00:00] Début.\n[1:00:05] Suite."

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


class TestApiTranscribeRoute:
    """/api/transcribe est un alias de /process (même vue FastAPI) — on
    revérifie ici les cas clés pour garantir que l'alias reste fonctionnel
    et cohérent avec /process."""

    def test_sans_fichier(self, client_app, monkeypatch):
        monkeypatch.setattr(transcribe, "client", MagicMock())

        resp = client_app.post("/api/transcribe")
        assert resp.status_code == 400

    def test_extension_refusee(self, client_app, monkeypatch):
        monkeypatch.setattr(transcribe, "client", MagicMock())

        files = {"audio": ("notes.txt", b"pas de l'audio", "text/plain")}
        resp = client_app.post("/api/transcribe", files=files)
        assert resp.status_code == 415

    def test_groq_non_configure(self, client_app, monkeypatch):
        monkeypatch.setattr(transcribe, "client", None)

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/api/transcribe", files=files)
        assert resp.status_code == 503

    def test_mode_invalide(self, client_app, monkeypatch):
        monkeypatch.setattr(transcribe, "client", MagicMock())

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/api/transcribe", files=files, data={"mode": "bogus"})
        assert resp.status_code == 400

    def test_succes(self, client_app, monkeypatch, tmp_path):
        fake_chunk = tmp_path / "chunk_0.mp3"
        fake_chunk.write_bytes(b"faux audio")

        monkeypatch.setattr(
            transcribe, "découper_audio", lambda *a, **k: [str(fake_chunk)]
        )
        monkeypatch.setattr(
            transcribe,
            "transcrire_chunk",
            lambda path, retries=2: (
                "Texte transcrit. ",
                [{"start": 0.0, "end": 1.5, "text": "Texte transcrit."}],
            ),
        )

        fake_groq_client = MagicMock()
        fake_completion = MagicMock()
        fake_completion.choices[0].message.content = "# Fiche générée"
        fake_groq_client.chat.completions.create.return_value = fake_completion
        monkeypatch.setattr(transcribe, "client", fake_groq_client)

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/api/transcribe", files=files)

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
            transcribe,
            "transcrire_chunk",
            lambda path, retries=2: (
                "Texte transcrit. ",
                [{"start": 0.0, "end": 1.5, "text": "Texte transcrit."}],
            ),
        )

        fake_groq_client = MagicMock()
        monkeypatch.setattr(transcribe, "client", fake_groq_client)

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/api/transcribe", files=files, data={"mode": "transcript"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "transcript"
        assert data["transcript"] == "[00:00] Texte transcrit."
        fake_groq_client.chat.completions.create.assert_not_called()

    def test_decoupage_echoue(self, client_app, monkeypatch):
        monkeypatch.setattr(transcribe, "découper_audio", lambda *a, **k: [])
        monkeypatch.setattr(transcribe, "client", MagicMock())

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/api/transcribe", files=files)
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
        resp = client_app.post("/api/transcribe", files=files)
        assert resp.status_code == 502
