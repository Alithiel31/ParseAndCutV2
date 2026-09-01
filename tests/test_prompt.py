from app.services.prompt import construire_prompt


class TestConstruirePrompt:
    def test_injecte_la_transcription(self):
        prompt = construire_prompt("Ceci est un test.")
        assert "Ceci est un test." in prompt
        assert "TRANSCRIPTION" in prompt

    def test_defaut_francais(self):
        prompt = construire_prompt("Ceci est un test.")
        assert "Réponds uniquement en français" in prompt
        assert "Respond only in English" not in prompt

    def test_langue_anglaise(self):
        prompt = construire_prompt("This is a test.", lang="en")
        assert "This is a test." in prompt
        assert "TRANSCRIPT:" in prompt
        assert "Respond only in English" in prompt
        assert "Réponds uniquement en français" not in prompt
