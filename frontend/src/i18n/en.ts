import type fr from "./fr";

// `satisfies typeof fr` fait échouer la compilation si une clé manque ou
// diffère de fr.ts.
const en = {
  "meta.appName": "AI Transcription Assistant",
  "meta.title": "AI Transcription Assistant",
  "meta.description": "Transcribe and summarize audio lectures with Whisper and AI",

  "header.tagline": "Whisper transcription · AI structuring · Installable PWA",

  "langSwitcher.label": "Language",

  "home.errors.noFile": "Select an audio file first.",
  "home.errors.unknown": "Unknown error",
  "home.status.uploading": "Uploading file…",
  "home.status.cutting": "Splitting audio…",
  "home.status.whisper": "Whisper transcription…",
  "home.status.structuring": "AI structuring…",
  "home.status.summaryDone": "✅ Study sheet generated!",
  "home.status.transcriptDone": "✅ Transcription complete!",
  "home.modeSelector.label": "Result type",
  "home.mode.summary": "🧠 AI summary",
  "home.mode.transcript": "📄 Basic transcript",
  "home.submit.summary": "🚀 Generate study sheet",
  "home.submit.transcript": "🚀 Transcribe audio",
  "home.selectedFile": "📎 {name} — {size} MB",

  "dropzone.tooLarge": "File too large (max {maxMb} MB).",
  "dropzone.hint": "Drag your audio file here or click to choose one",

  "steps.step-upload": "📤 Upload",
  "steps.step-cut": "✂️ Splitting",
  "steps.step-whisper": "🎙️ Transcription",
  "steps.step-llm": "🧠 Structuring",

  "result.summaryTitle": "📝 Study sheet",
  "result.transcriptTitle": "📄 Transcript",
  "result.copied": "✅ Copied!",
  "result.copy": "📋 Copy",
  "result.chunks": "🔀 {count} chunk(s)",
  "result.chars": "📝 {count} characters transcribed",

  "footer.navLabel": "Legal information",
  "footer.legal": "Legal notice",
  "footer.privacy": "Privacy",
  "footer.terms": "Terms",
  "footer.tagline": "Free service, no account — no file is ever stored.",

  "updateBanner.text": "🔄 A new version is available.",
  "updateBanner.update": "Update",
  "updateBanner.later": "Later",

  "notFound.pageTitle": "Page not found",
  "notFound.title": "🧭 Page not found",
  "notFound.body": "This address doesn't match any page of the application.",

  "common.back": "← Back",

  "legal.updatedAt": "Last updated: {date}",
  "legal.cgu.title": "📄 Terms of Use",
  "legal.cgu.date": "August 6, 2026",
  "legal.confidentialite.title": "🔒 Privacy Policy",
  "legal.confidentialite.date": "August 6, 2026",
  "legal.mentionsLegales.title": "⚖️ Legal Notice",
  "legal.mentionsLegales.date": "August 6, 2026",

  "api.httpError": "HTTP error {status}",
  "api.genericError": "Error {status}",
} satisfies typeof fr;

export default en;
