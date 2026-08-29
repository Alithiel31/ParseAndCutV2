#!/usr/bin/env python3
"""
Script de benchmark pour l'API de transcription ParseAndCutV2.

Mesure, sur un ensemble de fichiers audio de test, le ratio "durée audio
traitée" / "temps de traitement serveur" renvoyé par /api/transcribe
(champs stats.audio_duration_sec et stats.processing_time_sec), afin
d'obtenir un chiffre communicable ("X minutes d'audio transcrites en Y
secondes") et une estimation du temps de transcription manuelle évité.

Usage
-----
    python scripts/benchmark_transcription.py DOSSIER_AUDIO \\
        [--url http://localhost:5000/api/transcribe] \\
        [--mode summary|transcript] \\
        [--repeats 3] \\
        [--manual-ratio 5.0] \\
        [--timeout 600]

DOSSIER_AUDIO doit contenir un ou plusieurs fichiers audio de test
(extensions supportées : mp3, mp4, wav, m4a, ogg, webm, flac, aac, opus).

Le serveur ParseAndCutV2 doit déjà tourner (ex: `uvicorn app.main:app`)
et être joignable à --url. Chaque fichier est envoyé --repeats fois ; la
médiane des temps de traitement est retenue (pour lisser la variance
réseau/API Groq). --manual-ratio est le nombre de minutes de travail
manuel estimées par minute d'audio (5:1 par défaut, càd 5 min de travail
manuel pour 1 min d'audio).

Exemple :
    python scripts/benchmark_transcription.py tests/fixtures/audio --repeats 3

Dépendance : httpx (déjà présent dans requirements.txt).
"""
import argparse
import statistics
import sys
import time
from pathlib import Path
from typing import Optional

import httpx

AUDIO_EXTENSIONS = {".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac", ".opus"}


