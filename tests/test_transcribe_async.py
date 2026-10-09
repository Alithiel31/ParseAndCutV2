"""
Tests du flux asynchrone (app.routers.transcribe : /api/transcribe/start +
/api/transcribe/status/{job_id}).

Ce flux existe pour contourner le timeout fixe de 100s imposé par Cloudflare
sur les requêtes proxyées (voir docs/Troubleshooting.fr.md) : /process reste
synchrone (et testé séparément dans test_transcribe.py) pour ne pas casser
les clients existants (PWA), mais le pipeline y est trop long pour un fichier
de plus de quelques minutes d'audio derrière le tunnel Cloudflare.

Le traitement réel tourne dans un thread en tâche de fond : les tests
attendent la fin du job en sondant /status en boucle (le pipeline est mocké,
donc quasi instantané).
"""
import time
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import app.routers.transcribe as transcribe
from app.main import app


@pytest.fixture
def client_app():
    return TestClient(app)


def _attendre_fin_job(client_app, job_id, timeout=5.0):
    """Sonde /api/transcribe/status/{job_id} jusqu'à un statut terminal
    (200 avec status=done, ou code d'erreur HTTP), ou lève au bout de
    `timeout` secondes si le job reste bloqué en "processing"."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = client_app.get(f"/api/transcribe/status/{job_id}")
        if resp.status_code != 200 or resp.json().get("status") != "processing":
            return resp
        time.sleep(0.01)
    raise AssertionError(f"Job {job_id} toujours en 'processing' après {timeout}s")


class TestTranscribeStartValidation:
    def test_sans_fichier(self, client_app, monkeypatch):
        monkeypatch.setattr(transcribe, "client", MagicMock())

        resp = client_app.post("/api/transcribe/start")
        assert resp.status_code == 400

    def test_extension_refusee(self, client_app, monkeypatch):
        monkeypatch.setattr(transcribe, "client", MagicMock())

        files = {"audio": ("notes.txt", b"pas de l'audio", "text/plain")}
        resp = client_app.post("/api/transcribe/start", files=files)
        assert resp.status_code == 415

    def test_groq_non_configure(self, client_app, monkeypatch):
        monkeypatch.setattr(transcribe, "client", None)

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/api/transcribe/start", files=files)
        assert resp.status_code == 503

    def test_mode_invalide(self, client_app, monkeypatch):
        monkeypatch.setattr(transcribe, "client", MagicMock())

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/api/transcribe/start", files=files, data={"mode": "bogus"})
        assert resp.status_code == 400

    def test_ne_bloque_pas_la_reponse(self, client_app, monkeypatch, tmp_path):
        # Le point central du flux asynchrone : /start doit répondre 202
        # immédiatement (job_id), avant même que le pipeline n'ait fini.
        #
        # Important : le test attend explicitement la fin du job (via
        # _attendre_fin_job) avant de rendre la main. `_traiter_job` tourne
        # dans un vrai thread et résout découper_audio/transcrire_chunk/client
        # par lookup global à *chaque* appel — si ce thread survivait au-delà
        # du test, le monkeypatch teardown pourrait s'exécuter pendant qu'il
        # tourne encore, et un test suivant pourrait alors monkeypatcher ces
        # globals pendant que ce thread orphelin les relit, produisant un
        # résultat aléatoire selon le timing (observé de façon intermittente
        # en CI : cf. historique git).
        fake_chunk = tmp_path / "chunk_0.mp3"
        fake_chunk.write_bytes(b"faux audio")

        def _decouper_lent(*a, **k):
            time.sleep(0.05)
            return [str(fake_chunk)]

        monkeypatch.setattr(transcribe, "découper_audio", _decouper_lent)
        monkeypatch.setattr(
            transcribe, "transcrire_chunk", lambda path, retries=2: ("Texte. ", [])
        )
        monkeypatch.setattr(transcribe, "client", MagicMock())

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        avant = time.monotonic()
        resp = client_app.post(
            "/api/transcribe/start", files=files, data={"mode": "transcript"}
        )
        écoulé = time.monotonic() - avant

        assert resp.status_code == 202
        job_id = resp.json()["job_id"]
        assert écoulé < 0.05, "la réponse a attendu la fin du découpage (pipeline pas asynchrone)"

        _attendre_fin_job(client_app, job_id)


class TestTranscribeStatusRoute:
    def test_job_inconnu(self, client_app):
        resp = client_app.get("/api/transcribe/status/inexistant")
        assert resp.status_code == 404

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
        start_resp = client_app.post("/api/transcribe/start", files=files)
        assert start_resp.status_code == 202
        job_id = start_resp.json()["job_id"]

        resp = _attendre_fin_job(client_app, job_id)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "done"
        assert data["mode"] == "summary"
        assert data["markdown"] == "# Fiche générée"
        assert data["stats"]["chunks"] == 1

    def test_job_supprime_apres_recuperation(self, client_app, monkeypatch, tmp_path):
        fake_chunk = tmp_path / "chunk_0.mp3"
        fake_chunk.write_bytes(b"faux audio")

        monkeypatch.setattr(
            transcribe, "découper_audio", lambda *a, **k: [str(fake_chunk)]
        )
        monkeypatch.setattr(
            transcribe, "transcrire_chunk", lambda path, retries=2: ("Texte. ", [])
        )
        monkeypatch.setattr(transcribe, "client", MagicMock())

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        start_resp = client_app.post(
            "/api/transcribe/start", files=files, data={"mode": "transcript"}
        )
        job_id = start_resp.json()["job_id"]

        first = _attendre_fin_job(client_app, job_id)
        assert first.status_code == 200

        second = client_app.get(f"/api/transcribe/status/{job_id}")
        assert second.status_code == 404

    def test_echec_decoupage(self, client_app, monkeypatch):
        monkeypatch.setattr(transcribe, "découper_audio", lambda *a, **k: [])
        monkeypatch.setattr(transcribe, "client", MagicMock())

        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        start_resp = client_app.post("/api/transcribe/start", files=files)
        job_id = start_resp.json()["job_id"]

        resp = _attendre_fin_job(client_app, job_id)
        assert resp.status_code == 422

    def test_echec_transcription(self, client_app, monkeypatch, tmp_path):
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
        start_resp = client_app.post("/api/transcribe/start", files=files)
        job_id = start_resp.json()["job_id"]

        resp = _attendre_fin_job(client_app, job_id)
        assert resp.status_code == 502


class TestTranscriptionPartielle:
    """Si le job échoue en cours de route, ce qui est déjà transcrit doit
    être renvoyé avec l'erreur plutôt que perdu."""

    def _chunks(self, tmp_path, n):
        chunks = []
        for i in range(n):
            chunk = tmp_path / f"chunk_{i}.mp3"
            chunk.write_bytes(b"faux audio")
            chunks.append(str(chunk))
        return chunks

    def _lancer(self, client_app, mode="transcript"):
        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/api/transcribe/start", files=files, data={"mode": mode})
        return _attendre_fin_job(client_app, resp.json()["job_id"])

    def test_echec_au_second_chunk_renvoie_le_premier(self, client_app, monkeypatch, tmp_path):
        chunks = self._chunks(tmp_path, 2)
        monkeypatch.setattr(transcribe, "découper_audio", lambda *a, **k: chunks)
        monkeypatch.setattr(transcribe, "client", MagicMock())

        appels = []

        def _transcrire(path, retries=5):
            appels.append(path)
            if len(appels) == 2:
                raise RuntimeError("quota Groq épuisé")
            return "Premier. ", [{"start": 0.0, "end": 2.0, "text": "Premier."}]

        monkeypatch.setattr(transcribe, "transcrire_chunk", _transcrire)

        resp = self._lancer(client_app)

        assert resp.status_code == 502
        corps = resp.json()
        assert "quota Groq épuisé" in corps["detail"]
        assert corps["partial_transcript"] == "[00:00] Premier."

    def test_echec_du_resume_conserve_la_transcription_complete(self, client_app, monkeypatch, tmp_path):
        chunks = self._chunks(tmp_path, 1)
        monkeypatch.setattr(transcribe, "découper_audio", lambda *a, **k: chunks)
        monkeypatch.setattr(
            transcribe, "transcrire_chunk",
            lambda path, retries=5: ("Cours. ", [{"start": 3.0, "end": 5.0, "text": "Cours."}]),
        )
        fake_groq = MagicMock()
        fake_groq.chat.completions.create.side_effect = ValueError("LLM indisponible")
        monkeypatch.setattr(transcribe, "client", fake_groq)

        resp = self._lancer(client_app, mode="summary")

        assert resp.status_code == 500
        assert resp.json()["partial_transcript"] == "[00:03] Cours."

    def test_echec_sans_rien_de_transcrit_garde_la_forme_habituelle(self, client_app, monkeypatch, tmp_path):
        chunks = self._chunks(tmp_path, 1)
        monkeypatch.setattr(transcribe, "découper_audio", lambda *a, **k: chunks)
        monkeypatch.setattr(transcribe, "client", MagicMock())

        def _raise(*a, **k):
            raise RuntimeError("échec immédiat")

        monkeypatch.setattr(transcribe, "transcrire_chunk", _raise)

        resp = self._lancer(client_app)

        assert resp.status_code == 502
        assert set(resp.json()) == {"detail"}


