import { useMemo, useState } from "react";
import { marked } from "marked";
import DOMPurify from "dompurify";
import type { TranscribeStats } from "../api";

interface ResultViewProps {
  markdown: string;
  stats: TranscribeStats;
}

export default function ResultView({ markdown, stats }: ResultViewProps) {
  const [copied, setCopied] = useState(false);

  // Le Markdown vient du LLM, donc indirectement de l'audio déposé : `marked` ne filtre
  // pas le HTML brut, il faut l'assainir avant de l'injecter. Le profil `html` écarte
  // SVG et MathML, qu'une fiche de révision ne contient jamais.
  const html = useMemo(
    () =>
      DOMPurify.sanitize(marked.parse(markdown, { async: false }) as string, {
        USE_PROFILES: { html: true },
      }),
    [markdown]
  );

  function handleCopy() {
    // Copie le texte brut rendu (sans balises HTML)
    const tmp = document.createElement("div");
    tmp.innerHTML = html;
    navigator.clipboard.writeText(tmp.innerText).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <section id="resultArea">
      <div className="result-header">
        <h2>📝 Fiche de résumé</h2>
        <button className="btn-secondary" onClick={handleCopy}>
          {copied ? "✅ Copié !" : "📋 Copier"}
        </button>
      </div>

      <div className="stats-bar">
        <span>🔀 {stats.chunks} chunk(s)</span>
        <span>📝 {stats.transcription_chars.toLocaleString()} caractères transcrits</span>
      </div>

      <div className="markdown-body" dangerouslySetInnerHTML={{ __html: html }} />
    </section>
  );
}
