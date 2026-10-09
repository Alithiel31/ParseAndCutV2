"""
Routes de transcription : upload audio -> découpage -> transcription -> fiche Markdown.

Le traitement est toujours asynchrone (POST /api/transcribe/start puis
GET /api/transcribe/status/{job_id}) : une réponse HTTP unique dépasserait le
timeout de 100 s de Cloudflare dès quelques minutes d'audio.
"""
import os
import subprocess
import tempfile
import threading
import time
from typing import Callable, Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from groq import APIError
from werkzeug.utils import secure_filename

from app.config import CHUNK_DURATION, LANGUAGE, MAX_UPLOAD_SIZE_MB, RATE_LIMIT_PROCESS, client, logger
from app.i18n import SUPPORTED_LANGS, t
from app.limiter import limiter
from app.services.audio import allowed_file, découper_audio, est_silencieux, obtenir_duree_audio, ALLOWED_EXTENSIONS
from app.services.jobs import create_job, delete_job, get_job, update_job
from app.services.summary import generer_fiche
from app.services.transcription import transcrire_chunk

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


def _formater_horodatage(secondes: float) -> str:
    """Formate un nombre de secondes en mm:ss (ou h:mm:ss au-delà d'une heure)."""
    total = int(secondes)
    h, reste = divmod(total, 3600)
    m, s = divmod(reste, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _formater_transcript(segments: list[dict]) -> str:
    """Transcription horodatée « [mm:ss] texte », une ligne par segment non vide."""
    return "\n".join(
        f"[{_formater_horodatage(seg['start'])}] {seg['text']}"
        for seg in segments
        if seg["text"]
    )


def _valider_requete(lang: str, audio: Optional[UploadFile], mode: str) -> None:
    """Valide lang/client/audio/mode de la requête de démarrage. Lève
    HTTPException sinon."""
    if lang not in SUPPORTED_LANGS:
        raise HTTPException(status_code=400, detail=t("invalid_lang", lang))

    if not client:
        raise HTTPException(status_code=503, detail=t("groq_not_configured", lang))

    if audio is None or not audio.filename:
        raise HTTPException(status_code=400, detail=t("no_audio_file", lang))

    if mode not in ("summary", "transcript"):
        raise HTTPException(status_code=400, detail=t("invalid_mode", lang))

    if not allowed_file(audio.filename):
        raise HTTPException(
            status_code=415,
            detail=t("unsupported_format", lang, formats=", ".join(sorted(ALLOWED_EXTENSIONS)))
        )


class _ErreurPipeline(Exception):
    """Échec « métier » du pipeline, déjà associé à son code HTTP et à son
    message traduit (découpage illisible, transcription vide…)."""

    def __init__(self, http_status: int, detail: str):
        super().__init__(detail)
        self.http_status = http_status
        self.detail = detail


def _traduire_erreur(exc: Exception, lang: str) -> tuple[int, str]:
    """Convertit une exception du pipeline en (code HTTP, message traduit).
    Le job de fond l'écrit comme statut final du job ; le endpoint de statut
    la retraduit en réponse HTTP quand le client la récupère."""
    if isinstance(exc, _ErreurPipeline):
        return exc.http_status, exc.detail

    if isinstance(exc, subprocess.TimeoutExpired):
        logger.error("FFmpeg timeout global")
        return 504, t("ffmpeg_timeout", lang)

    if isinstance(exc, RuntimeError):
        logger.error(f"Erreur transcription: {exc}")
        return 502, t("transcription_error", lang, error=str(exc))

    if isinstance(exc, APIError):
        logger.error(f"Erreur API Groq: {exc}")
        return 502, t("groq_api_error", lang, error=exc.message)

    logger.error("Erreur inattendue dans le traitement", exc_info=exc)
    return 500, t("internal_error", lang)


def _supprimer_fichier_entree(input_path: str) -> None:
    if os.path.exists(input_path):
        os.remove(input_path)
        logger.info(f"Fichier original supprimé : {input_path}")


def _executer_pipeline(
    input_path: str,
    pipeline_id: str,
    mode: str,
    lang: str,
    on_progress: Optional[Callable[..., None]] = None,
    log_prefix: str = "",
) -> dict:
    """Pipeline complet : découpage -> transcription chunk par chunk -> résumé.

    Retourne le corps de la réponse ; lève `_ErreurPipeline` (ou l'exception d'origine) en cas
    d'échec, à charge pour l'appelant de la traduire via `_traduire_erreur`.
    `on_progress(**champs)`, si fourni, reçoit l'étape courante (step,
    chunk_total, chunk_current) et, après chaque chunk transcrit, la
    transcription cumulée (partial_transcript) : si une étape ultérieure
    échoue, ce qui a déjà été transcrit n'est pas perdu.
    Supprime ses propres chunks, pas `input_path`.
    """
    chunks_créés: list[str] = []
    try:
        size_mo = os.path.getsize(input_path) / 1024 / 1024
        logger.info(f"📥 {log_prefix}Fichier reçu : {os.path.basename(input_path)} ({size_mo:.1f} Mo)")

        # Mesure du temps de traitement total (hors upload) et de la durée
        # audio réelle — sert uniquement à alimenter les stats/logs (aucun
        # impact sur le comportement métier).
        début_traitement = time.perf_counter()
        durée_audio_sec = obtenir_duree_audio(input_path)

        # --- 1. Découpage ---
        logger.info(f"✂️  {log_prefix}Découpage en chunks...")
        if on_progress:
            on_progress(step="cutting")
        chunks_créés = découper_audio(input_path, pipeline_id, duree_totale_sec=durée_audio_sec)

        if not chunks_créés:
            raise _ErreurPipeline(422, t("ffmpeg_unreadable", lang))

        logger.info(f"✅ {log_prefix}{len(chunks_créés)} chunk(s) prêts à transcrire")

        # --- 2. Transcription chunk par chunk ---
        logger.info(f"🎙️  {log_prefix}Transcription Whisper...")
        if on_progress:
            on_progress(step="whisper", chunk_total=len(chunks_créés))
        texte_complet = ""
        segments_horodatés = []
        chunks_silencieux = 0

        for i, path in enumerate(chunks_créés):
            if on_progress:
                on_progress(chunk_current=i + 1)
            logger.info(f"  {log_prefix}[{i+1}/{len(chunks_créés)}] {os.path.basename(path)}")

            # Un chunk de silence numérique (micro coupé) ferait halluciner
            # Whisper et consommerait du quota Groq pour rien.
            if est_silencieux(path):
                logger.warning(f"  {log_prefix}chunk {i+1} silencieux — ignoré")
                chunks_silencieux += 1
                os.remove(path)
                continue

            texte_chunk, segments = transcrire_chunk(path)
            texte_complet += texte_chunk + " "

            offset = i * CHUNK_DURATION
            for seg in segments:
                segments_horodatés.append({
                    "start": seg["start"] + offset,
                    "text": seg["text"],
                })

            os.remove(path)  # Nettoyage immédiat après transcription

            if on_progress:
                on_progress(partial_transcript=_formater_transcript(segments_horodatés))

        if not texte_complet.strip():
            raison = "audio_silent" if chunks_silencieux == len(chunks_créés) else "transcription_empty"
            raise _ErreurPipeline(422, t(raison, lang))

        logger.info(f"✅ {log_prefix}Transcription complète : {len(texte_complet):,} caractères")

        response_body = {
            "mode": mode,
            "stats": {
                "chunks":               len(chunks_créés),
                "transcription_chars":  len(texte_complet),
                "silent_chunks":        chunks_silencieux
            }
        }

        # --- 3. Structuration LLM (uniquement en mode résumé) ---
        if mode == "summary":
            logger.info(f"🧠 {log_prefix}Structuration par IA...")
            if on_progress:
                on_progress(step="llm")
            response_body["markdown"] = generer_fiche(client, texte_complet, lang, on_progress)
            logger.info(f"✅ {log_prefix}Fiche générée avec succès")
        else:
            logger.info(f"⏭️  {log_prefix}Mode transcription basique — pas d'appel LLM")
            response_body["transcript"] = _formater_transcript(segments_horodatés)

        # --- Stats de performance (mesure uniquement, aucun impact fonctionnel) ---
        temps_traitement_sec = time.perf_counter() - début_traitement
        response_body["stats"]["audio_duration_sec"] = (
            round(durée_audio_sec, 2) if durée_audio_sec is not None else None
        )
        response_body["stats"]["processing_time_sec"] = round(temps_traitement_sec, 2)

        if durée_audio_sec:
            ratio = durée_audio_sec / temps_traitement_sec
            logger.info(
                f"⏱️  {log_prefix}{_formater_horodatage(durée_audio_sec)} audio traité en "
                f"{temps_traitement_sec:.1f}s (ratio {ratio:.0f}x)"
            )
        else:
            logger.info(f"⏱️  {log_prefix}Traitement terminé en {temps_traitement_sec:.1f}s (durée audio inconnue)")

        return response_body

    finally:
        # Nettoyage garanti des chunks restants, même en cas d'exception
        for path in chunks_créés:
            if os.path.exists(path):
                os.remove(path)
                logger.debug(f"Chunk supprimé : {path}")


def _traiter_job(job_id: str, input_path: str, filename: str, mode: str, lang: str) -> None:
    """Exécute le pipeline en tâche de fond et écrit le résultat (ou l'erreur)
    dans le store de jobs.

    Ce n'est plus une requête HTTP en cours (personne n'attraperait une
    HTTPException) : chaque erreur est directement écrite comme statut final
    du job, à charge pour GET /api/transcribe/status/{job_id} de la
    retraduire en HTTPException au moment où le client la récupère.
    """
    try:
        résultat = _executer_pipeline(
            input_path, job_id, mode, lang,
            on_progress=lambda **champs: update_job(job_id, **champs),
            log_prefix=f"[job {job_id}] ",
        )
        update_job(job_id, status="done", result=résultat)

    except Exception as exc:
        status, detail = _traduire_erreur(exc, lang)
        update_job(job_id, status="error", http_status=status, detail=detail)

    finally:
        _supprimer_fichier_entree(input_path)


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
    _valider_requete(lang, audio, mode)

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

    threading.Thread(
        target=_traiter_job,
        args=(job_id, input_path, filename, mode, lang),
        daemon=True,
    ).start()

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
