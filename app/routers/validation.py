"""Validations communes aux routes qui lancent un traitement ou reçoivent de l'audio."""
from typing import Optional

from fastapi import HTTPException, UploadFile

from app.config import LANGUAGE
from app.i18n import SUPPORTED_LANGS, t
from app.services import pipeline
from app.services.audio import allowed_file, ALLOWED_EXTENSIONS

MODES = ("summary", "transcript")


def valider_lang_et_mode(lang: str, mode: str) -> None:
    """Valide lang/client/mode d'une requête qui lance un traitement (fichier
    complet ou fin d'enregistrement). Lève HTTPException sinon."""
    if lang not in SUPPORTED_LANGS:
        # Langue inconnue : le message sort dans la langue configurée du serveur.
        raise HTTPException(status_code=400, detail=t("invalid_lang", LANGUAGE))

    if not pipeline.client:
        raise HTTPException(status_code=503, detail=t("groq_not_configured", lang))

    if mode not in MODES:
        raise HTTPException(status_code=400, detail=t("invalid_mode", lang))


def valider_fichier_audio(audio: Optional[UploadFile], lang: str) -> None:
    """Vérifie qu'un fichier audio est présent et que son extension est
    acceptée. Lève HTTPException sinon."""
    if audio is None or not audio.filename:
        raise HTTPException(status_code=400, detail=t("no_audio_file", lang))

    if not allowed_file(audio.filename):
        raise HTTPException(
            status_code=415,
            detail=t("unsupported_format", lang, formats=", ".join(sorted(ALLOWED_EXTENSIONS)))
        )
