"""
Store de jobs de transcription asynchrones (fichiers JSON sur disque).

Le backend tourne avec plusieurs workers Uvicorn (voir Dockerfile) : un
dict en mémoire ne serait pas visible d'un worker à l'autre si la requête
de création du job et celle de polling du statut sont routées vers des
processus différents. Le système de fichiers du conteneur, lui, est
partagé entre les workers — d'où ce store, volontairement simple (pas de
Redis pour une poignée de jobs concurrents sur un usage personnel).
"""
import json
import os
import tempfile
import time
import uuid
from typing import Optional

JOB_DIR = os.path.join(tempfile.gettempdir(), "pac_jobs")
JOB_MAX_AGE_SEC = 2 * 3600  # jobs orphelins (jamais relus) nettoyés après 2h


def _job_path(job_id: str) -> str:
    return os.path.join(JOB_DIR, f"{job_id}.json")


def _write_json_atomic(path: str, data: dict) -> None:
    """Écrit `data` en JSON de façon atomique (fichier tmp + rename) pour
    qu'une lecture concurrente ne voie jamais un fichier tronqué."""
    tmp_path = f"{path}.tmp-{os.getpid()}-{uuid.uuid4().hex}"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp_path, path)


def _cleanup_stale_jobs() -> None:
    """Supprime les fichiers de job plus vieux que JOB_MAX_AGE_SEC — filet de
    sécurité pour les jobs dont le résultat n'a jamais été récupéré par le
    client (onglet fermé, requête abandonnée avant le premier polling, etc.)."""
    try:
        now = time.time()
        for name in os.listdir(JOB_DIR):
            path = os.path.join(JOB_DIR, name)
            try:
                if now - os.path.getmtime(path) > JOB_MAX_AGE_SEC:
                    os.remove(path)
            except OSError:
                pass
    except FileNotFoundError:
        pass


def create_job() -> str:
    """Crée un nouveau job en statut "processing" et retourne son identifiant."""
    os.makedirs(JOB_DIR, exist_ok=True)
    _cleanup_stale_jobs()
    job_id = uuid.uuid4().hex
    _write_json_atomic(_job_path(job_id), {
        "status": "processing",
        "step": "cutting",
        "created_at": time.time(),
    })
    return job_id


def update_job(job_id: str, **fields) -> None:
    """Fusionne `fields` dans l'état existant du job (no-op silencieux si le
    fichier a déjà été nettoyé : le client a abandonné le job entre-temps)."""
    path = _job_path(job_id)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return
    data.update(fields)
    _write_json_atomic(path, data)


def get_job(job_id: str) -> Optional[dict]:
    """Retourne l'état du job, ou None s'il n'existe pas (jamais créé, déjà
    récupéré et supprimé, ou nettoyé après expiration)."""
    try:
        with open(_job_path(job_id), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def delete_job(job_id: str) -> None:
    try:
        os.remove(_job_path(job_id))
    except OSError:
        pass
