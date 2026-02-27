🎓 Meetup Killer - IA Course Assistant
🇫🇷 Français
À propos
Meetup Killer est un assistant intelligent hébergé sur Raspberry Pi qui transforme vos enregistrements audio de cours ou de réunions en fiches de révision structurées en Markdown. Il utilise l'API Groq pour une transcription ultra-rapide (Whisper) et une synthèse intelligente (Llama 3).

Fonctionnalités
🌐 Interface Web : Upload simple par glisser-déposer.

⚡ Vitesse : Transcription et résumé en quelques secondes via Groq Cloud.

🐳 Dockerisé : Environnement isolé avec FFmpeg pré-installé.

📱 Responsive : Accessible depuis votre PC, tablette ou smartphone sur le réseau local.

Installation Rapide
Cloner le projet sur le Raspberry Pi :

Bash
git clone <votre-url-repo>
cd mon-script-ia
Configurer les variables d'environnement :
Créez un fichier .env avec votre clé API Groq :

Extrait de code
GROQ_API_KEY=votre_cle_ici
LANGUAGE=fr
Lancer avec Docker :

Bash
docker build -t meetup-killer .
docker run -d -p 80:5000 --name meetup-app --env-file .env -v $(pwd):/app meetup-killer
🇬🇧 English
About
Meetup Killer is an AI-powered assistant hosted on a Raspberry Pi that converts your course or meeting audio recordings into structured Markdown study notes. It leverages the Groq API for ultra-fast transcription (Whisper) and intelligent summarization (Llama 3).

Features
🌐 Web Interface: Simple drag-and-drop upload.

⚡ Performance: Transcription and synthesis in seconds via Groq Cloud.

🐳 Dockerized: Fully isolated environment with pre-installed FFmpeg.

📱 Responsive: Access it from your PC, tablet, or smartphone on your local network.

Quick Setup
Clone the project onto your Raspberry Pi:

Bash
git clone <your-repo-url>
cd mon-script-ia
Configure environment variables:
Create a .env file with your Groq API key:

Extrait de code
GROQ_API_KEY=your_key_here
LANGUAGE=fr
Run with Docker:

Bash
docker build -t meetup-killer .
docker run -d -p 80:5000 --name meetup-app --env-file .env -v $(pwd):/app meetup-killer
