import { useEffect, useRef, useState } from "react";
import { ApiError, resumeTranscription, type JobProgress, type TranscribeMode, type TranscribeResult } from "../api";
import { STEPS } from "../components/ProgressSteps";
import { useTranslation } from "../i18n";
import { getPermission, notifyResult } from "../notifications";
import { clearPendingJob, readPendingJob } from "../pendingJob";

export type Phase = "idle" | "loading" | "done" | "error";

interface Options {
  notifyEnabled: boolean;
  // Appelé au chargement si un job resté en cours est repris (le mode affiché doit suivre).
  onResume: (mode: TranscribeMode) => void;
}

/**
 * État d'un traitement (phase, étape, message, erreur, résultat) et réactions
 * aux événements du job. Au chargement, reprend le suivi d'un job laissé en cours
 * par un rechargement de page (voir pendingJob.ts).
 */
export function useTranscriptionJob({ notifyEnabled, onResume }: Options) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [activeStep, setActiveStep] = useState<string>(STEPS[0].id);
  const [statusText, setStatusText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TranscribeResult | null>(null);
  const [partialTranscript, setPartialTranscript] = useState<string | null>(null);
  const [isResumed, setIsResumed] = useState(false);
  const restoreStartedRef = useRef(false);
  const { t } = useTranslation();

  function startLoading(status: string, resumed = false) {
    setError(null);
    setResult(null);
    setPartialTranscript(null);
    setPhase("loading");
    setIsResumed(resumed);
    setActiveStep(STEPS[0].id);
    setStatusText(status);
  }

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

  useEffect(() => {
    if (restoreStartedRef.current) return;
    restoreStartedRef.current = true;

    const pendingJob = readPendingJob();
    if (!pendingJob) return;

    onResume(pendingJob.mode);
    startLoading(t("home.status.resuming"), true);

    resumeTranscription(pendingJob.jobId, pendingJob.lang, handleProgress)
      .then((data) => handleResult(data, pendingJob.mode))
      .catch(handleJobError);
    // The ref prevents StrictMode's development-only effect replay from polling twice.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    phase,
    activeStep,
    statusText,
    setStatusText,
    error,
    setError,
    result,
    partialTranscript,
    isResumed,
    startLoading,
    handleProgress,
    handleResult,
    handleJobError,
  };
}
