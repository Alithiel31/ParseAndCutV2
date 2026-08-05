"""
Routes de transcription : upload audio -> découpage -> transcription -> fiche Markdown.
"""
import os
import shutil
import subprocess
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from groq import APIError
from werkzeug.utils import secure_filename

from app.config import client, logger
from app.services.audio import allowed_file, découper_audio, ALLOWED_EXTENSIONS
from app.services.prompt import construire_prompt
from app.services.transcription import transcrire_chunk

router = APIRouter()


@router.post('/process')
@router.post('/api/transcribe')  # alias explicite pour les clients API/PWA
def process(audio: Optional[UploadFile] = File(None)):

    # --- Vérifications préalables ---
    if not client:
        raise HTTPException(status_code=503, detail="Configuration API Groq manquante sur le serveur")

    if audio is None or not audio.filename:
        raise HTTPException(status_code=400, detail="Aucun fichier audio reçu")

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

    # Préfixe PID pour éviter les collisions entre requêtes simultanées
    input_path    = f"/tmp/{os.getpid()}_{filename}"
    chunks_créés  = []

    try:
        with open(input_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)
        size_mo = os.path.getsize(input_path) / 1024 / 1024
        logger.info(f"📥 Fichier reçu : {filename} ({size_mo:.1f} Mo)")

        # --- 1. Découpage ---
        logger.info("✂️  Découpage en chunks...")
        chunks_créés = découper_audio(input_path)

        if not chunks_créés:
            raise HTTPException(
                status_code=422,
                detail="Impossible de traiter le fichier audio (vide, corrompu, ou format non lisible par FFmpeg)"
            )

        logger.info(f"✅ {len(chunks_créés)} chunk(s) prêts à transcrire")

        # --- 2. Transcription chunk par chunk ---
        logger.info("🎙️  Transcription Whisper...")
        texte_complet = ""

        for i, path in enumerate(chunks_créés):
            logger.info(f"  [{i+1}/{len(chunks_créés)}] {os.path.basename(path)}")
            texte_complet += transcrire_chunk(path) + " "
            os.remove(path)  # Nettoyage immédiat après transcription

        if not texte_complet.strip():
            raise HTTPException(
                status_code=422,
                detail="Transcription vide — audio silencieux, inaudible ou langue incorrecte ?"
            )

        logger.info(f"✅ Transcription complète : {len(texte_complet):,} caractères")

        # --- 3. Structuration LLM ---
        logger.info("🧠 Structuration avec Llama 3...")
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": construire_prompt(texte_complet)}],
            temperature=0.4,
            max_tokens=4096
        )

        markdown = completion.choices[0].message.content
        logger.info("✅ Fiche générée avec succès")

        return JSONResponse({
            "markdown": markdown,
            "stats": {
                "chunks":               len(chunks_créés),
                "transcription_chars":  len(texte_complet)
            }
        })

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
