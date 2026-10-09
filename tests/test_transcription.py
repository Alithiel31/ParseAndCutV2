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

import app.services.groq_retry as groq_retry
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
        monkeypatch.setattr(groq_retry.time, "sleep", durees.append)
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

        assert pauses == [groq_retry.ATTENTE_MAX_SEC]

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
            *[_status_error(RateLimitError, 429) for _ in range(groq_retry.MAX_TENTATIVES)],
        )

        with pytest.raises(RuntimeError, match="RateLimitError"):
            transcription.transcrire_chunk(fake_chunk)

        assert fake_client.audio.transcriptions.create.call_count == groq_retry.MAX_TENTATIVES
        # Pas d'attente inutile après la dernière tentative.
        assert len(pauses) == groq_retry.MAX_TENTATIVES - 1


def _seg(texte, no_speech_prob=0.01, avg_logprob=-0.2, start=0.0):
    return {
        "start": start, "end": start + 2.0, "text": texte,
        "no_speech_prob": no_speech_prob, "avg_logprob": avg_logprob,
    }


class TestFiltreHallucinations:
    def _transcrire(self, monkeypatch, tmp_path, segments, text="brut"):
        chunk = tmp_path / "chunk.mp3"
        chunk.write_bytes(b"faux audio")
        fake_client = MagicMock()
        fake_client.audio.transcriptions.create.return_value = _fake_groq_response(text, segments)
        monkeypatch.setattr(transcription, "client", fake_client)
        return transcription.transcrire_chunk(str(chunk))

    def test_phrase_connue_supprimee_sans_condition(self, monkeypatch, tmp_path):
        # Cas réel : la sortie de ton enregistrement muet.
        texte, segments = self._transcrire(monkeypatch, tmp_path, [
            _seg("On va passer à travers."),
            _seg("Sous-titrage Société Radio-Canada", no_speech_prob=0.01, start=30.0),
        ])
        assert [s["text"] for s in segments] == ["On va passer à travers."]
        assert texte == "On va passer à travers."

    def test_you_repete_sur_silence_supprime(self, monkeypatch, tmp_path):
        _, segments = self._transcrire(monkeypatch, tmp_path, [
            _seg("you", no_speech_prob=0.9),
            _seg("you you", no_speech_prob=0.8, start=30.0),
            _seg("You.", no_speech_prob=0.7, start=60.0),
        ])
        assert segments == []

    def test_you_dit_pour_de_vrai_conserve(self, monkeypatch, tmp_path):
        # no_speech_prob très bas : Whisper est sûr qu'il y a de la parole.
        _, segments = self._transcrire(monkeypatch, tmp_path, [_seg("Thank you.", no_speech_prob=0.02)])
        assert [s["text"] for s in segments] == ["Thank you."]

    def test_critere_whisper_no_speech_et_logprob_bas(self, monkeypatch, tmp_path):
        _, segments = self._transcrire(monkeypatch, tmp_path, [
            _seg("Un texte inventé quelconque", no_speech_prob=0.85, avg_logprob=-1.4),
        ])
        assert segments == []

    def test_parole_peu_sure_mais_probable_conservee(self, monkeypatch, tmp_path):
        # no_speech_prob élevé SEUL ne suffit pas : il faut aussi un logprob bas.
        _, segments = self._transcrire(monkeypatch, tmp_path, [
            _seg("Ceci est un vrai passage", no_speech_prob=0.7, avg_logprob=-0.3),
        ])
        assert len(segments) == 1

    def test_rien_supprime_garde_le_texte_brut_de_whisper(self, monkeypatch, tmp_path):
        texte, _ = self._transcrire(monkeypatch, tmp_path, [_seg("Bonjour.")], text="Bonjour. ")
        assert texte == "Bonjour. "

    def test_segments_sans_metriques_conserves(self, monkeypatch, tmp_path):
        # Réponse sans no_speech_prob/avg_logprob : on ne filtre que les phrases connues.
        _, segments = self._transcrire(monkeypatch, tmp_path, [
            {"start": 0.0, "end": 1.0, "text": "Bonjour"},
            {"start": 1.0, "end": 2.0, "text": "you"},
        ])
        assert [s["text"] for s in segments] == ["Bonjour", "you"]
