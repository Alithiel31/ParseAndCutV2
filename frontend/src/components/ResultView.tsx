import { useMemo, useState } from "react";
import { marked } from "marked";
import DOMPurify from "dompurify";
import type { TranscribeMode, TranscribeStats } from "../api";

interface ResultViewProps {
  mode: TranscribeMode;
  markdown?: string;
  transcript?: string;
  stats: TranscribeStats;
}

export default function ResultView({ mode, markdown, transcript, stats }: ResultViewProps) {
  const [copied, setCopied] = useState(false);
  const isSummary = mode === "summary";

  // Le Markdown vient du LLM, donc indirectement de l'audio déposé : `marked` ne filtre
  // pas le HTML brut, il faut l'assainir avant de l'injecter. Le profil `html` écarte
  // SVG et MathML, qu'une fiche de révision ne contient jamais.
  const html = useMemo(
    () =>
      isSummary
        ? DOMPurify.sanitize(marked.parse(markdown ?? "", { async: false }) as string, {
            USE_PROFILES: { html: true },
          })
        : "",
    [isSummary, markdown]
  );

  function handleCopy() {
    if (isSummary) {
      // Copie le texte brut rendu (sans balises HTML)
      const tmp = document.createElement("div");
      tmp.innerHTML = html;
      navigator.clipboard.writeText(tmp.innerText).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    } else {
      navigator.clipboard.writeText(transcript ?? "").then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  }

  return (
    <section id="resultArea">
      <div className="result-header">
        <h2>{isSummary ? "📝 Fiche de résumé" : "📄 Transcription"}</h2>
        <button className="btn-secondary" onClick={handleCopy}>
          {copied ? "✅ Copié !" : "📋 Copier"}
        </button>
      </div>

      <div className="stats-bar">
        <span>🔀 {stats.chunks} chunk(s)</span>
        <span>📝 {stats.transcription_chars.toLocaleString()} caractères transcrits</span>
      </div>

      {isSummary ? (
        <div className="markdown-body" dangerouslySetInnerHTML={{ __html: html }} />
      ) : (
        <div className="markdown-body transcript-body">{transcript}</div>
      )}
    </section>
  );
}
