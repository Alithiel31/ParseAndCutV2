"""
Routes de transcription : upload audio -> découpage -> transcription -> fiche Markdown.

Le traitement est toujours asynchrone (POST /api/transcribe/start puis
GET /api/transcribe/status/{job_id}) : une réponse HTTP unique dépasserait le
timeout de 100 s de Cloudflare dès quelques minutes d'audio. Le pipeline
lui-même vit dans app/services/pipeline.py ; ce module ne fait que valider la
requête, stocker l'upload et exposer l'état du job.
"""
import os
import tempfile
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from werkzeug.utils import secure_filename

from app.config import LANGUAGE, MAX_UPLOAD_SIZE_MB, RATE_LIMIT_PROCESS
from app.i18n import SUPPORTED_LANGS, t
from app.limiter import limiter
from app.routers.validation import valider_fichier_audio, valider_lang_et_mode
from app.services import pipeline
from app.services.jobs import create_job, delete_job, get_job

router = APIRouter()

_UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 Mo par bloc de copie
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


def _sauvegarder_avec_limite(source, destination_path: str, max_bytes: int, lang: str) -> None:
    """Copie `source` (UploadFile.file) vers `destination_path` par blocs, en
    interrompant et en supprimant le fichier partiel si `max_bytes` est dépassé."""
    total = 0
    with open(destination_path, "wb") as f:
        while True:
            block = source.read(_UPLOAD_CHUNK_SIZE)
            if not block:
                break
            total += len(block)
            if total > max_bytes:
                f.close()
                os.remove(destination_path)
                raise HTTPException(
                    status_code=413,
                    detail=t("file_too_large", lang, max_mb=MAX_UPLOAD_SIZE_MB)
                )
            f.write(block)


@router.post('/api/transcribe/start')
@limiter.limit(RATE_LIMIT_PROCESS)
def transcribe_start(
    request: Request,
    audio: Optional[UploadFile] = File(None),
    mode: str = Form("summary"),
    lang: str = Form(LANGUAGE),
):
    """Démarre un job de transcription en tâche de fond et retourne aussitôt
    un `job_id` à interroger via GET /api/transcribe/status/{job_id}.

    Nécessaire pour contourner le timeout fixe de 100s imposé par Cloudflare
    sur les plans Free/Pro/Business (edge response timeout, non réglable en
    dehors d'Enterprise) : au-delà de quelques minutes d'audio, le pipeline
    complet (découpage + transcription chunk par chunk + résumé) dépasse
    cette fenêtre et Cloudflare coupe la connexion (524) avant que le Pi ait
    fini de répondre — même si le traitement backend aurait fini par aboutir.
    """
    valider_lang_et_mode(lang, mode)
    valider_fichier_audio(audio, lang)

    filename = secure_filename(audio.filename)
    if not filename:
        filename = f"audio_{os.getpid()}.mp3"

    job_id = create_job()
    input_path = os.path.join(tempfile.gettempdir(), f"{job_id}_{filename}")

    try:
        _sauvegarder_avec_limite(audio.file, input_path, MAX_UPLOAD_SIZE_BYTES, lang)
    except HTTPException:
        delete_job(job_id)
        raise

    pipeline.en_tache_de_fond(pipeline.traiter_fichier, job_id, input_path, mode, lang)

    return JSONResponse({"job_id": job_id}, status_code=202)


@router.get('/api/transcribe/status/{job_id}')
def transcribe_status(job_id: str, lang: str = LANGUAGE):
    """Renvoie l'état d'un job créé par POST /api/transcribe/start :
    - en cours : {"status": "processing", "step": ..., "chunk_current": ..., "chunk_total": ...,
                  "summary_current": ..., "summary_total": ...}
    - terminé  : {"status": "done", mode, stats, markdown | transcript}
    - échoué   : code et message de l'échec, plus
                 `partial_transcript` si une partie a déjà été transcrite

    Le job est supprimé du store dès qu'un statut terminal (done/error) a été
    lu une première fois : chaque job n'est consommé qu'une seule fois par un
    client qui, lui, ne fait que sonder son propre job_id.
    """
    if lang not in SUPPORTED_LANGS:
        lang = LANGUAGE

    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=t("job_not_found", lang))

    if job["status"] == "error":
        delete_job(job_id)
        # Même forme que HTTPException ({"detail": ...}) ; `partial_transcript`
        # n'est ajouté que si une partie de l'audio a pu être transcrite avant
        # l'échec (réseau, quota Groq, panne du résumé IA…).
        partial = job.get("partial_transcript")
        if partial:
            return JSONResponse(
                {"detail": job["detail"], "partial_transcript": partial},
                status_code=job["http_status"],
            )
        raise HTTPException(status_code=job["http_status"], detail=job["detail"])

    if job["status"] == "done":
        delete_job(job_id)
        return JSONResponse({"status": "done", **job["result"]})

    return JSONResponse({
        "status": "processing",
        "step": job.get("step"),
        "chunk_current": job.get("chunk_current"),
        "chunk_total": job.get("chunk_total"),
        "summary_current": job.get("summary_current"),
        "summary_total": job.get("summary_total"),
    })
