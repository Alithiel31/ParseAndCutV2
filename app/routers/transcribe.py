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

from app.config import (
    CHUNK_DURATION, LANGUAGE, MAX_UPLOAD_SIZE_MB, RATE_LIMIT_PROCESS, RECORDING_SEGMENT_SEC, client, logger,
)
from app.i18n import SUPPORTED_LANGS, t
from app.limiter import limiter
from app.services.audio import (
    allowed_file, convertir_en_mp3, découper_audio, est_silencieux, obtenir_duree_audio, ALLOWED_EXTENSIONS,
)
from app.services import recordings
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


MODES = ("summary", "transcript")


def valider_lang_et_mode(lang: str, mode: str) -> None:
    """Valide lang/client/mode d'une requête qui lance un traitement (fichier
    complet ou fin d'enregistrement). Lève HTTPException sinon."""
    if lang not in SUPPORTED_LANGS:
        raise HTTPException(status_code=400, detail=t("invalid_lang", lang))

    if not client:
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


def _transcrire_et_structurer(
    chunks: list[Optional[str]],
    offsets: list[float],
    durée_audio_sec: Optional[float],
    début_traitement: float,
    mode: str,
    lang: str,
    on_progress: Optional[Callable[..., None]],
    log_prefix: str,
    déjà_transcrits: Optional[dict[int, Optional[tuple[str, list[dict]]]]] = None,
) -> dict:
    """Étapes communes à tous les points d'entrée une fois l'audio découpé en
    chunks : transcription chunk par chunk, puis résumé. `offsets[i]` est le
    début (en secondes) du chunk i dans l'enregistrement complet. Supprime
    chaque chunk dès qu'il est transcrit ; les restes sont à nettoyer par
    l'appelant en cas d'exception.

    `déjà_transcrits[i]`, s'il existe, est le résultat d'une transcription faite à l'avance
    (pendant l'enregistrement) : (texte, segments), ou None si ce chunk était silencieux. Le
    chunk i n'a alors plus de fichier (`chunks[i]` vaut None) et ne coûte aucun appel."""
    déjà_transcrits = déjà_transcrits or {}
    # --- 2. Transcription chunk par chunk ---
    logger.info(f"🎙️  {log_prefix}Transcription Whisper...")
    if on_progress:
        on_progress(step="whisper", chunk_total=len(chunks))
    texte_complet = ""
    segments_horodatés = []
    chunks_silencieux = 0

    for i, path in enumerate(chunks):
        if on_progress:
            on_progress(chunk_current=i + 1)

        if i in déjà_transcrits:
            logger.info(f"  {log_prefix}[{i+1}/{len(chunks)}] déjà transcrit pendant l'enregistrement")
            résultat = déjà_transcrits[i]
            if résultat is None:
                chunks_silencieux += 1
                continue
            texte_chunk, segments = résultat
        else:
            logger.info(f"  {log_prefix}[{i+1}/{len(chunks)}] {os.path.basename(path)}")

            # Un chunk de silence numérique (micro coupé) ferait halluciner
            # Whisper et consommerait du quota Groq pour rien.
            if est_silencieux(path):
                logger.warning(f"  {log_prefix}chunk {i+1} silencieux — ignoré")
                chunks_silencieux += 1
                os.remove(path)
                continue

            texte_chunk, segments = transcrire_chunk(path)
            os.remove(path)  # Nettoyage immédiat après transcription

        texte_complet += texte_chunk + " "

        offset = offsets[i]
        for seg in segments:
            segments_horodatés.append({
                "start": seg["start"] + offset,
                "text": seg["text"],
            })

        if on_progress:
            on_progress(partial_transcript=_formater_transcript(segments_horodatés))

    if not texte_complet.strip():
        raison = "audio_silent" if chunks_silencieux == len(chunks) else "transcription_empty"
        raise _ErreurPipeline(422, t(raison, lang))

    logger.info(f"✅ {log_prefix}Transcription complète : {len(texte_complet):,} caractères")

    response_body = {
        "mode": mode,
        "stats": {
            "chunks":               len(chunks),
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

        return _transcrire_et_structurer(
            chunks_créés,
            [i * CHUNK_DURATION for i in range(len(chunks_créés))],
            durée_audio_sec, début_traitement, mode, lang, on_progress, log_prefix,
        )

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


def _executer_pipeline_segments(
    segments: list[str],
    pipeline_id: str,
    mode: str,
    lang: str,
    on_progress: Optional[Callable[..., None]] = None,
    log_prefix: str = "",
    rec_id: Optional[str] = None,
) -> dict:
    """Pipeline pour un enregistrement envoyé par segments : chaque segment
    (déjà court et autonome) devient un chunk MP3, sans nouveau découpage.
    Les décalages d'horodatage viennent de la durée réelle de chaque segment.
    Un segment illisible est ignoré (sa durée nominale est comptée pour garder
    les horodatages suivants à peu près justes) ; si aucun n'est lisible, échec.
    Si `rec_id` est fourni, un segment déjà transcrit pendant l'enregistrement
    (voir `_transcrire_segment_en_avance`) est réutilisé tel quel : ni conversion
    ni appel Whisper. Supprime ses propres chunks, pas les segments d'origine."""
    chunks_créés: list[Optional[str]] = []
    try:
        début_traitement = time.perf_counter()
        if on_progress:
            on_progress(step="cutting")

        offsets: list[float] = []
        déjà_transcrits: dict[int, Optional[tuple[str, list[dict]]]] = {}
        position = 0.0
        for i, source in enumerate(segments):
            à_l_avance = None
            if rec_id is not None:
                index = recordings.index_du_chemin(source)
                à_l_avance = recordings.lire_resultat(rec_id, index) if index is not None else None

            if à_l_avance is not None:
                # Transcrit pendant la réunion : on garde le texte, la durée et le fait qu'il était silencieux.
                déjà_transcrits[len(chunks_créés)] = (
                    None if à_l_avance.get("silencieux") else (à_l_avance["texte"], à_l_avance["segments"])
                )
                chunks_créés.append(None)
                offsets.append(position)
                position += à_l_avance.get("durée") or RECORDING_SEGMENT_SEC
                continue

            chunk = os.path.join(tempfile.gettempdir(), f"chunk_{pipeline_id}_{i}.mp3")
            if not convertir_en_mp3(source, chunk):
                logger.warning(f"  {log_prefix}segment {i} illisible — ignoré")
                position += RECORDING_SEGMENT_SEC
                continue
            chunks_créés.append(chunk)
            offsets.append(position)
            position += obtenir_duree_audio(chunk) or RECORDING_SEGMENT_SEC

        if not chunks_créés:
            raise _ErreurPipeline(422, t("ffmpeg_unreadable", lang))

        logger.info(
            f"✅ {log_prefix}{len(chunks_créés)}/{len(segments)} segment(s) prêts "
            f"({len(déjà_transcrits)} déjà transcrit(s) pendant l'enregistrement)"
        )
        return _transcrire_et_structurer(
            chunks_créés, offsets, position, début_traitement, mode, lang, on_progress, log_prefix,
            déjà_transcrits=déjà_transcrits,
        )

    finally:
        for path in chunks_créés:
            if path and os.path.exists(path):
                os.remove(path)


# Au plus 2 transcriptions anticipées simultanées par processus : à la reprise d'un enregistrement,
# tous les segments arrivent d'un coup et ne doivent pas lancer autant d'appels Whisper en parallèle.
_TRANSCRIPTIONS_EN_AVANCE = threading.BoundedSemaphore(2)
# Attente maximale, à la fin, des transcriptions anticipées encore en cours.
ATTENTE_TRANSCRIPTIONS_EN_AVANCE_SEC = 300


def _transcrire_segment_en_avance(rec_id: str, index: int) -> None:
    """Transcrit un segment dès son arrivée, en tâche de fond, et garde le résultat à côté du
    segment. Toute erreur est avalée (sans résultat enregistré) : à la fin, le pipeline
    retranscrira simplement ce segment lui-même. Le marqueur « en cours » est posé par l'appelant,
    avant le lancement du thread, pour que la fin de l'enregistrement sache qu'il faut attendre."""
    chunk = os.path.join(tempfile.gettempdir(), f"early_{rec_id}_{index}.mp3")
    try:
        with _TRANSCRIPTIONS_EN_AVANCE:
            # Relevée AVANT la transcription : si le segment est renvoyé entre-temps, ce résultat
            # périmé sera rejeté à la lecture.
            signature = recordings.signature_segment(rec_id, index)
            source = recordings.chemin_segment(rec_id, index)
            if not signature or not source:
                return
            if not convertir_en_mp3(source, chunk):
                return  # segment illisible : le pipeline final le signalera

            durée = obtenir_duree_audio(chunk)
            if est_silencieux(chunk):
                recordings.sauver_resultat(rec_id, index, {"silencieux": True, "durée": durée}, signature)
                return
            texte, segments = transcrire_chunk(chunk)
            recordings.sauver_resultat(
                rec_id, index, {"silencieux": False, "durée": durée, "texte": texte, "segments": segments}, signature
            )
            logger.info(f"🎙️  Segment {index} de {rec_id[:8]} transcrit pendant l'enregistrement")
    except Exception:
        logger.warning(f"Transcription anticipée du segment {index} de {rec_id[:8]} impossible", exc_info=True)
    finally:
        if os.path.exists(chunk):
            os.remove(chunk)
        recordings.fin_en_cours(rec_id, index)


def lancer_transcription_en_avance(rec_id: str, index: int) -> None:
    """Lance la transcription anticipée du segment `index` en tâche de fond."""
    if not client:
        return
    recordings.marquer_en_cours(rec_id, index)  # avant le thread : la fin ne doit pas passer entre deux
    threading.Thread(target=_transcrire_segment_en_avance, args=(rec_id, index), daemon=True).start()


def _traiter_enregistrement(job_id: str, rec_id: str, mode: str, lang: str) -> None:
    """Tâche de fond d'un enregistrement par segments : même contrat que
    `_traiter_job` (résultat ou erreur écrits dans le job), puis suppression de
    l'audio du serveur."""
    try:
        # Une transcription anticipée encore en cours (typiquement celle du dernier segment, reçu
        # juste avant la fin) est attendue plutôt que refaite.
        if not recordings.attendre_en_cours(rec_id, ATTENTE_TRANSCRIPTIONS_EN_AVANCE_SEC):
            logger.warning(f"[job {job_id}] transcriptions anticipées trop longues : le reste est fait ici")
        résultat = _executer_pipeline_segments(
            recordings.chemins_ordonnes(rec_id), job_id, mode, lang,
            on_progress=lambda **champs: update_job(job_id, **champs),
            log_prefix=f"[job {job_id}] ",
            rec_id=rec_id,
        )
        update_job(job_id, status="done", result=résultat)

    except Exception as exc:
        status, detail = _traduire_erreur(exc, lang)
        update_job(job_id, status="error", http_status=status, detail=detail)

    finally:
        recordings.supprimer(rec_id)


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
