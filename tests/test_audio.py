"""
Tests du service app.services.audio (validation d'extension, découpage FFmpeg).

Le découpage réel (subprocess FFmpeg) n'est pas testé ici — voir test_transcribe.py
pour les tests de flux qui mockent découper_audio au niveau de la route.
"""
import shutil
import subprocess

import pytest

from app.services.audio import allowed_file, est_silencieux, mesurer_pic_sonore


class TestAllowedFile:
    def test_extension_autorisee(self):
        assert allowed_file("cours.mp3") is True
        assert allowed_file("cours.WAV") is True  # insensible à la casse

    def test_extension_refusee(self):
        assert allowed_file("cours.txt") is False

    def test_sans_extension(self):
        assert allowed_file("cours") is False


def _generer_audio(chemin, source_lavfi):
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", source_lavfi, "-t", "2", str(chemin)],
        check=True,
    )
    return str(chemin)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg indisponible")
class TestDetectionSilence:
    def test_silence_numerique_detecte(self, tmp_path):
        # Reproduit un micro coupé par le navigateur : échantillons à zéro.
        fichier = _generer_audio(tmp_path / "vide.wav", "anullsrc=r=16000:cl=mono")
        assert est_silencieux(fichier) is True

    def test_son_normal_non_silencieux(self, tmp_path):
        fichier = _generer_audio(tmp_path / "son.wav", "sine=frequency=440:sample_rate=16000")
        assert est_silencieux(fichier) is False

    def test_bruit_de_fond_faible_non_silencieux(self, tmp_path):
        # ~ -60 dB : un enregistrement très discret ne doit pas être rejeté.
        fichier = _generer_audio(tmp_path / "bruit.wav", "anoisesrc=amplitude=0.001:sample_rate=16000")
        assert est_silencieux(fichier) is False

    def test_fichier_illisible_traite_normalement(self, tmp_path):
        # Mesure impossible -> on ne rejette pas : le pipeline s'en charge.
        faux = tmp_path / "faux.mp3"
        faux.write_bytes(b"pas de l'audio")
        assert mesurer_pic_sonore(str(faux)) is None
        assert est_silencieux(str(faux)) is False
