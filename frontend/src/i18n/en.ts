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
  "home.status.uploading": "Sending file to the server…",
  "home.status.cutting": "Splitting audio…",
  "home.status.whisper": "Whisper transcription…",
  "home.status.whisperProgress": "Whisper transcription… ({current}/{total})",
  "home.status.structuring": "AI structuring…",
  "home.status.summaryDone": "✅ Study sheet generated!",
  "home.status.transcriptDone": "✅ Transcription complete!",
  "home.eyebrow": "From audio to insight",
  "home.title": "Turn your audio into something useful",
  "home.description": "Drop in a lecture or meeting to get a study sheet or a timestamped transcript.",
  "home.modeSelector.label": "Result type",
  "home.mode.summary": "Study sheet",
  "home.mode.summaryDescription": "A structured summary with key ideas.",
  "home.mode.transcript": "Full transcript",
  "home.mode.transcriptDescription": "The full text with timestamps.",
  "home.submit.summary": "🚀 Generate study sheet",
  "home.submit.transcript": "🚀 Transcribe audio",
  "home.submit.loading": "Processing…",
  "home.progress.label": "Processing steps",
  "home.progress.title": "Your file is being processed",
  "home.progress.note": "Long recordings can take a few minutes. You can leave this page open.",
  "home.selectedFile": "📎 {name} — {size} MB",

  "dropzone.tooLarge": "File too large (max {maxMb} MB).",
  "dropzone.title": "Add your audio file",
  "dropzone.hint": "Drag and drop your file into this area",
  "dropzone.choose": "Choose a file",
  "dropzone.limits": "Common audio formats · {maxMb} MB maximum",

  "notify.toggle": "🔔 Notify me when done",
  "notify.blocked": "Notifications blocked — allow them in your browser settings.",
  "notify.title.summary": "Study sheet ready",
  "notify.title.transcript": "Transcript ready",
  "notify.body.summary": "Your study sheet has been generated.",
  "notify.body.transcript": "Your transcript is ready.",

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
  "api.timeout": "Processing is taking too long — please try again later.",
} satisfies typeof fr;

export default en;
