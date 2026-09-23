"""
Routes de transcription : upload audio -> découpage -> transcription -> fiche Markdown.
"""
import os
import subprocess
import tempfile
import threading
import time
import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from groq import APIError
from werkzeug.utils import secure_filename

from app.config import CHUNK_DURATION, LANGUAGE, MAX_UPLOAD_SIZE_MB, RATE_LIMIT_PROCESS, client, logger
from app.i18n import SUPPORTED_LANGS, t
from app.limiter import limiter
from app.services.audio import allowed_file, découper_audio, obtenir_duree_audio, ALLOWED_EXTENSIONS
from app.services.jobs import create_job, delete_job, get_job, update_job
from app.services.prompt import construire_prompt
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


def _valider_requete(lang: str, audio: Optional[UploadFile], mode: str) -> None:
    """Valide lang/client/audio/mode communs aux deux points d'entrée
    (synchrone et asynchrone). Lève HTTPException sinon."""
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


@router.post('/process')
@router.post('/api/transcribe')  # alias explicite pour les clients API/PWA
@limiter.limit(RATE_LIMIT_PROCESS)
def process(
    request: Request,
    audio: Optional[UploadFile] = File(None),
    mode: str = Form("summary"),
    lang: str = Form(LANGUAGE),
):

    # --- Vérifications préalables ---
    # `lang` est validé en premier : tous les messages d'erreur suivants
    # doivent être dans une langue confirmée.
    _valider_requete(lang, audio, mode)

    # --- Sauvegarde sécurisée ---
    filename = secure_filename(audio.filename)
    if not filename:
        # Fallback si le nom contient uniquement des caractères non-ASCII
        filename = f"audio_{os.getpid()}.mp3"

    # Identifiant unique par requête (pas le PID : avec plusieurs workers/threads,
    # deux requêtes concurrentes peuvent partager le même PID et donc, si le PID
    # seul suffisait, écraser/lire le fichier temporaire l'une de l'autre en cas
    # de nom de fichier identique — ex. deux utilisateurs uploadant "cours.mp3"
    # en même temps).
    request_id    = uuid.uuid4().hex
    input_path    = os.path.join(tempfile.gettempdir(), f"{request_id}_{filename}")
    chunks_créés  = []

    try:
        _sauvegarder_avec_limite(audio.file, input_path, MAX_UPLOAD_SIZE_BYTES, lang)
        size_mo = os.path.getsize(input_path) / 1024 / 1024
        logger.info(f"📥 Fichier reçu : {filename} ({size_mo:.1f} Mo)")

        # Mesure du temps de traitement total (hors upload) et de la durée
        # audio réelle — sert uniquement à alimenter les stats/logs (aucun
        # impact sur le comportement métier).
        début_traitement = time.perf_counter()
        durée_audio_sec = obtenir_duree_audio(input_path)

        # --- 1. Découpage ---
        logger.info("✂️  Découpage en chunks...")
        chunks_créés = découper_audio(input_path, request_id, duree_totale_sec=durée_audio_sec)

        if not chunks_créés:
            raise HTTPException(
                status_code=422,
                detail=t("ffmpeg_unreadable", lang)
            )

        logger.info(f"✅ {len(chunks_créés)} chunk(s) prêts à transcrire")

        # --- 2. Transcription chunk par chunk ---
        logger.info("🎙️  Transcription Whisper...")
        texte_complet = ""
        segments_horodatés = []

        for i, path in enumerate(chunks_créés):
            logger.info(f"  [{i+1}/{len(chunks_créés)}] {os.path.basename(path)}")
            texte_chunk, segments = transcrire_chunk(path)
            texte_complet += texte_chunk + " "

            offset = i * CHUNK_DURATION
            for seg in segments:
                segments_horodatés.append({
                    "start": seg["start"] + offset,
                    "text": seg["text"],
                })

            os.remove(path)  # Nettoyage immédiat après transcription

        if not texte_complet.strip():
            raise HTTPException(
                status_code=422,
                detail=t("transcription_empty", lang)
            )

        logger.info(f"✅ Transcription complète : {len(texte_complet):,} caractères")

        response_body = {
            "mode": mode,
            "stats": {
                "chunks":               len(chunks_créés),
                "transcription_chars":  len(texte_complet)
            }
        }

        # --- 3. Structuration LLM (uniquement en mode résumé) ---
        if mode == "summary":
            logger.info("🧠 Structuration par IA...")
            completion = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": construire_prompt(texte_complet, lang)}],
                temperature=0.4,
                max_tokens=4096
            )

            response_body["markdown"] = completion.choices[0].message.content
            logger.info("✅ Fiche générée avec succès")
        else:
            logger.info("⏭️  Mode transcription basique — pas d'appel LLM")
            response_body["transcript"] = "\n".join(
                f"[{_formater_horodatage(seg['start'])}] {seg['text']}"
                for seg in segments_horodatés
                if seg["text"]
            )

        # --- Stats de performance (mesure uniquement, aucun impact fonctionnel) ---
        temps_traitement_sec = time.perf_counter() - début_traitement
        response_body["stats"]["audio_duration_sec"] = (
            round(durée_audio_sec, 2) if durée_audio_sec is not None else None
        )
        response_body["stats"]["processing_time_sec"] = round(temps_traitement_sec, 2)

        if durée_audio_sec:
            ratio = durée_audio_sec / temps_traitement_sec
            logger.info(
                f"⏱️  {_formater_horodatage(durée_audio_sec)} audio traité en "
                f"{temps_traitement_sec:.1f}s (ratio {ratio:.0f}x)"
            )
        else:
            logger.info(f"⏱️  Traitement terminé en {temps_traitement_sec:.1f}s (durée audio inconnue)")

        return JSONResponse(response_body)

    # --- Gestion d'erreurs granulaire ---
    except HTTPException:
        raise

    except subprocess.TimeoutExpired:
        logger.error("FFmpeg timeout global")
        raise HTTPException(status_code=504, detail=t("ffmpeg_timeout", lang))

    except RuntimeError as e:
        logger.error(f"Erreur transcription: {e}")
        raise HTTPException(status_code=502, detail=t("transcription_error", lang, error=str(e)))

    except APIError as e:
        logger.error(f"Erreur API Groq: {e}")
        raise HTTPException(status_code=502, detail=t("groq_api_error", lang, error=e.message))

    except Exception:
        logger.exception("Erreur inattendue dans /process")
        raise HTTPException(status_code=500, detail=t("internal_error", lang))

    finally:
        # Nettoyage garanti même en cas d'exception à mi-parcours
        for path in chunks_créés:
            if os.path.exists(path):
                os.remove(path)
                logger.debug(f"Chunk supprimé : {path}")
        if os.path.exists(input_path):
            os.remove(input_path)
            logger.info(f"Fichier original supprimé : {input_path}")


