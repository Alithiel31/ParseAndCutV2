"""
Tests de l'enregistrement par segments (app.services.recordings et
app.routers.recordings) : stockage idempotent, validation, détection de
segments manquants, et pipeline de bout en bout sur de vrais segments webm.
"""
import io
import shutil
import subprocess
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import app.routers.recordings as recordings_router
import app.routers.transcribe as transcribe
import app.services.recordings as recordings
from app.main import app
from test_transcribe_async import _attendre_fin_job


@pytest.fixture(autouse=True)
def dossier_isole(tmp_path, monkeypatch):
    """Chaque test écrit dans son propre dossier d'enregistrements."""
    monkeypatch.setattr(recordings, "REC_DIR", str(tmp_path / "pac_recordings"))


@pytest.fixture
def client_app():
    return TestClient(app)


def _segment(contenu=b"audio factice", nom="segment.webm"):
    return {"audio": (nom, io.BytesIO(contenu), "audio/webm")}


def _creer(client_app):
    return client_app.post("/api/recordings").json()["recording_id"]


class TestServiceStockage:
    def test_segment_idempotent_le_dernier_envoi_gagne(self):
        rec = recordings.creer_enregistrement()
        for contenu in (b"v1", b"version deux"):
            recordings.enregistrer_segment(rec, 0, "webm", io.BytesIO(contenu), 1000, 10_000)

        assert recordings.indices_recus(rec) == [0]
        assert open(recordings.chemins_ordonnes(rec)[0], "rb").read() == b"version deux"

    def test_renvoi_avec_autre_extension_remplace(self):
        rec = recordings.creer_enregistrement()
        recordings.enregistrer_segment(rec, 0, "webm", io.BytesIO(b"a"), 1000, 10_000)
        recordings.enregistrer_segment(rec, 0, "mp4", io.BytesIO(b"b"), 1000, 10_000)

        assert len(recordings.chemins_ordonnes(rec)) == 1
        assert recordings.chemins_ordonnes(rec)[0].endswith(".mp4")

    def test_segment_trop_gros_ne_laisse_aucun_fichier(self):
        rec = recordings.creer_enregistrement()
        with pytest.raises(recordings.SegmentTropGros):
            recordings.enregistrer_segment(rec, 0, "webm", io.BytesIO(b"x" * 500), 100, 10_000)

        assert recordings.indices_recus(rec) == []
        assert recordings.taille_totale(rec) == 0

    def test_total_cumule_limite(self):
        rec = recordings.creer_enregistrement()
        recordings.enregistrer_segment(rec, 0, "webm", io.BytesIO(b"x" * 80), 100, 150)
        with pytest.raises(recordings.EnregistrementTropGros):
            recordings.enregistrer_segment(rec, 1, "webm", io.BytesIO(b"x" * 80), 100, 150)

    def test_remplacer_un_segment_ne_double_pas_son_poids(self):
        rec = recordings.creer_enregistrement()
        for _ in range(3):
            recordings.enregistrer_segment(rec, 0, "webm", io.BytesIO(b"x" * 80), 100, 150)
        assert recordings.taille_totale(rec) == 80

    def test_segments_manquants(self):
        rec = recordings.creer_enregistrement()
        for i in (0, 1, 4):
            recordings.enregistrer_segment(rec, i, "webm", io.BytesIO(b"x"), 100, 1000)
        assert recordings.segments_manquants(rec) == [2, 3]

    def test_ordre_numerique_et_pas_alphabetique(self):
        rec = recordings.creer_enregistrement()
        for i in (10, 2, 1):
            recordings.enregistrer_segment(rec, i, "webm", io.BytesIO(b"x"), 100, 1000)
        assert [p.rsplit("seg_", 1)[1][:4] for p in recordings.chemins_ordonnes(rec)] == ["0001", "0002", "0010"]

    def test_marqueur_termine_atomique(self):
        rec = recordings.creer_enregistrement()
        assert recordings.marquer_termine(rec) is True
        assert recordings.marquer_termine(rec) is False

    def test_identifiant_malforme_jamais_utilise_comme_chemin(self):
        for mauvais in ("../etc", "..", "a/b", "", "X" * 32):
            assert recordings.existe(mauvais) is False

    def test_nettoyage_des_enregistrements_abandonnes(self, monkeypatch):
        vieux = recordings.creer_enregistrement()
        monkeypatch.setattr(recordings, "RECORDING_MAX_AGE_SEC", -1)
        recordings.creer_enregistrement()  # déclenche le nettoyage
        assert recordings.existe(vieux) is False


