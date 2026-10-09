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


def construire_prompt_bloc(texte: str, lang: str, numero: int, total: int) -> str:
    """Prompt de la première étape d'un résumé « par blocs » : notes détaillées
    d'UNE partie d'une longue transcription (étape intermédiaire, jamais
    montrée telle quelle à l'utilisateur)."""
    if lang == "en":
        return f"""You are an expert note-taking assistant.
This is part {numero} of {total} of a long transcript (a lecture or a meeting).
Write detailed Markdown notes for THIS part only; they will later be merged
with the notes of the other parts.

Rules:
- Keep everything that matters: concepts, definitions, arguments, examples,
  names, figures, dates, decisions, action items and who owns them
- Follow the order of the transcript, with short headings for each topic
- Be faithful: add nothing that is not in the text
- Discreetly correct obvious transcription errors
- No introduction and no conclusion
- Respond only in English

TRANSCRIPT (part {numero}/{total}):
{texte}
"""

    return f"""Tu es un assistant expert en prise de notes.
Voici la partie {numero} sur {total} d'une longue transcription (cours ou réunion).
Rédige des notes Markdown détaillées de CETTE partie uniquement ; elles seront
ensuite fusionnées avec celles des autres parties.

Règles :
- Conserve tout ce qui compte : concepts, définitions, arguments, exemples,
  noms, chiffres, dates, décisions, actions à mener et leur responsable
- Suis l'ordre de la transcription, avec de courts titres par sujet
- Reste fidèle : n'ajoute rien qui ne soit dans le texte
- Corrige discrètement les erreurs de transcription évidentes
- Ni introduction ni conclusion
- Réponds uniquement en français

TRANSCRIPTION (partie {numero}/{total}) :
{texte}
"""


def construire_prompt_fusion(notes: list[str], lang: str) -> str:
    """Prompt de la seconde étape : fusionne les notes de chaque bloc en une
    seule fiche finale, avec les mêmes règles de forme que `construire_prompt`."""
    if lang == "en":
        parties = "\n\n".join(f"=== PART {i} ===\n{n}" for i, n in enumerate(notes, 1))
        return f"""You are an expert academic note-taking assistant.
Below are the detailed notes of the consecutive parts of one long recording.
Merge them into ONE clear, structured Markdown study sheet.

Rules:
- Start with a summary of 3 to 5 key points (## Summary section)
- Use hierarchical headings (# ## ###) to organize the content by theme,
  not by part; merge duplicates and keep the logical order
- Put key concepts in **bold**
- Use bullet lists for enumerations
- Put important definitions in blockquotes (> Definition: ...)
- Keep decisions and action items together in a dedicated section if there are any
- Do not invent anything that is not in the notes
- Respond only in English

NOTES:
{parties}
"""

    parties = "\n\n".join(f"=== PARTIE {i} ===\n{n}" for i, n in enumerate(notes, 1))
    return f"""Tu es un assistant universitaire expert en prise de notes.
Voici les notes détaillées des parties successives d'un même enregistrement long.
Fusionne-les en UNE fiche de révision Markdown structurée et claire.

Règles :
- Commence par un résumé en 3 à 5 points clés (section ## Résumé)
- Utilise des titres hiérarchiques (# ## ###) pour organiser le contenu par
  thème, pas par partie ; fusionne les doublons et garde l'ordre logique
- Mets les concepts clés en **gras**
- Utilise des listes à puces pour les énumérations
- Mets les définitions importantes dans des blocs citation (> Définition : ...)
- Regroupe décisions et actions à mener dans une section dédiée s'il y en a
- N'invente rien qui ne soit dans les notes
- Réponds uniquement en français

NOTES :
{parties}
"""