def _formater_duree(secondes: float) -> str:
    """mm:ss (ou h:mm:ss au-delà d'une heure) — même logique que l'API."""
    total = int(secondes)
    h, reste = divmod(total, 3600)
    m, s = divmod(reste, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def transcrire_un_fichier(client: httpx.Client, url: str, path: Path, mode: str) -> Optional[dict]:
    """Envoie un fichier à l'API et retourne son bloc `stats` (ou None en cas d'échec)."""
    with open(path, "rb") as f:
        files = {"audio": (path.name, f, "application/octet-stream")}
        data = {"mode": mode}
        try:
            resp = client.post(url, files=files, data=data)
        except httpx.RequestError as e:
            print(f"  ⚠️  {path.name} : erreur réseau ({e})", file=sys.stderr)
            return None

    if resp.status_code != 200:
        print(f"  ⚠️  {path.name} : HTTP {resp.status_code} — {resp.text[:200]}", file=sys.stderr)
        return None

    return resp.json().get("stats", {})


def benchmarker_fichier(client: httpx.Client, url: str, path: Path, mode: str, repeats: int) -> Optional[dict]:
    """Répète `repeats` appels sur un fichier et retourne les médianes (durée audio, temps de traitement)."""
    durées_audio = []
    temps_traitement = []

    for i in range(repeats):
        print(f"  [{i + 1}/{repeats}] {path.name}...", end=" ", flush=True)
        début = time.perf_counter()
        stats = transcrire_un_fichier(client, url, path, mode)
        écoulé = time.perf_counter() - début

        if stats is None:
            print("échec")
            continue

        audio_sec = stats.get("audio_duration_sec")
        proc_sec = stats.get("processing_time_sec")
        if audio_sec is None or proc_sec is None:
            print("stats manquantes dans la réponse")
            continue

        durées_audio.append(audio_sec)
        temps_traitement.append(proc_sec)
        print(f"ok ({proc_sec:.1f}s serveur, {écoulé:.1f}s total)")

    if not temps_traitement:
        return None

    return {
        "fichier": path.name,
        "audio_duration_sec": statistics.median(durées_audio),
        "processing_time_sec": statistics.median(temps_traitement),
        "essais": len(temps_traitement),
    }


def afficher_tableau(résultats: list, manual_ratio: float) -> None:
    en_têtes = ["Fichier", "Durée audio", "Traitement (médiane)", "Ratio", "Manuel équiv."]
    lignes = []
    for r in résultats:
        ratio = r["audio_duration_sec"] / r["processing_time_sec"] if r["processing_time_sec"] else float("nan")
        manuel_min = (r["audio_duration_sec"] / 60) * manual_ratio
        lignes.append([
            r["fichier"],
            _formater_duree(r["audio_duration_sec"]),
            f"{r['processing_time_sec']:.1f}s",
            f"{ratio:.0f}x",
            f"{manuel_min:.0f} min",
        ])

    toutes_lignes = [en_têtes] + lignes
    largeurs = [max(len(row[i]) for row in toutes_lignes) for i in range(len(en_têtes))]

    def _ligne(cols):
        return "  ".join(c.ljust(largeurs[i]) for i, c in enumerate(cols))

    print()
    print(_ligne(en_têtes))
    print("  ".join("-" * w for w in largeurs))
    for ligne in lignes:
        print(_ligne(ligne))


def afficher_résumé(résultats: list, manual_ratio: float) -> None:
    total_audio_sec = sum(r["audio_duration_sec"] for r in résultats)
    total_traitement_sec = sum(r["processing_time_sec"] for r in résultats)
    ratio_global = total_audio_sec / total_traitement_sec if total_traitement_sec else float("nan")

    manuel_min = (total_audio_sec / 60) * manual_ratio
    gain_min = manuel_min - (total_traitement_sec / 60)

    print()
    print(f"Total audio traité                                      : {_formater_duree(total_audio_sec)}")
    print(f"Total temps de traitement                               : {total_traitement_sec:.1f}s")
    print(f"Ratio moyen global                                      : {ratio_global:.0f}x")
    print(f"Équivalent manuel estimé ({manual_ratio:.0f} min manuel / min audio) : {manuel_min:.0f} min")
    print(f"Gain de temps estimé                                    : {gain_min:.0f} min (~{gain_min / 60:.1f} h)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark de l'API de transcription ParseAndCutV2.")
    parser.add_argument("dossier", type=Path, help="Dossier contenant les fichiers audio de test")
    parser.add_argument(
        "--url", default="http://localhost:5000/api/transcribe", help="URL de l'API (défaut: %(default)s)"
    )
    parser.add_argument(
        "--mode", default="summary", choices=["summary", "transcript"],
        help="Mode de transcription (défaut: %(default)s)"
    )
    parser.add_argument(
        "--repeats", type=int, default=3, help="Nombre de répétitions par fichier (défaut: %(default)s)"
    )
    parser.add_argument(
        "--manual-ratio", type=float, default=5.0,
        help="Minutes de travail manuel estimées par minute d'audio (défaut: %(default)s)"
    )
    parser.add_argument(
        "--timeout", type=float, default=600.0, help="Timeout HTTP par requête, en secondes (défaut: %(default)s)"
    )
    args = parser.parse_args()

    if not args.dossier.is_dir():
        parser.error(f"Dossier introuvable : {args.dossier}")

    fichiers = sorted(
        p for p in args.dossier.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    )
    if not fichiers:
        parser.error(f"Aucun fichier audio ({', '.join(sorted(AUDIO_EXTENSIONS))}) trouvé dans {args.dossier}")

    print(f"{len(fichiers)} fichier(s) audio trouvé(s) — {args.repeats} répétition(s) chacun, mode={args.mode}")

    résultats = []
    with httpx.Client(timeout=args.timeout) as client:
        for path in fichiers:
            print(f"\n{path.name} :")
            résultat = benchmarker_fichier(client, args.url, path, args.mode, args.repeats)
            if résultat is not None:
                résultats.append(résultat)

    if not résultats:
        print("\nAucun résultat exploitable — vérifiez que le serveur tourne et que l'URL est correcte.", file=sys.stderr)
        sys.exit(1)

    afficher_tableau(résultats, args.manual_ratio)
    afficher_résumé(résultats, args.manual_ratio)


if __name__ == "__main__":
    main()
