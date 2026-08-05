import { useEffect, useRef, useState } from "react";
import { useRegisterSW } from "virtual:pwa-register/react";
import "./App.css";
import DropZone from "./components/DropZone";
import ProgressSteps, { STEPS } from "./components/ProgressSteps";
import ResultView from "./components/ResultView";
import UpdateBanner from "./components/UpdateBanner";
import { transcribeAudio, type TranscribeResult } from "./api";

type Phase = "idle" | "loading" | "done" | "error";

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [activeStep, setActiveStep] = useState<string>(STEPS[0].id);
  const [statusText, setStatusText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TranscribeResult | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const timers = useRef<number[]>([]);

  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW(_url, registration) {
      // Vérifie les mises à jour périodiquement
      if (registration) {
        setInterval(() => registration.update(), 60 * 60 * 1000);
      }
    },
  });

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
      setError("Sélectionnez d'abord un fichier audio.");
      return;
    }
    setError(null);
    setResult(null);
    setPhase("loading");
    setActiveStep(STEPS[0].id);
    setStatusText("Envoi du fichier…");

    const stepTimings: [string, number, string][] = [
      ["step-cut", 1500, "Découpage en cours…"],
      ["step-whisper", 4000, "Transcription Whisper…"],
      ["step-llm", 9000, "Structuration avec Llama…"],
    ];
    timers.current = stepTimings.map(([id, delay, label]) =>
      window.setTimeout(() => {
        setActiveStep(id);
        setStatusText(label);
      }, delay)
    );

    try {
      const data = await transcribeAudio(file);
      clearTimers();
      setResult(data);
      setStatusText("✅ Fiche générée !");
      setPhase("done");
    } catch (e) {
      clearTimers();
      setError(e instanceof Error ? e.message : "Erreur inconnue");
      setPhase("error");
    }
  }

  const loading = phase === "loading";

  return (
    <div className="container">
      <header>
        <h1>🎓 Assistant Transcripteur <span>IA</span></h1>
        <p>Transcription Whisper · Structuration Llama 3 · PWA installable</p>
      </header>

      <main className="card">
        <div className="upload-section">
          <DropZone
            onFileSelected={(f) => {
              setFile(f);
              setError(null);
            }}
            onError={setError}
            selectedFileLabel={
              file ? `📎 ${file.name} — ${(file.size / 1024 / 1024).toFixed(1)} Mo` : ""
            }
          />

          {error && <div className="error-banner">⚠️ {error}</div>}

          <button className="btn-primary" onClick={handleSubmit} disabled={loading}>
            🚀 Générer la fiche de révision
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
            <ResultView markdown={result.markdown} stats={result.stats} />
          </div>
        )}
      </main>

      {needRefresh && (
        <UpdateBanner
          onUpdate={() => updateServiceWorker(true)}
          onDismiss={() => setNeedRefresh(false)}
        />
      )}
    </div>
  );
}
