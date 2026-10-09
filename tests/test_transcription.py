"""
Tests unitaires de transcrire_chunk (app.services.transcription).

Le SDK Groq ne type que le champ `text` du modèle Transcription ; en
verbose_json, `segments` arrive en extra="allow" et est donc du JSON brut
désérialisé en dicts (pas en objets avec attributs). On simule fidèlement
cette forme, car test_transcribe.py mocke transcrire_chunk en entier et ne
peut donc pas détecter une régression de parsing ici.

Lancer avec :  pytest
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from groq import APITimeoutError, AuthenticationError, InternalServerError, RateLimitError

import app.services.transcription as transcription


def _fake_groq_response(text, segments):
    return SimpleNamespace(text=text, segments=segments)


class TestTranscrireChunk:
    def test_parse_segments_horodates(self, monkeypatch, tmp_path):
        fake_chunk = tmp_path / "chunk.mp3"
        fake_chunk.write_bytes(b"faux audio")

        fake_client = MagicMock()
        fake_client.audio.transcriptions.create.return_value = _fake_groq_response(
            text="Bonjour tout le monde. ",
            segments=[
                {"start": 0.0, "end": 1.2, "text": "Bonjour"},
                {"start": 1.2, "end": 2.5, "text": " tout le monde."},
            ],
        )
        monkeypatch.setattr(transcription, "client", fake_client)

        texte, segments = transcription.transcrire_chunk(str(fake_chunk))

        assert texte == "Bonjour tout le monde. "
        assert segments == [
            {"start": 0.0, "end": 1.2, "text": "Bonjour"},
            {"start": 1.2, "end": 2.5, "text": "tout le monde."},
        ]

    def test_langue_toujours_auto_detectee(self, monkeypatch, tmp_path):
        # La langue parlée est toujours auto-détectée par Whisper (language=None),
        # indépendamment de la langue de sortie choisie côté /process.
        fake_chunk = tmp_path / "chunk.mp3"
        fake_chunk.write_bytes(b"faux audio")

        fake_client = MagicMock()
        fake_client.audio.transcriptions.create.return_value = _fake_groq_response(
            text="Hello world.", segments=[]
        )
        monkeypatch.setattr(transcription, "client", fake_client)

        transcription.transcrire_chunk(str(fake_chunk))

        _, kwargs = fake_client.audio.transcriptions.create.call_args
        assert kwargs["language"] is None


def _status_error(cls, status, headers=None):
    request = httpx.Request("POST", "https://api.groq.com/audio/transcriptions")
    response = httpx.Response(status, request=request, headers=headers or {})
    return cls("erreur", response=response, body=None)


class TestRetries:
    @pytest.fixture
    def fake_chunk(self, tmp_path):
        chunk = tmp_path / "chunk.mp3"
        chunk.write_bytes(b"faux audio")
        return str(chunk)

    @pytest.fixture
    def pauses(self, monkeypatch):
        """Remplace time.sleep : aucune vraie attente, et on garde les délais demandés."""
        durees = []
        monkeypatch.setattr(transcription.time, "sleep", durees.append)
        return durees

    def _client(self, monkeypatch, *effets):
        fake_client = MagicMock()
        fake_client.audio.transcriptions.create.side_effect = list(effets)
        monkeypatch.setattr(transcription, "client", fake_client)
        return fake_client

    def test_429_puis_succes_respecte_retry_after(self, monkeypatch, fake_chunk, pauses):
        fake_client = self._client(
            monkeypatch,
            _status_error(RateLimitError, 429, {"retry-after": "7"}),
            _fake_groq_response("Bonjour.", []),
        )

        texte, _ = transcription.transcrire_chunk(fake_chunk)

        assert texte == "Bonjour."
        assert pauses == [7.0]
        assert fake_client.audio.transcriptions.create.call_count == 2

    def test_429_sans_retry_after_utilise_backoff_exponentiel(self, monkeypatch, fake_chunk, pauses):
        self._client(
            monkeypatch,
            _status_error(RateLimitError, 429),
            _status_error(RateLimitError, 429),
            _fake_groq_response("ok", []),
        )

        transcription.transcrire_chunk(fake_chunk)

        assert pauses == [1.0, 2.0]

    def test_retry_after_plafonne(self, monkeypatch, fake_chunk, pauses):
        self._client(
            monkeypatch,
            _status_error(RateLimitError, 429, {"retry-after": "3600"}),
            _fake_groq_response("ok", []),
        )

        transcription.transcrire_chunk(fake_chunk)

        assert pauses == [transcription.ATTENTE_MAX_SEC]

    def test_erreur_5xx_est_retentee(self, monkeypatch, fake_chunk, pauses):
        self._client(
            monkeypatch,
            _status_error(InternalServerError, 503),
            _fake_groq_response("ok", []),
        )

        texte, _ = transcription.transcrire_chunk(fake_chunk)

        assert texte == "ok"
        assert len(pauses) == 1

    def test_timeout_est_retente(self, monkeypatch, fake_chunk, pauses):
        self._client(
            monkeypatch,
            APITimeoutError(request=httpx.Request("POST", "https://api.groq.com")),
            _fake_groq_response("ok", []),
        )

        texte, _ = transcription.transcrire_chunk(fake_chunk)

        assert texte == "ok"

    def test_erreur_non_transitoire_n_est_pas_retentee(self, monkeypatch, fake_chunk, pauses):
        fake_client = self._client(monkeypatch, _status_error(AuthenticationError, 401))

        with pytest.raises(AuthenticationError):
            transcription.transcrire_chunk(fake_chunk)

        assert fake_client.audio.transcriptions.create.call_count == 1
        assert pauses == []

    def test_abandon_apres_toutes_les_tentatives(self, monkeypatch, fake_chunk, pauses):
        fake_client = self._client(
            monkeypatch,
            *[_status_error(RateLimitError, 429) for _ in range(transcription.MAX_TENTATIVES)],
        )

        with pytest.raises(RuntimeError, match="RateLimitError"):
            transcription.transcrire_chunk(fake_chunk)

        assert fake_client.audio.transcriptions.create.call_count == transcription.MAX_TENTATIVES
        # Pas d'attente inutile après la dernière tentative.
        assert len(pauses) == transcription.MAX_TENTATIVES - 1
