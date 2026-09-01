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
