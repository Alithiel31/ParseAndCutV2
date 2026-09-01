import { useEffect, useRef, useState } from "react";
import DropZone from "../components/DropZone";
import ProgressSteps, { STEPS } from "../components/ProgressSteps";
import ResultView from "../components/ResultView";
import { transcribeAudio, type TranscribeMode, type TranscribeResult } from "../api";
import { useLanguage, useTranslation } from "../i18n";
import { getPermission, isNotificationSupported, notifyResult, requestPermission } from "../notifications";

type Phase = "idle" | "loading" | "done" | "error";

const NOTIFY_STORAGE_KEY = "pac_notify";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<TranscribeMode>("summary");
  const [phase, setPhase] = useState<Phase>("idle");
  const [activeStep, setActiveStep] = useState<string>(STEPS[0].id);
  const [statusText, setStatusText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TranscribeResult | null>(null);
  const [notifyEnabled, setNotifyEnabled] = useState(() => {
    try {
      return localStorage.getItem(NOTIFY_STORAGE_KEY) === "true";
    } catch {
      return false;
    }
  });
  const resultRef = useRef<HTMLDivElement>(null);
  const timers = useRef<number[]>([]);
  const { t } = useTranslation();
  const { lang } = useLanguage();

  async function handleNotifyToggle(checked: boolean) {
    if (checked) {
      const permission = getPermission() === "granted" ? "granted" : await requestPermission();
      if (permission !== "granted") {
        setError(t("notify.blocked"));
        return;
      }
    }
    setNotifyEnabled(checked);
    try {
      localStorage.setItem(NOTIFY_STORAGE_KEY, String(checked));
    } catch {
      // navigation privée / stockage désactivé : la préférence reste valide pour la session en cours
    }
  }

  useEffect(() => {
    if (phase === "done") {
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 200);
    }
  }, [phase]);

  function clearTimers() {
    timers.current.forEach((t) => window.clearTimeout(t));
    timers.current = [];
  }

  async function handleSubmit() {
    if (!file) {
      setError(t("home.errors.noFile"));
      return;
    }
    setError(null);
    setResult(null);
    setPhase("loading");
    setActiveStep(STEPS[0].id);
    setStatusText(t("home.status.uploading"));

    const stepTimings: [string, number, string][] = [
      ["step-cut", 1500, t("home.status.cutting")],
      ["step-whisper", 4000, t("home.status.whisper")],
      ...(mode === "summary"
        ? ([["step-llm", 9000, t("home.status.structuring")]] as [string, number, string][])
        : []),
    ];
    timers.current = stepTimings.map(([id, delay, label]) =>
      window.setTimeout(() => {
        setActiveStep(id);
        setStatusText(label);
      }, delay)
    );

    try {
      const data = await transcribeAudio(file, mode, lang);
      clearTimers();
      setResult(data);
      setStatusText(mode === "summary" ? t("home.status.summaryDone") : t("home.status.transcriptDone"));
      setPhase("done");
      if (notifyEnabled && getPermission() === "granted") {
        notifyResult(
          t(mode === "summary" ? "notify.title.summary" : "notify.title.transcript"),
          t(mode === "summary" ? "notify.body.summary" : "notify.body.transcript")
        );
      }
    } catch (e) {
      clearTimers();
      setError(e instanceof Error ? e.message : t("home.errors.unknown"));
      setPhase("error");
    }
  }

  const loading = phase === "loading";

  return (
    <main className="card">
      <div className="upload-section">
        <DropZone
          onFileSelected={(f) => {
            setFile(f);
            setError(null);
          }}
          onError={setError}
          selectedFileLabel={
            file
              ? t("home.selectedFile", { name: file.name, size: (file.size / 1024 / 1024).toFixed(1) })
              : ""
          }
        />

        {error && <div className="error-banner">⚠️ {error}</div>}

        <div className="mode-selector" role="radiogroup" aria-label={t("home.modeSelector.label")}>
          <label className={`mode-option${mode === "summary" ? " active" : ""}`}>
            <input
              type="radio"
              name="mode"
              value="summary"
              checked={mode === "summary"}
              onChange={() => setMode("summary")}
            />
            <span>{t("home.mode.summary")}</span>
          </label>
          <label className={`mode-option${mode === "transcript" ? " active" : ""}`}>
            <input
              type="radio"
              name="mode"
              value="transcript"
              checked={mode === "transcript"}
              onChange={() => setMode("transcript")}
            />
            <span>{t("home.mode.transcript")}</span>
          </label>
        </div>

        {isNotificationSupported() && (
          <label className="notify-toggle">
            <input
              type="checkbox"
              checked={notifyEnabled}
              onChange={(e) => handleNotifyToggle(e.target.checked)}
            />
            <span>{t("notify.toggle")}</span>
          </label>
        )}

        <button className="btn-primary" onClick={handleSubmit} disabled={loading}>
          {mode === "summary" ? t("home.submit.summary") : t("home.submit.transcript")}
        </button>
      </div>

      {loading && (
        <div id="loader">
          <div className="spinner" />
          <p>{statusText}</p>
          <ProgressSteps activeId={activeStep} done={false} />
        </div>
      )}

      {result && (
        <div ref={resultRef}>
          <ResultView
            mode={result.mode}
            markdown={result.markdown}
            transcript={result.transcript}
            stats={result.stats}
          />
        </div>
      )}
    </main>
  );
}
