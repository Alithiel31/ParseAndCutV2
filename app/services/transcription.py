"""
Transcription des chunks audio via l'API Groq Whisper.
"""
import os
import re
from typing import Optional

from app.config import client, logger
from app.services.groq_retry import MAX_TENTATIVES, executer_avec_reessais


# --- Filtre d'hallucinations -------------------------------------------------
# Sur du silence ou du bruit, Whisper « complète » avec des textes vus à
# l'entraînement : fins de vidéos YouTube, sous-titres. Deux critères :
#  1. le signal propre à Whisper : segment probablement sans parole
#     (no_speech_prob élevé) ET peu fiable (avg_logprob bas) ;
#  2. des phrases connues, jamais plausibles dans un cours ou une réunion
#     (supprimées sans condition), ou courtes et ambiguës comme « you » ou
#     « merci » (supprimées seulement si Whisper doute qu'il y ait de la parole).
NO_SPEECH_PROB_MAX = 0.6
AVG_LOGPROB_MIN = -1.0
NO_SPEECH_PROB_AMBIGU = 0.2

_PHRASES_TOUJOURS_HALLUCINEES = (
    "sous-titrage société radio-canada",
    "sous-titrage st' 501",
    "sous-titres réalisés par la communauté d'amara.org",
    "sous-titres réalisés para la communauté d'amara.org",
    "amara.org",
    "thanks for watching",
    "thank you for watching",
    "merci d'avoir regardé cette vidéo",
    "merci d'avoir regardé",
    "n'oubliez pas de vous abonner",
    "subtitles by the amara.org community",
)
_PHRASES_AMBIGUES = {"you", "thank you", "thanks", "merci", "bye", "bye bye", "okay", "ok"}
_RE_NON_ALNUM = re.compile(r"[^\w'\-\.\s]", re.UNICODE)


def _normaliser(texte: str) -> str:
    return " ".join(_RE_NON_ALNUM.sub(" ", texte.lower()).split()).strip(" .")


def _est_hallucination(texte: str, no_speech_prob: Optional[float], avg_logprob: Optional[float]) -> bool:
    if (
        no_speech_prob is not None and avg_logprob is not None
        and no_speech_prob > NO_SPEECH_PROB_MAX and avg_logprob < AVG_LOGPROB_MIN
    ):
        return True

    normalise = _normaliser(texte)
    if not normalise:
        return True

    if any(phrase in normalise for phrase in _PHRASES_TOUJOURS_HALLUCINEES):
        return True

    # « you », « you you », « thank you thank you »… : le motif répété aussi.
    mots = normalise.split()
    for phrase in _PHRASES_AMBIGUES:
        unite = phrase.split()
        if len(mots) % len(unite) == 0 and mots == unite * (len(mots) // len(unite)):
            return no_speech_prob is not None and no_speech_prob > NO_SPEECH_PROB_AMBIGU

    return False


def transcrire_chunk(path: str, retries: int = MAX_TENTATIVES) -> tuple[str, list[dict]]:
    """
    Transcrit un chunk audio via Groq Whisper.
    Retente automatiquement les erreurs transitoires (voir groq_retry).

    La langue parlée est toujours auto-détectée par Whisper (language=None),
    indépendamment de la langue de sortie choisie par l'utilisateur pour la
    fiche générée (voir app.services.prompt) : ce sont deux réglages
    indépendants.

    Les segments que Whisper a probablement inventés sur du silence sont
    écartés (voir `_est_hallucination`), texte compris.

    Retourne (texte_complet, segments) où segments est la liste des
    passages horodatés : [{"start": float, "end": float, "text": str}, ...]
    (temps en secondes, relatifs au début de ce chunk).
    """
    nom = os.path.basename(path)

    def _appeler_whisper():
        with open(path, "rb") as f:
            return client.audio.transcriptions.create(
                file=(nom, f.read()),
                model="whisper-large-v3",
                language=None,
                response_format="verbose_json"
            )

    result = executer_avec_reessais(_appeler_whisper, f"Transcription du chunk {nom}", retries)

    # "segments" n'est pas un champ typé du modèle Transcription du SDK Groq
    # (extra="allow") : c'est du JSON brut désérialisé en dicts, pas en objets.
    segments = []
    ignorés = 0
    for seg in result.segments:
        texte_seg = seg["text"].strip()
        if _est_hallucination(texte_seg, seg.get("no_speech_prob"), seg.get("avg_logprob")):
            ignorés += 1
            continue
        segments.append({"start": seg["start"], "end": seg["end"], "text": texte_seg})

    if ignorés:
        logger.info(f"  {ignorés} segment(s) ignoré(s) dans {nom} (hallucination probable sur silence/bruit)")
        return " ".join(seg["text"] for seg in segments), segments
    return result.text, segments
