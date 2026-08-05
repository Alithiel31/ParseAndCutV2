import { useState } from "react";
import { marked } from "marked";
import type { TranscribeStats } from "../api";

interface ResultViewProps {
  markdown: string;
  stats: TranscribeStats;
}

export default function ResultView({ markdown, stats }: ResultViewProps) {
  const [copied, setCopied] = useState(false);
  const html = marked.parse(markdown, { async: false }) as string;

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
