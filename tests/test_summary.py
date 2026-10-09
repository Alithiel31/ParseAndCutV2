"""
Tests du résumé par blocs (app.services.summary) : découpage d'une longue
transcription, puis notes par bloc et fusion. Le client Groq est simulé.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from groq import RateLimitError

import app.services.groq_retry as groq_retry
import app.services.summary as summary
from app.services.summary import decouper_en_blocs, generer_fiche


def _phrases(n, longueur=60):
    return " ".join(f"Phrase numéro {i} " + "x" * longueur + "." for i in range(n))


class TestDecouperEnBlocs:
    def test_texte_court_un_seul_bloc(self):
        assert decouper_en_blocs("Bonjour. Au revoir.", taille=100) == ["Bonjour. Au revoir."]

    def test_texte_vide(self):
        assert decouper_en_blocs("   ", taille=100) == []

    def test_aucun_bloc_ne_depasse_la_taille(self):
        blocs = decouper_en_blocs(_phrases(200), taille=1000)
        assert len(blocs) > 1
        assert all(0 < len(b) <= 1000 for b in blocs)

    def test_aucun_mot_perdu_ni_duplique(self):
        texte = _phrases(200)
        blocs = decouper_en_blocs(texte, taille=1000)
        assert " ".join(blocs).split() == texte.split()

    def test_coupe_a_une_fin_de_phrase(self):
        blocs = decouper_en_blocs(_phrases(200), taille=1000)
        assert all(b.endswith(".") for b in blocs)

    def test_sans_espace_coupe_franche(self):
        blocs = decouper_en_blocs("a" * 2500, taille=1000)
        assert [len(b) for b in blocs] == [1000, 1000, 500]


def _fake_client(reponses=None):
    """Client dont chaque appel renvoie « réponse N » ; garde les appels reçus."""
    appels = []

    def _create(**kwargs):
        appels.append(kwargs)
        contenu = reponses[len(appels) - 1] if reponses else f"réponse {len(appels)}"
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=contenu))])

    client = MagicMock()
    client.chat.completions.create.side_effect = _create
    return client, appels


class TestGenererFiche:
    def test_texte_court_un_seul_appel_prompt_d_origine(self):
        client, appels = _fake_client()

        fiche = generer_fiche(client, "Un cours très court.", "fr")

        assert fiche == "réponse 1"
        assert len(appels) == 1
        assert "TRANSCRIPTION :" in appels[0]["messages"][0]["content"]
        assert appels[0]["max_tokens"] == summary.MAX_TOKENS_PASSE_UNIQUE

    def test_texte_long_notes_par_bloc_puis_fusion(self, monkeypatch):
        monkeypatch.setattr(summary, "SEUIL_PASSE_UNIQUE_CHARS", 2000)
        monkeypatch.setattr(summary, "TAILLE_BLOC_CHARS", 1000)
        client, appels = _fake_client()
        texte = _phrases(60)
        attendu_blocs = len(decouper_en_blocs(texte, 1000))
        assert attendu_blocs >= 3

        fiche = generer_fiche(client, texte, "fr")

        assert len(appels) == attendu_blocs + 1
        # Les appels de blocs portent un bloc de texte, numéroté.
        premier = appels[0]["messages"][0]["content"]
        assert f"partie 1 sur {attendu_blocs}" in premier
        # La fusion reçoit les notes de TOUS les blocs, dans l'ordre.
        fusion = appels[-1]["messages"][0]["content"]
        for i in range(1, attendu_blocs + 1):
            assert f"=== PARTIE {i} ===\nréponse {i}" in fusion
        assert appels[-1]["max_tokens"] == summary.MAX_TOKENS_FUSION
        assert fiche == f"réponse {attendu_blocs + 1}"

    def test_texte_long_en_anglais(self, monkeypatch):
        monkeypatch.setattr(summary, "SEUIL_PASSE_UNIQUE_CHARS", 500)
        monkeypatch.setattr(summary, "TAILLE_BLOC_CHARS", 300)
        client, appels = _fake_client()

        generer_fiche(client, _phrases(20), "en")

        assert "part 1 of" in appels[0]["messages"][0]["content"]
        assert "=== PART 1 ===" in appels[-1]["messages"][0]["content"]
        assert "Respond only in English" in appels[-1]["messages"][0]["content"]

    def test_progression_signalee_a_chaque_bloc(self, monkeypatch):
        monkeypatch.setattr(summary, "SEUIL_PASSE_UNIQUE_CHARS", 500)
        monkeypatch.setattr(summary, "TAILLE_BLOC_CHARS", 300)
        client, _ = _fake_client()
        suivi = []
        texte = _phrases(20)
        n = len(decouper_en_blocs(texte, 300))

        generer_fiche(client, texte, "fr", lambda **champs: suivi.append(champs))

        assert suivi[0] == {"summary_current": 1, "summary_total": n}
        assert suivi[n - 1] == {"summary_current": n, "summary_total": n}
        # Dernière étape : la fusion compte pour une étape de plus.
        assert suivi[-1] == {"summary_current": n + 1, "summary_total": n + 1}

    def test_texte_court_pas_de_progression(self):
        client, _ = _fake_client()
        suivi = []

        generer_fiche(client, "Court.", "fr", lambda **champs: suivi.append(champs))

        assert suivi == []

    def test_echec_d_un_bloc_remonte_l_erreur(self, monkeypatch):
        monkeypatch.setattr(summary, "SEUIL_PASSE_UNIQUE_CHARS", 500)
        monkeypatch.setattr(summary, "TAILLE_BLOC_CHARS", 300)
        client = MagicMock()
        client.chat.completions.create.side_effect = ValueError("LLM en panne")

        with pytest.raises(ValueError, match="LLM en panne"):
            generer_fiche(client, _phrases(20), "fr")

    def test_quota_429_pendant_le_resume_est_retente(self, monkeypatch):
        monkeypatch.setattr(groq_retry.time, "sleep", lambda s: None)
        reponse = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="fiche"))])
        requete = httpx.Request("POST", "https://api.groq.com/chat")
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            RateLimitError("quota", response=httpx.Response(429, request=requete), body=None),
            reponse,
        ]

        assert generer_fiche(client, "Court.", "fr") == "fiche"
        assert client.chat.completions.create.call_count == 2
