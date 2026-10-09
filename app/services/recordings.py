"""
Stockage des enregistrements par segments (fichiers sur disque).

Le backend tourne avec plusieurs workers Uvicorn : comme pour les jobs
(app/services/jobs.py), l'état est donc dans le système de fichiers, partagé
entre workers. Un enregistrement = un dossier `pac_recordings/<id>/` contenant
un fichier par segment (`seg_0000.<ext>`, `seg_0001.<ext>`…).

L'audio n'y reste que le temps de la réunion puis du traitement : le dossier est
supprimé à la fin du job, ou au bout de RECORDING_MAX_AGE_SEC s'il est abandonné.
"""
import os
import re
import shutil
import tempfile
import time
import uuid
from typing import Optional

REC_DIR = os.path.join(tempfile.gettempdir(), "pac_recordings")
RECORDING_MAX_AGE_SEC = 6 * 3600  # enregistrement jamais terminé : nettoyé après 6 h

_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_SEGMENT_RE = re.compile(r"^seg_(\d{4})\.[a-z0-9]+$")
_FINISHED_MARKER = ".finished"


class SegmentTropGros(Exception):
    pass


class EnregistrementTropGros(Exception):
    pass


def _dossier(rec_id: str) -> Optional[str]:
    """Chemin du dossier de l'enregistrement, ou None si l'identifiant n'a pas
    la forme attendue (jamais de chemin construit à partir d'une entrée brute)."""
    if not _ID_RE.match(rec_id or ""):
        return None
    return os.path.join(REC_DIR, rec_id)


def _nettoyer_anciens() -> None:
    try:
        maintenant = time.time()
        for nom in os.listdir(REC_DIR):
            chemin = os.path.join(REC_DIR, nom)
            try:
                if maintenant - os.path.getmtime(chemin) > RECORDING_MAX_AGE_SEC:
                    shutil.rmtree(chemin, ignore_errors=True)
            except OSError:
                pass
    except FileNotFoundError:
        pass


def creer_enregistrement() -> str:
    os.makedirs(REC_DIR, exist_ok=True)
    _nettoyer_anciens()
    rec_id = uuid.uuid4().hex
    os.makedirs(os.path.join(REC_DIR, rec_id))
    return rec_id


def existe(rec_id: str) -> bool:
    dossier = _dossier(rec_id)
    return dossier is not None and os.path.isdir(dossier)


def est_termine(rec_id: str) -> bool:
    dossier = _dossier(rec_id)
    return dossier is not None and os.path.exists(os.path.join(dossier, _FINISHED_MARKER))


def marquer_termine(rec_id: str) -> bool:
    """Pose le marqueur « traitement lancé » de façon atomique. Retourne False
    s'il existait déjà : deux appels simultanés à /finish ne lancent qu'un job."""
    dossier = _dossier(rec_id)
    try:
        fd = os.open(os.path.join(dossier, _FINISHED_MARKER), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    os.close(fd)
    return True


def _segments(rec_id: str) -> dict[int, str]:
    dossier = _dossier(rec_id)
    trouves: dict[int, str] = {}
    for nom in os.listdir(dossier):
        m = _SEGMENT_RE.match(nom)
        if m:
            trouves[int(m.group(1))] = os.path.join(dossier, nom)
    return trouves


def indices_recus(rec_id: str) -> list[int]:
    return sorted(_segments(rec_id))


def taille_totale(rec_id: str) -> int:
    return sum(os.path.getsize(p) for p in _segments(rec_id).values())


def enregistrer_segment(
    rec_id: str, index: int, extension: str, source, max_segment_bytes: int, max_total_bytes: int
) -> None:
    """Copie `source` (flux binaire) vers le segment `index`, par blocs de 1 Mo.
    Idempotent : renvoyer le même index remplace le segment précédent (renvoi
    après une coupure réseau). L'écriture passe par un fichier temporaire puis
    un renommage atomique : un segment n'est jamais lu à moitié écrit."""
    dossier = _dossier(rec_id)
    deja = _segments(rec_id)
    autres = sum(os.path.getsize(p) for i, p in deja.items() if i != index)

    destination = os.path.join(dossier, f"seg_{index:04d}.{extension}")
    temporaire = f"{destination}.part-{uuid.uuid4().hex}"
    total = 0
    try:
        with open(temporaire, "wb") as f:
            while True:
                bloc = source.read(1024 * 1024)
                if not bloc:
                    break
                total += len(bloc)
                if total > max_segment_bytes:
                    raise SegmentTropGros()
                if autres + total > max_total_bytes:
                    raise EnregistrementTropGros()
                f.write(bloc)
        # Un ancien envoi du même index avec une autre extension est remplacé.
        if index in deja and deja[index] != destination:
            os.remove(deja[index])
        os.replace(temporaire, destination)
    finally:
        if os.path.exists(temporaire):
            os.remove(temporaire)


def segments_manquants(rec_id: str) -> list[int]:
    """Indices absents entre 0 et le dernier segment reçu (trous dans la suite)."""
    recus = indices_recus(rec_id)
    if not recus:
        return []
    return [i for i in range(recus[-1] + 1) if i not in set(recus)]


def chemins_ordonnes(rec_id: str) -> list[str]:
    segments = _segments(rec_id)
    return [segments[i] for i in sorted(segments)]


def supprimer(rec_id: str) -> None:
    dossier = _dossier(rec_id)
    if dossier:
        shutil.rmtree(dossier, ignore_errors=True)
