# 🎓 Meetup Killer — Assistant de Cours IA

[![Docker](https://img.shields.io/badge/Docker-Enabled-blue?logo=docker)](https://www.docker.com/)
[![Groq](https://img.shields.io/badge/Powered%20by-Groq-orange)](https://groq.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


/!\ Little Update, the service is host on Railway : https://parseandcutv2-production.up.railway.app/
---

## ReadMe : Français

### À propos
**Meetup Killer** est un assistant intelligent conçu pour être hébergé sur un **Raspberry Pi** (via Docker). Il transforme vos enregistrements audio de cours ou de réunions en fiches de révision structurées au format Markdown.

Grâce à l'API **Groq**, le traitement est quasi instantané :
* **Transcription** : Whisper-Large-V3 (le plus haut niveau de précision).
* **Synthèse** : Llama 3 (70B) pour une structuration académique parfaite.

### Fonctionnalités
- 🌐 **Interface Web moderne** : Une UI "Glassmorphism" pour envoyer vos fichiers.
- ✂️ **Auto-splitting** : Découpage automatique des gros fichiers audio pour respecter les limites d'API.
- 🐳 **Prêt pour Docker** : FFmpeg et Python sont pré-configurés dans un conteneur léger.
- ⚡ **Performance** : Délégue le calcul lourd au Cloud (Groq) pour ne pas ralentir le Raspberry Pi.

### Installation
1.  **Cloner le dépôt** :
    ```bash
    git clone [https://github.com/votre-compte/meetup-killer.git](https://github.com/votre-compte/meetup-killer.git)
    cd meetup-killer
    ```
2.  **Configurer le `.env`** :
    Créez un fichier `.env` à la racine :
    ```env
    GROQ_API_KEY=votre_cle_api
    LANGUAGE=fr
    ```
3.  **Déployer avec Docker** :
    ```bash
    docker build -t meetup-killer .
    docker run -d -p 80:5000 --name meetup-app --env-file .env -v $(pwd):/app meetup-killer
    ```
4.  **Accéder à l'outil** : Ouvrez votre navigateur sur `http://<IP_DU_RASPBERRY>`.

---

## ReadMe : English

### About
**Meetup Killer** is an AI assistant designed to be hosted on a **Raspberry Pi**. It converts course or meeting audio recordings into structured Markdown study notes.

Using the **Groq API**, processing is near-instantaneous:
* **Transcription**: Whisper-Large-V3 (highest accuracy level).
* **Synthesis**: Llama 3 (70B) for perfect academic structuring.

### Features
- 🌐 **Modern Web UI**: Glassmorphism design for easy file uploading.
- ✂️ **Auto-splitting**: Automatically splits large audio files to comply with API limits.
- 🐳 **Docker Ready**: FFmpeg and Python are pre-configured in a lightweight container.
- ⚡ **Performance