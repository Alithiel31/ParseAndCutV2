"""
Tests du service app.services.audio (validation d'extension, découpage FFmpeg).

Le découpage réel (subprocess FFmpeg) n'est pas testé ici — voir test_transcribe.py
pour les tests de flux qui mockent découper_audio au niveau de la route.
"""
from app.services.audio import allowed_file


class TestAllowedFile:
    def test_extension_autorisee(self):
        assert allowed_file("cours.mp3") is True
        assert allowed_file("cours.WAV") is True  # insensible à la casse

    def test_extension_refusee(self):
        assert allowed_file("cours.txt") is False

    def test_sans_extension(self):
        assert allowed_file("cours") is False
