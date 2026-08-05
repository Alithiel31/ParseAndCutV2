from app.services.prompt import construire_prompt


class TestConstruirePrompt:
    def test_injecte_la_transcription(self):
        prompt = construire_prompt("Ceci est un test.")
        assert "Ceci est un test." in prompt
        assert "TRANSCRIPTION" in prompt