class TestRoutes:
    @pytest.fixture(autouse=True)
    def groq_configure(self, monkeypatch):
        monkeypatch.setattr(transcribe, "client", MagicMock())

    def test_creation(self, client_app):
        resp = client_app.post("/api/recordings")
        assert resp.status_code == 201
        corps = resp.json()
        assert len(corps["recording_id"]) == 32
        assert corps["segment_seconds"] > 0

    def test_creation_refusee_si_groq_non_configure(self, client_app, monkeypatch):
        monkeypatch.setattr(transcribe, "client", None)
        assert client_app.post("/api/recordings").status_code == 503

    def test_envoi_puis_etat(self, client_app):
        rec = _creer(client_app)
        resp = client_app.post(f"/api/recordings/{rec}/segments/0", files=_segment())
        assert resp.status_code == 200
        client_app.post(f"/api/recordings/{rec}/segments/2", files=_segment())

        etat = client_app.get(f"/api/recordings/{rec}").json()
        assert etat["segments"] == [0, 2]
        assert etat["finished"] is False

    def test_renvoi_du_meme_segment_est_sans_danger(self, client_app):
        rec = _creer(client_app)
        for _ in range(3):
            assert client_app.post(f"/api/recordings/{rec}/segments/0", files=_segment()).status_code == 200
        assert client_app.get(f"/api/recordings/{rec}").json()["segments"] == [0]

    def test_enregistrement_inconnu(self, client_app):
        assert client_app.get("/api/recordings/" + "0" * 32).status_code == 404
        assert client_app.get("/api/recordings/pas-un-id").status_code == 404
        assert client_app.post("/api/recordings/" + "0" * 32 + "/segments/0", files=_segment()).status_code == 404

    def test_index_invalide(self, client_app):
        rec = _creer(client_app)
        assert client_app.post(f"/api/recordings/{rec}/segments/-1", files=_segment()).status_code == 400
        assert client_app.post(f"/api/recordings/{rec}/segments/99999", files=_segment()).status_code == 400

    def test_extension_refusee(self, client_app):
        rec = _creer(client_app)
        resp = client_app.post(f"/api/recordings/{rec}/segments/0", files=_segment(nom="note.txt"))
        assert resp.status_code == 415

    def test_sans_fichier(self, client_app):
        rec = _creer(client_app)
        assert client_app.post(f"/api/recordings/{rec}/segments/0").status_code == 400

    def test_segment_trop_gros(self, client_app, monkeypatch):
        monkeypatch.setattr(recordings_router, "MAX_SEGMENT_SIZE_MB", 0)
        rec = _creer(client_app)
        resp = client_app.post(f"/api/recordings/{rec}/segments/0", files=_segment(b"x" * 10))
        assert resp.status_code == 413

    def test_enregistrement_trop_gros(self, client_app, monkeypatch):
        monkeypatch.setattr(recordings_router, "MAX_RECORDING_SIZE_MB", 0)
        rec = _creer(client_app)
        resp = client_app.post(f"/api/recordings/{rec}/segments/0", files=_segment(b"x" * 10))
        assert resp.status_code == 413

    def test_finish_sans_segment(self, client_app):
        rec = _creer(client_app)
        assert client_app.post(f"/api/recordings/{rec}/finish").status_code == 400

    def test_finish_signale_les_segments_manquants(self, client_app):
        rec = _creer(client_app)
        for i in (0, 3):
            client_app.post(f"/api/recordings/{rec}/segments/{i}", files=_segment())

        resp = client_app.post(f"/api/recordings/{rec}/finish")

        assert resp.status_code == 409
        assert resp.json()["missing"] == [1, 2]
        assert "1, 2" in resp.json()["detail"]
        # Rien n'est lancé : le client peut renvoyer les trous puis réessayer.
        assert client_app.get(f"/api/recordings/{rec}").json()["finished"] is False

    def test_finish_valide_mode_et_langue(self, client_app):
        rec = _creer(client_app)
        client_app.post(f"/api/recordings/{rec}/segments/0", files=_segment())
        assert client_app.post(f"/api/recordings/{rec}/finish", data={"mode": "bogus"}).status_code == 400
        assert client_app.post(f"/api/recordings/{rec}/finish", data={"lang": "de"}).status_code == 400

    def test_annulation_supprime_l_audio(self, client_app):
        rec = _creer(client_app)
        client_app.post(f"/api/recordings/{rec}/segments/0", files=_segment())

        assert client_app.post(f"/api/recordings/{rec}/cancel").status_code == 200
        assert client_app.get(f"/api/recordings/{rec}").status_code == 404

    def test_limite_de_debit_partagee_entre_tous_les_segments(self, client_app):
        # Régression : slowapi compte par chemin d'URL ; sans `scope`, chaque
        # numéro de segment aurait son propre compteur et la limite serait inopérante.
        rec = _creer(client_app)
        # 60/minute par défaut : un enregistrement normal (1 segment / 5 min) en est très loin.
        for i in range(60):
            assert client_app.post(f"/api/recordings/{rec}/segments/{i}", files=_segment()).status_code == 200
        assert client_app.post(f"/api/recordings/{rec}/segments/60", files=_segment()).status_code == 429

    def test_limite_de_creation_partagee_entre_enregistrements(self, client_app):
        for _ in range(5):
            assert client_app.post("/api/recordings").status_code == 201
        assert client_app.post("/api/recordings").status_code == 429