def _traiter_job(job_id: str, input_path: str, filename: str, mode: str, lang: str) -> None:
    """Exécute le pipeline complet (découpage -> transcription -> résumé) en
    tâche de fond et écrit le résultat (ou l'erreur) dans le store de jobs.

    Miroir de la logique de `process()` ci-dessus, adapté pour ne jamais lever
    d'exception HTTP : ce n'est plus une requête HTTP en cours (personne ne
    l'attraperait), donc chaque erreur est directement écrite comme statut
    final du job, à charge pour GET /api/transcribe/status/{job_id} de la
    retraduire en HTTPException au moment où le client la récupère.
    """
    chunks_créés = []
    try:
        size_mo = os.path.getsize(input_path) / 1024 / 1024
        logger.info(f"📥 [job {job_id}] Fichier reçu : {filename} ({size_mo:.1f} Mo)")

        début_traitement = time.perf_counter()
        durée_audio_sec = obtenir_duree_audio(input_path)

        # --- 1. Découpage ---
        logger.info(f"✂️  [job {job_id}] Découpage en chunks...")
        update_job(job_id, step="cutting")
        chunks_créés = découper_audio(input_path, job_id, duree_totale_sec=durée_audio_sec)

        if not chunks_créés:
            update_job(job_id, status="error", http_status=422, detail=t("ffmpeg_unreadable", lang))
            return

        logger.info(f"✅ [job {job_id}] {len(chunks_créés)} chunk(s) prêts à transcrire")

        # --- 2. Transcription chunk par chunk ---
        logger.info(f"🎙️  [job {job_id}] Transcription Whisper...")
        update_job(job_id, step="whisper", chunk_total=len(chunks_créés))
        texte_complet = ""
        segments_horodatés = []

        for i, path in enumerate(chunks_créés):
            update_job(job_id, chunk_current=i + 1)
            logger.info(f"  [job {job_id}] [{i+1}/{len(chunks_créés)}] {os.path.basename(path)}")
            texte_chunk, segments = transcrire_chunk(path)
            texte_complet += texte_chunk + " "

            offset = i * CHUNK_DURATION
            for seg in segments:
                segments_horodatés.append({
                    "start": seg["start"] + offset,
                    "text": seg["text"],
                })

            os.remove(path)  # Nettoyage immédiat après transcription

        if not texte_complet.strip():
            update_job(job_id, status="error", http_status=422, detail=t("transcription_empty", lang))
            return

        logger.info(f"✅ [job {job_id}] Transcription complète : {len(texte_complet):,} caractères")

        response_body = {
            "mode": mode,
            "stats": {
                "chunks":               len(chunks_créés),
                "transcription_chars":  len(texte_complet)
            }
        }

        # --- 3. Structuration LLM (uniquement en mode résumé) ---
        if mode == "summary":
            logger.info(f"🧠 [job {job_id}] Structuration par IA...")
            update_job(job_id, step="llm")
            completion = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": construire_prompt(texte_complet, lang)}],
                temperature=0.4,
                max_tokens=4096
            )

            response_body["markdown"] = completion.choices[0].message.content
            logger.info(f"✅ [job {job_id}] Fiche générée avec succès")
        else:
            logger.info(f"⏭️  [job {job_id}] Mode transcription basique — pas d'appel LLM")
            response_body["transcript"] = "\n".join(
                f"[{_formater_horodatage(seg['start'])}] {seg['text']}"
                for seg in segments_horodatés
                if seg["text"]
            )

        # --- Stats de performance (mesure uniquement, aucun impact fonctionnel) ---
        temps_traitement_sec = time.perf_counter() - début_traitement
        response_body["stats"]["audio_duration_sec"] = (
            round(durée_audio_sec, 2) if durée_audio_sec is not None else None
        )
        response_body["stats"]["processing_time_sec"] = round(temps_traitement_sec, 2)

        if durée_audio_sec:
            ratio = durée_audio_sec / temps_traitement_sec
            logger.info(
                f"⏱️  [job {job_id}] {_formater_horodatage(durée_audio_sec)} audio traité en "
                f"{temps_traitement_sec:.1f}s (ratio {ratio:.0f}x)"
            )
        else:
            logger.info(f"⏱️  [job {job_id}] Traitement terminé en {temps_traitement_sec:.1f}s (durée audio inconnue)")

        update_job(job_id, status="done", result=response_body)

    except subprocess.TimeoutExpired:
        logger.error(f"FFmpeg timeout global [job {job_id}]")
        update_job(job_id, status="error", http_status=504, detail=t("ffmpeg_timeout", lang))

    except RuntimeError as e:
        logger.error(f"Erreur transcription [job {job_id}]: {e}")
        update_job(job_id, status="error", http_status=502, detail=t("transcription_error", lang, error=str(e)))

    except APIError as e:
        logger.error(f"Erreur API Groq [job {job_id}]: {e}")
        update_job(job_id, status="error", http_status=502, detail=t("groq_api_error", lang, error=e.message))

    except Exception:
        logger.exception(f"Erreur inattendue dans le traitement du job {job_id}")
        update_job(job_id, status="error", http_status=500, detail=t("internal_error", lang))

    finally:
        for path in chunks_créés:
            if os.path.exists(path):
                os.remove(path)
                logger.debug(f"Chunk supprimé : {path}")
        if os.path.exists(input_path):
            os.remove(input_path)
            logger.info(f"Fichier original supprimé : {input_path}")


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
    - en cours : {"status": "processing", "step": ..., "chunk_current": ..., "chunk_total": ...}
    - terminé  : {"status": "done", ...corps identique à la réponse synchrone de /process}
    - échoué   : HTTPException avec le même code/message que /process aurait renvoyé

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
        raise HTTPException(status_code=job["http_status"], detail=job["detail"])

    if job["status"] == "done":
        delete_job(job_id)
        return JSONResponse({"status": "done", **job["result"]})

    return JSONResponse({
        "status": "processing",
        "step": job.get("step"),
        "chunk_current": job.get("chunk_current"),
        "chunk_total": job.get("chunk_total"),
    })