class TestChunksSilencieux:
    """Un micro coupé produit des chunks de silence numérique : ils ne doivent
    ni consommer de quota Whisper ni produire une fiche inventée."""

    def _preparer(self, monkeypatch, tmp_path, silencieux):
        chunks = []
        for i in range(len(silencieux)):
            chunk = tmp_path / f"chunk_{i}.mp3"
            chunk.write_bytes(b"faux audio")
            chunks.append(str(chunk))
        monkeypatch.setattr(transcribe, "découper_audio", lambda *a, **k: chunks)
        monkeypatch.setattr(
            transcribe, "est_silencieux", lambda path: silencieux[chunks.index(path)]
        )
        monkeypatch.setattr(transcribe, "client", MagicMock())
        appels = []

        def _transcrire(path, retries=5):
            appels.append(path)
            return "Du texte. ", [{"start": 1.0, "end": 2.0, "text": "Du texte."}]

        monkeypatch.setattr(transcribe, "transcrire_chunk", _transcrire)
        return chunks, appels

    def _lancer(self, client_app, mode="transcript"):
        files = {"audio": ("cours.mp3", b"faux contenu audio", "audio/mpeg")}
        resp = client_app.post("/api/transcribe/start", files=files, data={"mode": mode})
        return _attendre_fin_job(client_app, resp.json()["job_id"])

    def test_tout_silencieux_erreur_explicite_sans_appel_whisper(self, client_app, monkeypatch, tmp_path):
        _, appels = self._preparer(monkeypatch, tmp_path, [True, True, True])

        resp = self._lancer(client_app)

        assert resp.status_code == 422
        assert "silencieux" in resp.json()["detail"]
        assert appels == []

    def test_chunks_silencieux_ignores_les_autres_transcrits(self, client_app, monkeypatch, tmp_path):
        chunks, appels = self._preparer(monkeypatch, tmp_path, [False, True, True])

        resp = self._lancer(client_app)

        assert resp.status_code == 200
        assert appels == [chunks[0]]
        corps = resp.json()
        assert corps["stats"]["silent_chunks"] == 2
        assert corps["transcript"] == "[00:01] Du texte."
