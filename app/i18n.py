"""
Catalogue de messages bilingues (fr/en) pour les réponses API.
Volontairement minimal (dict + .format) : pas de framework i18n pour une
douzaine de messages d'erreur.
"""

SUPPORTED_LANGS = {"fr", "en"}

DEFAULT_LANG = "fr"

MESSAGES: dict[str, dict[str, str]] = {
    "fr": {
        "invalid_lang": "Langue invalide (fr/en attendu) / Invalid language (expected fr/en)",
        "groq_not_configured": "Configuration API Groq manquante sur le serveur",
        "no_audio_file": "Aucun fichier audio reçu",
        "invalid_mode": "Mode invalide (attendu : 'summary' ou 'transcript')",
        "unsupported_format": "Format non supporté. Formats acceptés : {formats}",
        "file_too_large": "Fichier trop volumineux (max {max_mb} Mo)",
        "ffmpeg_unreadable": "Impossible de traiter le fichier audio (vide, corrompu, ou format non lisible par FFmpeg)",
        "ffmpeg_timeout": "Le découpage audio a pris trop de temps",
        "transcription_empty": "Transcription vide — audio silencieux, inaudible ou langue incorrecte ?",
        "transcription_error": "Erreur de transcription : {error}",
        "groq_api_error": "Erreur API Groq : {error}",
        "internal_error": "Erreur interne du serveur",
    },
    "en": {
        "invalid_lang": "Langue invalide (fr/en attendu) / Invalid language (expected fr/en)",
        "groq_not_configured": "Groq API configuration missing on the server",
        "no_audio_file": "No audio file received",
        "invalid_mode": "Invalid mode (expected: 'summary' or 'transcript')",
        "unsupported_format": "Unsupported format. Accepted formats: {formats}",
        "file_too_large": "File too large (max {max_mb} MB)",
        "ffmpeg_unreadable": "Unable to process the audio file (empty, corrupted, or unreadable format for FFmpeg)",
        "ffmpeg_timeout": "Audio splitting took too long",
        "transcription_empty": "Empty transcription — silent audio, inaudible, or wrong language?",
        "transcription_error": "Transcription error: {error}",
        "groq_api_error": "Groq API error: {error}",
        "internal_error": "Internal server error",
    },
}


def t(msg_id: str, lang: str, **kwargs) -> str:
    """Retourne le message `msg_id` traduit en `lang`, avec repli sur le
    français si la langue ou la clé est inconnue (jamais de KeyError)."""
    catalog = MESSAGES.get(lang, MESSAGES[DEFAULT_LANG])
    template = catalog.get(msg_id) or MESSAGES[DEFAULT_LANG][msg_id]
    return template.format(**kwargs) if kwargs else template
