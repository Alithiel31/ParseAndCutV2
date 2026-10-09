"""
Génération de la fiche de révision par le LLM Groq.

Une longue transcription (réunion de 2 h ≈ 100 000 caractères) donnerait, en un
seul appel, une fiche superficielle plafonnée à quelques milliers de tokens.
Au-delà de SEUIL_PASSE_UNIQUE_CHARS, on procède donc en deux étapes :
  1. notes détaillées de chaque bloc de ~TAILLE_BLOC_CHARS caractères ;
  2. fusion de ces notes en une fiche unique.
Les textes courts gardent le prompt d'origine, en un seul appel.
"""
from typing import Callable, Optional

from app.config import logger
from app.services.groq_retry import executer_avec_reessais
from app.services.prompt import construire_prompt, construire_prompt_bloc, construire_prompt_fusion

MODELE_LLM = "openai/gpt-oss-120b"

SEUIL_PASSE_UNIQUE_CHARS = 30_000   # ≈ 30 à 40 min de parole
TAILLE_BLOC_CHARS = 20_000          # ≈ 20 à 25 min de parole

MAX_TOKENS_PASSE_UNIQUE = 4096
MAX_TOKENS_NOTES_BLOC = 3000
MAX_TOKENS_FUSION = 8192

_FINS_DE_PHRASE = (". ", "? ", "! ", "\n")


def decouper_en_blocs(texte: str, taille: Optional[int] = None) -> list[str]:
    """Découpe `texte` en blocs d'au plus `taille` caractères (TAILLE_BLOC_CHARS
    par défaut), de préférence à une fin de phrase (sinon à un espace) pour ne
    pas couper un propos en deux. Aucun bloc vide ; espaces de bord retirés."""
    taille = taille or TAILLE_BLOC_CHARS
    texte = texte.strip()
    blocs: list[str] = []

    while len(texte) > taille:
        fenetre = texte[:taille]
        plancher = int(taille * 0.7)  # ne pas produire un bloc minuscule

        coupe = max((fenetre.rfind(fin) + len(fin) - 1 for fin in _FINS_DE_PHRASE if fenetre.rfind(fin) >= plancher),
                    default=-1)
        if coupe < 0:
            coupe = fenetre.rfind(" ")
        if coupe < plancher:
            coupe = taille  # aucun repère : coupe franche

        blocs.append(texte[:coupe].strip())
        texte = texte[coupe:].strip()

    if texte:
        blocs.append(texte)
    return [b for b in blocs if b]


def _completer(client, prompt: str, temperature: float, max_tokens: int, description: str) -> str:
    completion = executer_avec_reessais(
        lambda: client.chat.completions.create(
            model=MODELE_LLM,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        ),
        description,
    )
    return completion.choices[0].message.content


def generer_fiche(
    client,
    texte: str,
    lang: str,
    on_progress: Optional[Callable[..., None]] = None,
) -> str:
    """Retourne la fiche Markdown. `on_progress(summary_current=i, summary_total=n)`
    est appelé avant chaque bloc dans le mode « par blocs »."""
    if len(texte) <= SEUIL_PASSE_UNIQUE_CHARS:
        return _completer(
            client, construire_prompt(texte, lang), 0.4, MAX_TOKENS_PASSE_UNIQUE, "Génération de la fiche"
        )

    blocs = decouper_en_blocs(texte)
    total = len(blocs)
    logger.info(f"  Résumé par blocs : {len(texte):,} caractères en {total} bloc(s)")

    notes = []
    for i, bloc in enumerate(blocs, 1):
        if on_progress:
            on_progress(summary_current=i, summary_total=total)
        notes.append(_completer(
            client, construire_prompt_bloc(bloc, lang, i, total), 0.3, MAX_TOKENS_NOTES_BLOC,
            f"Notes du bloc {i}/{total}",
        ))

    if on_progress:
        on_progress(summary_current=total + 1, summary_total=total + 1)
    return _completer(
        client, construire_prompt_fusion(notes, lang), 0.4, MAX_TOKENS_FUSION, "Fusion des notes"
    )
