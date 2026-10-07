import { useMemo, useState } from "react";
import { marked } from "marked";
import DOMPurify from "dompurify";
import type { TranscribeMode, TranscribeStats } from "../api";
import { useTranslation } from "../i18n";

interface ResultViewProps {
  mode: TranscribeMode;
  markdown?: string;
  transcript?: string;
  stats: TranscribeStats;
}

export default function ResultView({ mode, markdown, transcript, stats }: ResultViewProps) {
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");
  const isSummary = mode === "summary";
  const { t } = useTranslation();

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

  async function handleCopy() {
    try {
      let textToCopy = transcript ?? "";
      if (isSummary) {
        const tmp = document.createElement("div");
        tmp.innerHTML = html;
        textToCopy = tmp.innerText;
      }
      await navigator.clipboard.writeText(textToCopy);
      setCopyState("copied");
      window.setTimeout(() => setCopyState("idle"), 2500);
    } catch {
      setCopyState("failed");
    }
  }

  return (
    <section id="resultArea" aria-labelledby="result-title">
      <div className="result-header">
        <h2 id="result-title">{t(isSummary ? "result.summaryTitle" : "result.transcriptTitle")}</h2>
        <button className="btn-secondary" onClick={handleCopy}>
          {t(copyState === "copied" ? "result.copied" : "result.copy")}
        </button>
      </div>
      <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {copyState === "copied" ? t("result.copied") : copyState === "failed" ? t("result.copyFailed") : ""}
      </p>

      <div className="stats-bar">
        <span>{t("result.chunks", { count: stats.chunks })}</span>
        <span>{t("result.chars", { count: stats.transcription_chars.toLocaleString() })}</span>
      </div>

      {isSummary ? (
        <div className="markdown-body" dangerouslySetInnerHTML={{ __html: html }} />
      ) : (
        <div className="markdown-body transcript-body">{transcript}</div>
      )}
    </section>
  );
}
