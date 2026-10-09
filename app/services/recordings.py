"""
Stockage des enregistrements par segments (fichiers sur disque).

Le backend tourne avec plusieurs workers Uvicorn : comme pour les jobs
(app/services/jobs.py), l'état est donc dans le système de fichiers, partagé
entre workers. Un enregistrement = un dossier `pac_recordings/<id>/` contenant
un fichier par segment (`seg_0000.<ext>`, `seg_0001.<ext>`…).

L'audio n'y reste que le temps de la réunion puis du traitement : le dossier est
supprimé à la fin du job, ou au bout de RECORDING_MAX_AGE_SEC s'il est abandonné.
"""
import json
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
_RESULT_RE = re.compile(r"^res_(\d{4})\.(json|working)$")
# Une transcription anticipée « en cours » plus ancienne que ça est considérée comme morte
# (worker redémarré) : on cesse de l'attendre.
WORKING_STALE_SEC = 10 * 60


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
        # Le contenu a changé : une transcription anticipée de l'ancienne version ne vaut plus rien.
        supprimer_resultat(rec_id, index)
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


# --- Transcription anticipée des segments ---
# Chaque segment reçu est transcrit en tâche de fond pendant la réunion ; son résultat est
# gardé à côté du segment (res_NNNN.json). À la fin, le pipeline réutilise ces résultats au
# lieu de tout retranscrire. Un résultat porte la « signature » du fichier qu'il décrit : si le
# segment est renvoyé avec un autre contenu, l'ancien résultat est ignoré.


def chemin_segment(rec_id: str, index: int) -> Optional[str]:
    return _segments(rec_id).get(index) if existe(rec_id) else None


def index_du_chemin(chemin: str) -> Optional[int]:
    m = _SEGMENT_RE.match(os.path.basename(chemin))
    return int(m.group(1)) if m else None


def indices_et_chemins(rec_id: str) -> list[tuple[int, str]]:
    segments = _segments(rec_id)
    return [(i, segments[i]) for i in sorted(segments)]


def _signature(chemin: str) -> str:
    stat = os.stat(chemin)
    return f"{stat.st_size}:{stat.st_mtime_ns}"


def _fichier_resultat(rec_id: str, index: int, extension: str = "json") -> Optional[str]:
    dossier = _dossier(rec_id)
    return os.path.join(dossier, f"res_{index:04d}.{extension}") if dossier else None


def marquer_en_cours(rec_id: str, index: int) -> None:
    """Signale qu'une transcription anticipée de ce segment est lancée (ou en attente de son tour)."""
    marqueur = _fichier_resultat(rec_id, index, "working")
    try:
        with open(marqueur, "w") as f:
            f.write(str(time.time()))
    except OSError:
        pass


def fin_en_cours(rec_id: str, index: int) -> None:
    marqueur = _fichier_resultat(rec_id, index, "working")
    try:
        os.remove(marqueur)
    except (OSError, TypeError):
        pass


def signature_segment(rec_id: str, index: int) -> Optional[str]:
    """Signature du fichier du segment tel qu'il est maintenant. À relever AVANT de le transcrire :
    si le segment est renvoyé pendant la transcription, le résultat périmé garde l'ancienne
    signature et sera rejeté à la lecture."""
    chemin = chemin_segment(rec_id, index)
    try:
        return _signature(chemin) if chemin else None
    except OSError:
        return None


def sauver_resultat(rec_id: str, index: int, donnees: dict, signature: str) -> None:
    """Écrit le résultat de la transcription anticipée du segment `index` (écriture atomique),
    avec la signature du fichier tel qu'il était quand la transcription a commencé."""
    cible = _fichier_resultat(rec_id, index)
    if not cible or not signature:
        return
    temporaire = f"{cible}.part-{uuid.uuid4().hex}"
    try:
        with open(temporaire, "w", encoding="utf-8") as f:
            json.dump({**donnees, "signature": signature}, f)
        os.replace(temporaire, cible)
    except OSError:
        pass
    finally:
        if os.path.exists(temporaire):
            os.remove(temporaire)


def lire_resultat(rec_id: str, index: int) -> Optional[dict]:
    """Résultat de la transcription anticipée du segment, ou None s'il n'existe pas ou s'il
    décrit une version du segment qui a changé depuis."""
    chemin = chemin_segment(rec_id, index)
    cible = _fichier_resultat(rec_id, index)
    if not chemin or not cible:
        return None
    try:
        with open(cible, encoding="utf-8") as f:
            donnees = json.load(f)
        if donnees.get("signature") != _signature(chemin):
            return None
        return donnees
    except (OSError, ValueError):
        return None


def supprimer_resultat(rec_id: str, index: int) -> None:
    for extension in ("json", "working"):
        cible = _fichier_resultat(rec_id, index, extension)
        try:
            os.remove(cible)
        except (OSError, TypeError):
            pass


def attendre_en_cours(rec_id: str, timeout_sec: float) -> bool:
    """Attend la fin des transcriptions anticipées en cours (pour ne pas retranscrire un segment
    qu'une tâche de fond est en train de traiter). Retourne False si le délai est dépassé."""
    dossier = _dossier(rec_id)
    limite = time.monotonic() + timeout_sec
    while dossier and os.path.isdir(dossier):
        en_cours = False
        for nom in os.listdir(dossier):
            m = _RESULT_RE.match(nom)
            if m and m.group(2) == "working":
                try:
                    if time.time() - os.path.getmtime(os.path.join(dossier, nom)) < WORKING_STALE_SEC:
                        en_cours = True
                except OSError:
                    pass
        if not en_cours:
            return True
        if time.monotonic() >= limite:
            return False
        time.sleep(0.25)
    return True