def _webm(chemin, secondes, frequence):
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
         f"sine=frequency={frequence}:sample_rate=16000:duration={secondes}",
         "-c:a", "libopus", str(chemin)],
        check=True,
    )
    return chemin.read_bytes()


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg indisponible")
class TestPipelineDeBoutEnBout:
    """De vrais segments webm/opus passent par l'upload, l'assemblage et le
    pipeline ; seul Whisper est simulé."""

    @pytest.fixture(autouse=True)
    def groq_configure(self, monkeypatch):
        monkeypatch.setattr(transcribe, "client", MagicMock())

    def _envoyer(self, client_app, rec, tmp_path, durees):
        for i, duree in enumerate(durees):
            contenu = _webm(tmp_path / f"s{i}.webm", duree, 440 + 100 * i)
            resp = client_app.post(f"/api/recordings/{rec}/segments/{i}", files=_segment(contenu, f"segment-{i}.webm"))
            assert resp.status_code == 200

    def test_transcript_horodate_depuis_la_duree_reelle_des_segments(self, client_app, monkeypatch, tmp_path):
        vus = []

        def _transcrire(path, retries=5):
            vus.append(path)
            return "Mot. ", [{"start": 1.0, "end": 2.0, "text": f"Segment {len(vus)}"}]

        monkeypatch.setattr(transcribe, "transcrire_chunk", _transcrire)
        rec = _creer(client_app)
        self._envoyer(client_app, rec, tmp_path, [3, 5, 2])

        start = client_app.post(f"/api/recordings/{rec}/finish", data={"mode": "transcript"})
        assert start.status_code == 202
        resp = _attendre_fin_job(client_app, start.json()["job_id"], timeout=30)

        assert resp.status_code == 200
        # Décalages = somme des durées réelles : 0 s, ~3 s, ~8 s (pas des multiples de 300 s).
        lignes = resp.json()["transcript"].splitlines()
        assert lignes[0] == "[00:01] Segment 1"
        assert lignes[1] in ("[00:04] Segment 2", "[00:05] Segment 2")
        assert lignes[2] in ("[00:09] Segment 3", "[00:10] Segment 3")
        assert resp.json()["stats"]["chunks"] == 3
        # L'audio est supprimé du serveur une fois le job terminé.
        assert recordings.existe(rec) is False

    def test_resume_sur_enregistrement_segmente(self, client_app, monkeypatch, tmp_path):
        monkeypatch.setattr(
            transcribe, "transcrire_chunk",
            lambda path, retries=5: ("Du texte. ", [{"start": 0.0, "end": 1.0, "text": "Du texte."}]),
        )
        fake = MagicMock()
        fake.chat.completions.create.return_value.choices[0].message.content = "## Résumé\nOK"
        monkeypatch.setattr(transcribe, "client", fake)
        rec = _creer(client_app)
        self._envoyer(client_app, rec, tmp_path, [2, 2])

        start = client_app.post(f"/api/recordings/{rec}/finish")
        resp = _attendre_fin_job(client_app, start.json()["job_id"], timeout=30)

        assert resp.status_code == 200
        assert resp.json()["markdown"] == "## Résumé\nOK"

    def test_segment_illisible_ignore_les_autres_sont_traites(self, client_app, monkeypatch, tmp_path):
        monkeypatch.setattr(
            transcribe, "transcrire_chunk",
            lambda path, retries=5: ("Bon. ", [{"start": 0.0, "end": 1.0, "text": "Bon."}]),
        )
        rec = _creer(client_app)
        client_app.post(f"/api/recordings/{rec}/segments/0", files=_segment(b"pas du tout de l'audio"))
        self._envoyer_depuis(client_app, rec, tmp_path, index=1, duree=2)

        start = client_app.post(f"/api/recordings/{rec}/finish", data={"mode": "transcript"})
        resp = _attendre_fin_job(client_app, start.json()["job_id"], timeout=30)

        assert resp.status_code == 200
        assert resp.json()["stats"]["chunks"] == 1
        # Le segment 0 manquant compte pour sa durée nominale : le suivant est décalé de 300 s.
        assert resp.json()["transcript"] == "[05:00] Bon."

    def _envoyer_depuis(self, client_app, rec, tmp_path, index, duree):
        contenu = _webm(tmp_path / f"s{index}.webm", duree, 500)
        client_app.post(f"/api/recordings/{rec}/segments/{index}", files=_segment(contenu, f"segment-{index}.webm"))

    def test_tout_illisible_echec_clair(self, client_app, monkeypatch):
        monkeypatch.setattr(transcribe, "transcrire_chunk", lambda *a, **k: ("x", []))
        rec = _creer(client_app)
        client_app.post(f"/api/recordings/{rec}/segments/0", files=_segment(b"corrompu"))

        start = client_app.post(f"/api/recordings/{rec}/finish")
        resp = _attendre_fin_job(client_app, start.json()["job_id"], timeout=30)

        assert resp.status_code == 422
