import os
import subprocess
import logging
import time
from flask import Flask, render_template, request, jsonify
from groq import Groq, APIError, APITimeoutError
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# --- LOGGING STRUCTURÉ ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
if not os.getenv("RAILWAY_ENVIRONMENT"):
    load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 Mo pour les longs audios

# Extensions audio autorisées
ALLOWED_EXTENSIONS = {'mp3', 'mp4', 'wav', 'm4a', 'ogg', 'webm', 'flac', 'aac', 'opus'}

PORT         = int(os.getenv("PORT", 5000))
FFMPEG_PATH  = os.getenv("FFMPEG_PATH", "ffmpeg")
LANGUAGE     = os.getenv("LANGUAGE", "fr")
CHUNK_DURATION = int(os.getenv("CHUNK_DURATION_SEC", 600))  # 10 min par chunk

# --- INITIALISATION GROQ ---
api_key = os.environ.get("GROQ_API_KEY")
client  = None

if api_key:
    try:
        client = Groq(api_key=api_key, timeout=240.0)  # Aligné avec Gunicorn --timeout 300
        logger.info("✅ Groq Client initialisé")
    except Exception as e:
        logger.error(f"❌ Erreur init Groq: {e}")
else:
    logger.warning("⚠️ GROQ_API_KEY manquante")


# --- UTILITAIRES ---

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
        chunk_path = f"/tmp/chunk_{os.getpid()}_{part}.mp3"

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


def transcrire_chunk(path: str, retries: int = 2) -> str:
    """
    Transcrit un chunk audio via Groq Whisper.
    Retente automatiquement avec backoff exponentiel en cas de timeout.
    2 tentatives max pour rester dans le timeout Gunicorn (300s).
    """
    for attempt in range(retries):
        try:
            with open(path, "rb") as f:
                result = client.audio.transcriptions.create(
                    file=(os.path.basename(path), f.read()),
                    model="whisper-large-v3",
                    language=LANGUAGE,
                    response_format="text"
                )
            return result

        except APITimeoutError:
            wait = 2 ** attempt  # 1s puis 2s
            logger.warning(
                f"  Timeout chunk {os.path.basename(path)}, "
                f"tentative {attempt + 1}/{retries} — attente {wait}s"
            )
            time.sleep(wait)

        except APIError as e:
            logger.error(f"  Erreur API Groq (non récupérable): {e}")
            raise

    raise RuntimeError(
        f"Transcription échouée après {retries} tentatives pour {os.path.basename(path)}"
    )


def construire_prompt(texte: str) -> str:
    """
    Prompt enrichi pour la structuration Markdown.
    Isolé pour faciliter les tests et les évolutions futures.
    """
    return f"""Tu es un assistant universitaire expert en prise de notes.
Transforme cette transcription brute en fiche de révision Markdown structurée et claire.

Règles :
- Commence par un résumé en 3 à 5 points clés (section ## Résumé)
- Utilise des titres hiérarchiques (# ## ###) pour organiser le contenu
- Mets les concepts clés en **gras**
- Utilise des listes à puces pour les énumérations
- Mets les définitions importantes dans des blocs citation (> Définition : ...)
- Corrige discrètement les erreurs de transcription évidentes
- Si le contenu est très long, structure-le en grandes parties thématiques
- Réponds uniquement en français

TRANSCRIPTION :
{texte}
"""


# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/health')
def health():
    """Endpoint de santé pour Railway et le monitoring."""
    return jsonify({
        "status":               "ok",
        "groq_ready":           client is not None,
        "language":             LANGUAGE,
        "chunk_duration_sec":   CHUNK_DURATION,
        "allowed_extensions":   sorted(ALLOWED_EXTENSIONS)
    })


@app.route('/process', methods=['POST'])
def process():

    # --- Vérifications préalables ---
    if not client:
        return jsonify({"error": "Configuration API Groq manquante sur le serveur"}), 503

    if 'audio' not in request.files:
        return jsonify({"error": "Aucun fichier audio reçu"}), 400

    audio_file = request.files['audio']

    if not audio_file.filename:
        return jsonify({"error": "Nom de fichier vide"}), 400

    if not allowed_file(audio_file.filename):
        return jsonify({
            "error": f"Format non supporté. Formats acceptés : {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        }), 415

    # --- Sauvegarde sécurisée ---
    filename = secure_filename(audio_file.filename)
    if not filename:
        # Fallback si le nom contient uniquement des caractères non-ASCII
        filename = f"audio_{os.getpid()}.mp3"

    # Préfixe PID pour éviter les collisions entre requêtes simultanées
    input_path    = f"/tmp/{os.getpid()}_{filename}"
    chunks_créés  = []

    try:
        audio_file.save(input_path)
        size_mo = os.path.getsize(input_path) / 1024 / 1024
        logger.info(f"📥 Fichier reçu : {filename} ({size_mo:.1f} Mo)")

        # --- 1. Découpage ---
        logger.info("✂️  Découpage en chunks...")
        chunks_créés = découper_audio(input_path)

        if not chunks_créés:
            return jsonify({
                "error": "Impossible de traiter le fichier audio (vide, corrompu, ou format non lisible par FFmpeg)"
            }), 422

        logger.info(f"✅ {len(chunks_créés)} chunk(s) prêts à transcrire")

        # --- 2. Transcription chunk par chunk ---
        logger.info("🎙️  Transcription Whisper...")
        texte_complet = ""

        for i, path in enumerate(chunks_créés):
            logger.info(f"  [{i+1}/{len(chunks_créés)}] {os.path.basename(path)}")
            texte_complet += transcrire_chunk(path) + " "
            os.remove(path)  # Nettoyage immédiat après transcription

        if not texte_complet.strip():
            return jsonify({
                "error": "Transcription vide — audio silencieux, inaudible ou langue incorrecte ?"
            }), 422

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

        return jsonify({
            "markdown": markdown,
            "stats": {
                "chunks":               len(chunks_créés),
                "transcription_chars":  len(texte_complet)
            }
        })

    # --- Gestion d'erreurs granulaire ---
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg timeout global")
        return jsonify({"error": "Le découpage audio a pris trop de temps"}), 504

    except RuntimeError as e:
        logger.error(f"Erreur transcription: {e}")
        return jsonify({"error": str(e)}), 502

    except APIError as e:
        logger.error(f"Erreur API Groq: {e}")
        return jsonify({"error": f"Erreur API Groq : {e.message}"}), 502

    except Exception:
        logger.exception("Erreur inattendue dans /process")
        return jsonify({"error": "Erreur interne du serveur"}), 500

    finally:
        # Nettoyage garanti même en cas d'exception à mi-parcours
        for path in chunks_créés:
            if os.path.exists(path):
                os.remove(path)
                logger.debug(f"Chunk supprimé : {path}")
        if os.path.exists(input_path):
            os.remove(input_path)
            logger.info(f"Fichier original supprimé : {input_path}")


if __name__ == '__main__':
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host='0.0.0.0', port=PORT, debug=debug)
