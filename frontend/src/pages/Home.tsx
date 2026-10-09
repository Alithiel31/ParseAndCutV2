import { useEffect, useRef, useState } from "react";
import DropZone from "../components/DropZone";
import AudioRecorder from "../components/AudioRecorder";
import ProgressSteps, { STEPS } from "../components/ProgressSteps";
import ResultView from "../components/ResultView";
import { ApiError, cancelRecording, resumeTranscription, transcribeAudio, transcribeRecording, type JobProgress, type TranscribeMode, type TranscribeResult } from "../api";
import { useLanguage, useTranslation, type Lang } from "../i18n";
import type { RecordedUpload } from "../segmentedRecording";
import { getPermission, isNotificationSupported, notifyResult, requestPermission } from "../notifications";

type Phase = "idle" | "loading" | "done" | "error";

const NOTIFY_STORAGE_KEY = "pac_notify";
const PENDING_JOB_STORAGE_KEY = "pac_pending_job";

interface PendingJob {
  jobId: string;
  mode: TranscribeMode;
  lang: Lang;
}

function readPendingJob(): PendingJob | null {
  try {
    const value = localStorage.getItem(PENDING_JOB_STORAGE_KEY);
    if (!value) return null;
    const job = JSON.parse(value) as Partial<PendingJob>;
    if (
      typeof job.jobId !== "string" ||
      !/^[\da-f]{32}$/i.test(job.jobId) ||
      (job.mode !== "summary" && job.mode !== "transcript") ||
      (job.lang !== "fr" && job.lang !== "en")
    ) {
      localStorage.removeItem(PENDING_JOB_STORAGE_KEY);
      return null;
    }
    return job as PendingJob;
  } catch {
    return null;
  }
}

function savePendingJob(job: PendingJob) {
  try {
    localStorage.setItem(PENDING_JOB_STORAGE_KEY, JSON.stringify(job));
  } catch {
    // Le suivi continue dans l'onglet même si le stockage local est indisponible.
  }
}

