def construire_prompt(texte: str, lang: str = "fr") -> str:
    """
    Prompt enrichi pour la structuration Markdown.
    Isolé pour faciliter les tests et les évolutions futures.
    """
    if lang == "en":
        return f"""You are an expert academic note-taking assistant.
Turn this raw transcript into a clear, structured Markdown study sheet.

Rules:
- Start with a summary of 3 to 5 key points (## Summary section)
- Use hierarchical headings (# ## ###) to organize the content
- Put key concepts in **bold**
- Use bullet lists for enumerations
- Put important definitions in blockquotes (> Definition: ...)
- Discreetly correct obvious transcription errors
- If the content is very long, structure it into large thematic parts
- Respond only in English

TRANSCRIPT:
{texte}
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
