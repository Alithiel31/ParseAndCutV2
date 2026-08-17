"""
Découpage et validation des fichiers audio (FFmpeg).
"""
import os
import subprocess
import tempfile

from app.config import ALLOWED_EXTENSIONS, CHUNK_DURATION, FFMPEG_PATH, logger


def allowed_file(filename: str) -> bool:
    """Vérifie que l'extension du fichier est autorisée."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def découper_audio(input_path: str, interval_sec: int = CHUNK_DURATION) -> list[str]:
    """
    Découpe l'audio en chunks MP3 pour l'API Groq (limite 25 Mo par chunk).
    10 min à 128k ≈ 9,6 Mo — bien en dessous de la limite Groq.
    1h d'audio = ~6 chunks traités séquentiellement.
    Retourne la liste ordonnée des chemins de chunks créés.
    """
    chunks = []
    part   = 0

    # Vérifie d'abord la durée totale pour logger une estimation
    try:
        probe = subprocess.run(
            [FFMPEG_PATH, "-i", input_path],
            capture_output=True, text=True, timeout=30
        )
        # FFmpeg écrit les infos sur stderr
        for line in probe.stderr.splitlines():
            if "Duration" in line:
                logger.info(f"Durée détectée : {line.strip()}")
                break
    except Exception:
        pass  # Non bloquant

    while True:
        start_time = part * interval_sec
        chunk_path = os.path.join(tempfile.gettempdir(), f"chunk_{os.getpid()}_{part}.mp3")

        cmd = [
            FFMPEG_PATH,
            "-ss", str(start_time),
            "-t",  str(interval_sec),
            "-i",  input_path,
            "-vn",                      # Ignore la piste vidéo si présente (mp4)
            "-acodec", "libmp3lame",
            "-ab",     "128k",
            "-loglevel", "error",       # Supprime les logs verbeux FFmpeg
            chunk_path, "-y"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode != 0:
                logger.warning(
                    f"FFmpeg avertissement chunk {part}: "
                    f"{result.stderr.decode(errors='replace')[:200]}"
                )
        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg timeout sur chunk {part}")
            break

        # Un chunk valide fait au moins 5 Ko
        if not os.path.exists(chunk_path) or os.path.getsize(chunk_path) < 5000:
            if os.path.exists(chunk_path):
                os.remove(chunk_path)
            break

        size_kb = os.path.getsize(chunk_path) // 1024
        logger.info(f"  Chunk {part} créé ({size_kb} Ko)")
        chunks.append(chunk_path)
        part += 1

    return chunks
