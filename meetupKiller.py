import os
import subprocess
from flask import Flask, render_template, request, jsonify
from groq import Groq
from dotenv import load_dotenv

# --- CONFIGURATION ---
if not os.getenv("RAILWAY_ENVIRONMENT"):
    load_dotenv()

app = Flask(__name__, 
            static_folder='static', 
            template_folder='templates')

# Essaye de lire la variable directement
api_key = os.environ.get("GROQ_API_KEY")

# Initialisation prudente
client = None

if api_key:
    try:
        client = Groq(api_key=api_key)
        print(f"✅ Groq Client initialisé (Clé: {api_key[:5]}...)")
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation Groq: {e}")
else:
    print("⚠️ WARNING: GROQ_API_KEY est toujours invisible pour Python.")

# On ne bloque pas l'exécution ici, on gérera l'absence de client dans la route /process

# IMPORTANT : Railway définit sa propre variable PORT
PORT = int(os.getenv("PORT", 5000))
FFMPEG_PATH = "ffmpeg" 
LANGUAGE = os.getenv("LANGUAGE", "fr")

# --- FONCTIONS UTILITAIRES ---

def découper_audio(input_path, interval_sec=600):
    """Découpe l'audio en morceaux pour l'API Groq (limite 25Mo)"""
    part = 0
    chunks = []
    
    while True:
        start_time = part * interval_sec
        # On stocke temporairement dans /tmp 
        chunk_name = f"/tmp/chunk_part_{part}.mp3"
        
        cmd = [
            FFMPEG_PATH, "-ss", str(start_time), "-t", str(interval_sec),
            "-i", input_path, "-vn", "-acodec", "libmp3lame", "-ab", "128k", chunk_name, "-y"
        ]
        
        subprocess.run(cmd, capture_output=True)
        
        if not os.path.exists(chunk_name) or os.path.getsize(chunk_name) < 5000:
            if os.path.exists(chunk_name): os.remove(chunk_name)
            break
            
        chunks.append(chunk_name)
        part += 1
    return chunks

# --- ROUTES FLASK ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    if not client:
        return jsonify({"error": "Configuration API Groq manquante sur le serveur"}), 500
    if 'audio' not in request.files:
        return jsonify({"error": "Aucun fichier reçu"}), 400
    
    audio_file = request.files['audio']
    input_path = os.path.join("/tmp", audio_file.filename)
    audio_file.save(input_path)

    try:
        # 1. Découpage automatique
        liste_chunks = découper_audio(input_path)
        texte_complet = ""
        
        # 2. Transcription via Groq
        for path in liste_chunks:
            with open(path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(path, file.read()),
                    model="whisper-large-v3",
                    language=LANGUAGE,
                    response_format="text"
                )
                texte_complet += transcription + " "
            os.remove(path) # Nettoyage du chunk

        # 3. Structuration via Llama 3
        prompt = f"""
        Tu es un assistant universitaire expert. 
        Transforme cette transcription brute en fiche de révision Markdown structurée.
        Utilise des titres (H1, H2, H3), des listes à puces et du **gras**.
        Réponds en français.

        TRANSCRIPTION :
        {texte_complet}
        """

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )

        return jsonify({"markdown": completion.choices[0].message.content})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        # Nettoyage du fichier original
        if os.path.exists(input_path):
            os.remove(input_path)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)