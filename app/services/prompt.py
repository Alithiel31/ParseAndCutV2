def construire_prompt(texte: str) -> str:
    """
    Prompt enrichi pour la structuration Markdown.
    Isolé pour faciliter les tests et les évolutions futures.
    """
    return f"""Tu es un assistant universitaire expert en prise de notes.
Transforme cette transcription brute en fiche de révision Markdown structurée et claire.

Règles :
- Commence par un résumé en 3 à 5 points clés (section ## Résumé)
- Utilise des titres hiérarchiques (# ## ###) pour organiser le contenu
- Mets les concepts clés en **gras**
- Utilise des listes à puces pour les énumérations
- Mets les définitions importantes dans des blocs citation (> Définition : ...)
- Corrige discrètement les erreurs de transcription évidentes
- Si le contenu est très long, structure-le en grandes parties thématiques
- Réponds uniquement en français

TRANSCRIPTION :
{texte}
"""
