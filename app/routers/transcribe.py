"""
Routes de transcription : upload audio -> découpage -> transcription -> fiche Markdown.
"""
import os
import subprocess
import tempfile
import time
import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from groq import APIError
from werkzeug.utils import secure_filename

from app.config import CHUNK_DURATION, MAX_UPLOAD_SIZE_MB, RATE_LIMIT_PROCESS, client, logger
from app.limiter import limiter
from app.services.audio import allowed_file, découper_audio, obtenir_duree_audio, ALLOWED_EXTENSIONS
from app.services.prompt import construire_prompt
from app.services.transcription import transcrire_chunk

router = APIRouter()

_UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 Mo par bloc de copie
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


def _sauvegarder_avec_limite(source, destination_path: str, max_bytes: int) -> None:
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
                    detail=f"Fichier trop volumineux (max {MAX_UPLOAD_SIZE_MB} Mo)"
                )
            f.write(block)


def _formater_horodatage(secondes: float) -> str:
    """Formate un nombre de secondes en mm:ss (ou h:mm:ss au-delà d'une heure)."""
    total = int(secondes)
    h, reste = divmod(total, 3600)
    m, s = divmod(reste, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


@router.post('/process')
@router.post('/api/transcribe')  # alias explicite pour les clients API/PWA
@limiter.limit(RATE_LIMIT_PROCESS)
def process(request: Request, audio: Optional[UploadFile] = File(None), mode: str = Form("summary")):

    # --- Vérifications préalables ---
    if not client:
        raise HTTPException(status_code=503, detail="Configuration API Groq manquante sur le serveur")

    if audio is None or not audio.filename:
        raise HTTPException(status_code=400, detail="Aucun fichier audio reçu")

    if mode not in ("summary", "transcript"):
        raise HTTPException(status_code=400, detail="Mode invalide (attendu : 'summary' ou 'transcript')")

    if not allowed_file(audio.filename):
        raise HTTPException(
            status_code=415,
            detail=f"Format non supporté. Formats acceptés : {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

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
        _sauvegarder_avec_limite(audio.file, input_path, MAX_UPLOAD_SIZE_BYTES)
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
                detail="Impossible de traiter le fichier audio (vide, corrompu, ou format non lisible par FFmpeg)"
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
                detail="Transcription vide — audio silencieux, inaudible ou langue incorrecte ?"
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
                messages=[{"role": "user", "content": construire_prompt(texte_complet)}],
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
        raise HTTPException(status_code=504, detail="Le découpage audio a pris trop de temps")

    except RuntimeError as e:
        logger.error(f"Erreur transcription: {e}")
        raise HTTPException(status_code=502, detail=str(e))

    except APIError as e:
        logger.error(f"Erreur API Groq: {e}")
        raise HTTPException(status_code=502, detail=f"Erreur API Groq : {e.message}")

    except Exception:
        logger.exception("Erreur inattendue dans /process")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

    finally:
        # Nettoyage garanti même en cas d'exception à mi-parcours
        for path in chunks_créés:
            if os.path.exists(path):
                os.remove(path)
                logger.debug(f"Chunk supprimé : {path}")
        if os.path.exists(input_path):
            os.remove(input_path)
            logger.info(f"Fichier original supprimé : {input_path}")
