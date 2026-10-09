"""
Enregistrement par segments : le navigateur envoie l'audio au fil de la réunion
(un segment autonome toutes les ~5 min) puis demande le traitement à la fin.

    POST /api/recordings                              crée l'enregistrement
    GET  /api/recordings/{id}                         segments déjà reçus (reprise après plantage)
    POST /api/recordings/{id}/segments/{n}            envoie le segment n (idempotent)
    POST /api/recordings/{id}/finish                  lance le traitement -> job_id
    POST /api/recordings/{id}/cancel                  abandonne et supprime l'audio

Seules les méthodes GET/POST sont utilisées : ce sont les seules autorisées par
la config CORS (app/main.py). Le traitement lui-même réutilise le pipeline et le
suivi de job de /api/transcribe (GET /api/transcribe/status/{job_id}).
"""
import threading
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from app.config import (
    LANGUAGE, MAX_RECORDING_SIZE_MB, MAX_SEGMENT_SIZE_MB, MAX_SEGMENTS, RATE_LIMIT_PROCESS,
    RATE_LIMIT_SEGMENTS, RECORDING_EARLY_TRANSCRIPTION, RECORDING_SEGMENT_SEC,
)
from app.i18n import SUPPORTED_LANGS, t
from app.limiter import limiter
from app.routers import transcribe
from app.services import recordings
from app.services.audio import ALLOWED_EXTENSIONS
from app.services.jobs import create_job

router = APIRouter()

# slowapi compte par défaut « par chemin d'URL complet » : avec un identifiant
# d'enregistrement ou un numéro de segment dans le chemin, chaque URL aurait son
# propre compteur et la limite ne s'appliquerait jamais. `scope` force un
# compteur unique par IP pour tout un groupe de routes.
SCOPE_SEGMENTS = "recordings-segments"
SCOPE_DEMARRAGE = "recordings-start"


def _langue(lang: str) -> str:
    """Langue des messages : repli silencieux sur la langue par défaut (ces
    routes ne produisent pas de contenu, seulement des messages d'erreur)."""
    return lang if lang in SUPPORTED_LANGS else LANGUAGE


def _exiger_enregistrement(rec_id: str, lang: str) -> None:
    if not recordings.existe(rec_id):
        raise HTTPException(status_code=404, detail=t("recording_not_found", lang))


@router.post('/api/recordings')
@limiter.shared_limit(RATE_LIMIT_PROCESS, scope=SCOPE_DEMARRAGE)
def creer(request: Request, lang: str = LANGUAGE):
    lang = _langue(lang)
    # Mieux vaut refuser dès le début d'une réunion que 2 h plus tard.
    if not transcribe.client:
        raise HTTPException(status_code=503, detail=t("groq_not_configured", lang))

    return JSONResponse({
        "recording_id": recordings.creer_enregistrement(),
        "segment_seconds": RECORDING_SEGMENT_SEC,
        "max_segment_mb": MAX_SEGMENT_SIZE_MB,
    }, status_code=201)


@router.get('/api/recordings/{rec_id}')
def etat(rec_id: str, lang: str = LANGUAGE):
    """Segments que le serveur a déjà reçus : permet au client, après un
    rechargement de page, de ne renvoyer que ce qui manque."""
    lang = _langue(lang)
    _exiger_enregistrement(rec_id, lang)
    return {
        "recording_id": rec_id,
        "segments": recordings.indices_recus(rec_id),
        "finished": recordings.est_termine(rec_id),
    }


@router.post('/api/recordings/{rec_id}/segments/{index}')
@limiter.shared_limit(RATE_LIMIT_SEGMENTS, scope=SCOPE_SEGMENTS)
def envoyer_segment(
    request: Request,
    rec_id: str,
    index: int,
    audio: Optional[UploadFile] = File(None),
    lang: str = Form(LANGUAGE),
):
    lang = _langue(lang)
    _exiger_enregistrement(rec_id, lang)

    if recordings.est_termine(rec_id):
        raise HTTPException(status_code=409, detail=t("recording_finished", lang))
    if not 0 <= index < MAX_SEGMENTS:
        raise HTTPException(
            status_code=400, detail=t("segment_invalid_index", lang, max_index=MAX_SEGMENTS - 1)
        )
    if audio is None or not audio.filename:
        raise HTTPException(status_code=400, detail=t("no_audio_file", lang))

    extension = audio.filename.rsplit(".", 1)[-1].lower() if "." in audio.filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=t("unsupported_format", lang, formats=", ".join(sorted(ALLOWED_EXTENSIONS))),
        )

    try:
        recordings.enregistrer_segment(
            rec_id, index, extension, audio.file,
            MAX_SEGMENT_SIZE_MB * 1024 * 1024, MAX_RECORDING_SIZE_MB * 1024 * 1024,
        )
    except recordings.SegmentTropGros:
        raise HTTPException(status_code=413, detail=t("segment_too_large", lang, max_mb=MAX_SEGMENT_SIZE_MB))
    except recordings.EnregistrementTropGros:
        raise HTTPException(
            status_code=413, detail=t("recording_too_large", lang, max_mb=MAX_RECORDING_SIZE_MB)
        )

    # Transcrit ce segment tout de suite, pendant que la réunion continue.
    if RECORDING_EARLY_TRANSCRIPTION:
        transcribe.lancer_transcription_en_avance(rec_id, index)

    return {"index": index, "segments": recordings.indices_recus(rec_id)}


@router.post('/api/recordings/{rec_id}/finish')
@limiter.shared_limit(RATE_LIMIT_PROCESS, scope=SCOPE_DEMARRAGE)
def terminer(
    request: Request,
    rec_id: str,
    mode: str = Form("summary"),
    lang: str = Form(LANGUAGE),
):
    """Vérifie que la suite de segments est complète, puis lance le même job de
    fond qu'un fichier envoyé d'un bloc. Le client suit ensuite le job avec
    GET /api/transcribe/status/{job_id}."""
    if lang not in SUPPORTED_LANGS:
        raise HTTPException(status_code=400, detail=t("invalid_lang", LANGUAGE))
    if not transcribe.client:
        raise HTTPException(status_code=503, detail=t("groq_not_configured", lang))
    if mode not in ("summary", "transcript"):
        raise HTTPException(status_code=400, detail=t("invalid_mode", lang))
    _exiger_enregistrement(rec_id, lang)

    if not recordings.indices_recus(rec_id):
        raise HTTPException(status_code=400, detail=t("recording_empty", lang))

    manquants = recordings.segments_manquants(rec_id)
    if manquants:
        # Le client peut renvoyer ces segments depuis son stockage local puis réessayer.
        return JSONResponse(
            {"detail": t("segments_missing", lang, missing=", ".join(map(str, manquants))), "missing": manquants},
            status_code=409,
        )

    if not recordings.marquer_termine(rec_id):
        raise HTTPException(status_code=409, detail=t("recording_finished", lang))

    job_id = create_job()
    threading.Thread(
        target=transcribe._traiter_enregistrement,
        args=(job_id, rec_id, mode, lang),
        daemon=True,
    ).start()
    return JSONResponse({"job_id": job_id}, status_code=202)


@router.post('/api/recordings/{rec_id}/cancel')
def annuler(rec_id: str, lang: str = LANGUAGE):
    """Abandonne l'enregistrement et supprime tout l'audio reçu. Sans effet si
    le traitement est déjà lancé : il supprime lui-même l'audio à sa fin."""
    lang = _langue(lang)
    _exiger_enregistrement(rec_id, lang)
    if not recordings.est_termine(rec_id):
        recordings.supprimer(rec_id)
    return {"cancelled": True}