function clearPendingJob() {
  try {
    localStorage.removeItem(PENDING_JOB_STORAGE_KEY);
  } catch {
    // Le job est terminé ; le stockage local peut être indisponible.
  }
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<TranscribeMode>("summary");
  const [phase, setPhase] = useState<Phase>("idle");
  const [activeStep, setActiveStep] = useState<string>(STEPS[0].id);
  const [statusText, setStatusText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TranscribeResult | null>(null);
  const [partialTranscript, setPartialTranscript] = useState<string | null>(null);
  // Enregistrement micro déjà entièrement envoyé par segments (le fichier concerné est gardé pour le repérer).
  const [recordingUpload, setRecordingUpload] = useState<{ file: File; upload: RecordedUpload } | null>(null);
  const [isResumed, setIsResumed] = useState(false);
  const [recorderBusy, setRecorderBusy] = useState(false);
  const [notifyEnabled, setNotifyEnabled] = useState(() => {
    try {
      return localStorage.getItem(NOTIFY_STORAGE_KEY) === "true";
    } catch {
      return false;
    }
  });
  const resultRef = useRef<HTMLDivElement>(null);
  const restoreStartedRef = useRef(false);
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

  // Un autre fichier remplace l'enregistrement : sa copie sur le serveur ne servira plus.
  useEffect(() => {
    if (recordingUpload && recordingUpload.file !== file) {
      void cancelRecording(recordingUpload.upload.recordingId, lang);
      setRecordingUpload(null);
    }
  }, [file, recordingUpload, lang]);

  useEffect(() => {
    if (restoreStartedRef.current) return;
    restoreStartedRef.current = true;

    const pendingJob = readPendingJob();
    if (!pendingJob) return;

    setMode(pendingJob.mode);
    setPhase("loading");
    setIsResumed(true);
    setStatusText(t("home.status.resuming"));
    setError(null);

    resumeTranscription(pendingJob.jobId, pendingJob.lang, handleProgress)
      .then((data) => handleResult(data, pendingJob.mode))
      .catch(handleJobError);
    // The ref prevents StrictMode's development-only effect replay from polling twice.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleProgress(progress: JobProgress) {
    if (progress.step === "cutting") {
      setActiveStep("step-cut");
      setStatusText(t("home.status.cutting"));
    } else if (progress.step === "whisper") {
      setActiveStep("step-whisper");
      setStatusText(
        progress.chunkTotal && progress.chunkTotal > 1
          ? t("home.status.whisperProgress", {
              current: progress.chunkCurrent ?? 1,
              total: progress.chunkTotal,
            })
          : t("home.status.whisper")
      );
    } else if (progress.step === "llm") {
      setActiveStep("step-llm");
      setStatusText(
        progress.summaryTotal && progress.summaryTotal > 1
          ? t("home.status.structuringProgress", {
              current: progress.summaryCurrent ?? 1,
              total: progress.summaryTotal,
            })
          : t("home.status.structuring")
      );
    }
  }

  function handleResult(data: TranscribeResult, resultMode: TranscribeMode) {
    clearPendingJob();
    setResult(data);
    setStatusText(resultMode === "summary" ? t("home.status.summaryDone") : t("home.status.transcriptDone"));
    setPhase("done");
    if (notifyEnabled && getPermission() === "granted") {
      notifyResult(
        t(resultMode === "summary" ? "notify.title.summary" : "notify.title.transcript"),
        t(resultMode === "summary" ? "notify.body.summary" : "notify.body.transcript")
      );
    }
  }

  function handleJobError(e: unknown) {
    clearPendingJob();
    setError(e instanceof Error ? e.message : t("home.errors.unknown"));
    setPartialTranscript(e instanceof ApiError && e.partialTranscript ? e.partialTranscript : null);
    setPhase("error");
  }

  async function handleSubmit() {
    if (recorderBusy) return;
    if (!file) {
      setError(t("home.errors.noFile"));
      return;
    }
    setError(null);
    setResult(null);
    setPartialTranscript(null);
    setPhase("loading");
    setIsResumed(false);
    setActiveStep(STEPS[0].id);
    setStatusText(t("home.status.uploading"));

    const onJobStarted = (jobId: string) => savePendingJob({ jobId, mode, lang });
    const segmented = recordingUpload && recordingUpload.file === file ? recordingUpload.upload : null;
    setRecordingUpload(null);

    try {
      let data: TranscribeResult;
      if (segmented) {
        try {
          // Déjà sur le serveur : on lance le traitement sans renvoyer le fichier.
          data = await transcribeRecording(segmented.recordingId, mode, lang, handleProgress, onJobStarted);
        } catch (e) {
          // Enregistrement expiré (404) ou incomplet (409) : le fichier complet reste disponible.
          if (!(e instanceof ApiError) || (e.status !== 404 && e.status !== 409)) throw e;
          data = await transcribeAudio(file, mode, lang, handleProgress, onJobStarted);
        }
      } else {
        data = await transcribeAudio(file, mode, lang, handleProgress, onJobStarted);
      }
      handleResult(data, mode);
    } catch (e) {
      handleJobError(e);
    }
  }

  const loading = phase === "loading";
  const controlsDisabled = loading || recorderBusy;

  return (
    <main className="card home-card">
      <section className="home-intro" aria-labelledby="home-title">
        <span className="eyebrow">{t("home.eyebrow")}</span>
        <h2 id="home-title">{t("home.title")}</h2>
        <p>{t("home.description")}</p>
      </section>

      <div className="upload-section" aria-busy={controlsDisabled}>
        <DropZone
          disabled={controlsDisabled}
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

        <div className="source-divider"><span>{t("home.source.or")}</span></div>
        <AudioRecorder
          disabled={loading}
          onActivityChange={setRecorderBusy}
          onRecordingStart={() => {
            setFile(null);
            setError(null);
          }}
          onFileReady={(recording, upload) => {
            setFile(recording);
            setRecordingUpload(upload?.complete ? { file: recording, upload } : null);
            setError(null);
          }}
        />

        {error && (
          <div className="error-banner" role="alert">
            ⚠️ {error}
            {partialTranscript && <> {t("home.errors.partialRecovered")}</>}
          </div>
        )}

        <div className="mode-selector" role="radiogroup" aria-label={t("home.modeSelector.label")}>
          <label className={`mode-option${mode === "summary" ? " active" : ""}`}>
            <input
              type="radio"
              name="mode"
              value="summary"
              checked={mode === "summary"}
              onChange={() => setMode("summary")}
              disabled={controlsDisabled}
            />
            <span className="mode-icon" aria-hidden="true">✦</span>
            <span className="mode-copy"><strong>{t("home.mode.summary")}</strong><small>{t("home.mode.summaryDescription")}</small></span>
          </label>
          <label className={`mode-option${mode === "transcript" ? " active" : ""}`}>
            <input
              type="radio"
              name="mode"
              value="transcript"
              checked={mode === "transcript"}
              onChange={() => setMode("transcript")}
              disabled={controlsDisabled}
            />
            <span className="mode-icon" aria-hidden="true">≋</span>
            <span className="mode-copy"><strong>{t("home.mode.transcript")}</strong><small>{t("home.mode.transcriptDescription")}</small></span>
          </label>
        </div>

        {isNotificationSupported() && (
          <label className="notify-toggle">
            <input
              type="checkbox"
              checked={notifyEnabled}
              onChange={(e) => handleNotifyToggle(e.target.checked)}
              disabled={controlsDisabled}
            />
            <span>{t("notify.toggle")}</span>
          </label>
        )}

        <button
          className="btn-primary"
          onClick={handleSubmit}
          disabled={controlsDisabled}
          aria-disabled={!file || undefined}
        >
          {loading
            ? t("home.submit.loading")
            : mode === "summary"
              ? t("home.submit.summary")
              : t("home.submit.transcript")}
        </button>
      </div>

      {loading && (
        <div id="loader" className="processing-panel">
          <div className="processing-heading">
            <div className="spinner" aria-hidden="true" />
            <div><strong>{t("home.progress.title")}</strong><p role="status" aria-live="polite" aria-atomic="true">{statusText}</p></div>
          </div>
          <ProgressSteps activeId={activeStep} mode={mode} />
          <p className="processing-note">{t(isResumed ? "home.progress.resumed" : "home.progress.note")}</p>
        </div>
      )}

      {partialTranscript && !result && (
        <div>
          <ResultView mode="transcript" transcript={partialTranscript} />
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
      <p className="sr-only" role="status" aria-live="polite">
        {phase === "done" ? t("result.ready") : ""}
      </p>
    </main>
  );
}
