// Dictionnaire français — langue par défaut. `en.ts` doit exposer exactement
// les mêmes clés (vérifié à la compilation via `satisfies typeof fr`).
const fr = {
  "meta.appName": "Assistant Transcripteur IA",
  "meta.title": "Assistant Transcripteur IA",
  "meta.description": "Transcription et résumé de cours audio avec Whisper et IA",

  "header.tagline": "Transcription Whisper · Structuration par IA · PWA installable",

  "langSwitcher.label": "Langue",

  "home.errors.noFile": "Sélectionnez d'abord un fichier audio.",
  "home.errors.unknown": "Erreur inconnue",
  "home.status.uploading": "Envoi du fichier au serveur…",
  "home.status.cutting": "Découpage en cours…",
  "home.status.whisper": "Transcription Whisper…",
  "home.status.whisperProgress": "Transcription Whisper… ({current}/{total})",
  "home.status.structuring": "Structuration par l'IA…",
  "home.status.summaryDone": "✅ Fiche générée !",
  "home.status.transcriptDone": "✅ Transcription terminée !",
  "home.eyebrow": "De l’audio à l’essentiel",
  "home.title": "Transformez votre audio en contenu utile",
  "home.description": "Déposez un cours ou une réunion pour obtenir une fiche de révision ou une transcription horodatée.",
  "home.modeSelector.label": "Type de résultat",
  "home.mode.summary": "Fiche de révision",
  "home.mode.summaryDescription": "Un résumé structuré avec les notions clés.",
  "home.mode.transcript": "Transcription complète",
  "home.mode.transcriptDescription": "Le texte intégral avec repères temporels.",
  "home.submit.summary": "🚀 Générer la fiche de révision",
  "home.submit.transcript": "🚀 Transcrire l'audio",
  "home.submit.loading": "Traitement en cours…",
  "home.progress.label": "Étapes du traitement",
  "home.progress.title": "Votre fichier est en cours de traitement",
  "home.progress.note": "Le traitement peut prendre quelques minutes pour les longs enregistrements. Vous pouvez laisser cette page ouverte.",
  "home.selectedFile": "📎 {name} — {size} Mo",

  "dropzone.tooLarge": "Fichier trop volumineux (max {maxMb} Mo).",
  "dropzone.title": "Ajoutez votre fichier audio",
  "dropzone.hint": "Glissez-déposez votre fichier dans cette zone",
  "dropzone.choose": "Choisir un fichier",
  "dropzone.limits": "Formats audio courants · {maxMb} Mo maximum",

  "notify.toggle": "🔔 Me notifier à la fin",
  "notify.blocked": "Notifications bloquées — autorise-les dans les réglages du navigateur.",
  "notify.title.summary": "Fiche de révision prête",
  "notify.title.transcript": "Transcription prête",
  "notify.body.summary": "Ta fiche de révision a été générée.",
  "notify.body.transcript": "Ta transcription est terminée.",

  "steps.step-upload": "📤 Envoi",
  "steps.step-cut": "✂️ Découpage",
  "steps.step-whisper": "🎙️ Transcription",
  "steps.step-llm": "🧠 Structuration",

  "result.summaryTitle": "📝 Fiche de résumé",
  "result.transcriptTitle": "📄 Transcription",
  "result.copied": "✅ Copié !",
  "result.copy": "📋 Copier",
  "result.chunks": "🔀 {count} chunk(s)",
  "result.chars": "📝 {count} caractères transcrits",

  "footer.navLabel": "Informations légales",
  "footer.legal": "Mentions légales",
  "footer.privacy": "Confidentialité",
  "footer.terms": "CGU",
  "footer.tagline": "Service gratuit et sans compte — aucun fichier n'est conservé.",

  "updateBanner.text": "🔄 Une nouvelle version est disponible.",
  "updateBanner.update": "Mettre à jour",
  "updateBanner.later": "Plus tard",

  "notFound.pageTitle": "Page introuvable",
  "notFound.title": "🧭 Page introuvable",
  "notFound.body": "Cette adresse ne correspond à aucune page de l'application.",

  "common.back": "← Retour",

  "legal.updatedAt": "Dernière mise à jour : {date}",
  "legal.cgu.title": "📄 Conditions générales d'utilisation",
  "legal.cgu.date": "6 août 2026",
  "legal.confidentialite.title": "🔒 Politique de confidentialité",
  "legal.confidentialite.date": "6 août 2026",
  "legal.mentionsLegales.title": "⚖️ Mentions légales",
  "legal.mentionsLegales.date": "6 août 2026",

  "api.httpError": "Erreur HTTP {status}",
  "api.genericError": "Erreur {status}",
  "api.timeout": "Le traitement prend trop de temps — réessayez plus tard.",
};

export type Translations = typeof fr;

export default fr;
