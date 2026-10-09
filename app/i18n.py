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
        "audio_silent": (
            "Enregistrement silencieux : aucun son n'a été capté. Le micro a probablement été "
            "coupé (écran verrouillé, changement d'application). Gardez l'écran allumé pendant "
            "l'enregistrement et réessayez."
        ),
        "groq_api_error": "Erreur API Groq : {error}",
        "internal_error": "Erreur interne du serveur",
        "job_not_found": "Job introuvable ou déjà récupéré",
        "recording_not_found": "Enregistrement introuvable ou expiré",
        "recording_finished": "Cet enregistrement est déjà en cours de traitement",
        "segment_invalid_index": "Numéro de segment invalide (0 à {max_index} attendu)",
        "segment_too_large": "Segment trop volumineux (max {max_mb} Mo)",
        "recording_too_large": "Enregistrement trop volumineux (max {max_mb} Mo au total)",
        "segments_missing": "Segments manquants : {missing}",
        "recording_empty": "Aucun segment reçu pour cet enregistrement",
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
        "audio_silent": (
            "Silent recording: no sound was captured. The microphone was probably muted "
            "(screen locked, app switched). Keep the screen on while recording and try again."
        ),
        "groq_api_error": "Groq API error: {error}",
        "internal_error": "Internal server error",
        "job_not_found": "Job not found or already retrieved",
        "recording_not_found": "Recording not found or expired",
        "recording_finished": "This recording is already being processed",
        "segment_invalid_index": "Invalid segment number (expected 0 to {max_index})",
        "segment_too_large": "Segment too large (max {max_mb} MB)",
        "recording_too_large": "Recording too large (max {max_mb} MB in total)",
        "segments_missing": "Missing segments: {missing}",
        "recording_empty": "No segment received for this recording",
    },
}


def t(msg_id: str, lang: str, **kwargs) -> str:
    """Retourne le message `msg_id` traduit en `lang`, avec repli sur le
    français si la langue ou la clé est inconnue (jamais de KeyError)."""
    catalog = MESSAGES.get(lang, MESSAGES[DEFAULT_LANG])
    template = catalog.get(msg_id) or MESSAGES[DEFAULT_LANG][msg_id]
    return template.format(**kwargs) if kwargs else template
