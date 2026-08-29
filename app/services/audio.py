"""
Découpage et validation des fichiers audio (FFmpeg).
"""
import os
import re
import subprocess
import tempfile
from typing import Optional

from app.config import ALLOWED_EXTENSIONS, CHUNK_DURATION, FFMPEG_PATH, logger

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d{2}):(\d{2})\.(\d+)")


def allowed_file(filename: str) -> bool:
    """Vérifie que l'extension du fichier est autorisée."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def obtenir_duree_audio(input_path: str) -> Optional[float]:
    """Interroge FFmpeg pour obtenir la durée totale du fichier audio, en secondes.
    Retourne None si FFmpeg est indisponible ou si la durée n'a pas pu être lue
    (fichier vide/corrompu) — non bloquant, à usage purement informatif/mesure."""
    try:
        probe = subprocess.run(
            [FFMPEG_PATH, "-i", input_path],
            capture_output=True, text=True, timeout=30
        )
    except Exception:
        return None

    # FFmpeg écrit les infos (dont "Duration: HH:MM:SS.xx, ...") sur stderr
    for line in probe.stderr.splitlines():
        match = _DURATION_RE.search(line)
        if match:
            h, m, s, frac = match.groups()
            return int(h) * 3600 + int(m) * 60 + int(s) + int(frac) / 10 ** len(frac)
    return None


def découper_audio(
    input_path: str,
    request_id: str,
    interval_sec: int = CHUNK_DURATION,
    duree_totale_sec: Optional[float] = None,
) -> list[str]:
    """
    Découpe l'audio en chunks MP3 pour l'API Groq (limite 25 Mo par chunk).
    10 min à 128k ≈ 9,6 Mo — bien en dessous de la limite Groq.
    1h d'audio = ~6 chunks traités séquentiellement.
    `request_id` (unique par requête) évite toute collision de noms de chunks
    entre deux requêtes concurrentes traitées par le même worker.
    `duree_totale_sec`, si déjà connue (cf. `obtenir_duree_audio`), évite de
    reprober le fichier ici — sinon elle est calculée à la volée pour le log.
    Retourne la liste ordonnée des chemins de chunks créés.
    """
    chunks = []
    part   = 0

    if duree_totale_sec is None:
        duree_totale_sec = obtenir_duree_audio(input_path)
    if duree_totale_sec is not None:
        logger.info(f"Durée détectée : {duree_totale_sec:.1f}s")

    while True:
        start_time = part * interval_sec
        chunk_path = os.path.join(tempfile.gettempdir(), f"chunk_{request_id}_{part}.mp3")

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
