import { useEffect, useRef, useState } from "react";
import DropZone from "../components/DropZone";
import AudioRecorder from "../components/AudioRecorder";
import ModeSelector from "../components/ModeSelector";
import ProgressSteps from "../components/ProgressSteps";
import ResultView from "../components/ResultView";
import { ApiError, cancelRecording, transcribeAudio, transcribeRecording, type TranscribeMode, type TranscribeResult } from "../api";
import { useLanguage, useTranslation } from "../i18n";
import RecoveryBanner from "../components/RecoveryBanner";
import { discardInterrupted, findInterruptedRecordings, forgetLocalRecording, processInterrupted, type InterruptedRecording } from "../recovery";
import type { RecordedUpload } from "../segmentedRecording";
import { isNotificationSupported } from "../notifications";
import { savePendingJob } from "../pendingJob";
import { useNotifyPreference } from "../hooks/useNotifyPreference";
import { useTranscriptionJob } from "../hooks/useTranscriptionJob";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<TranscribeMode>("summary");
  // Sauvegarde par segments de l'enregistrement micro courant (le fichier concerné est gardé pour le repérer).
  const [recordingUpload, setRecordingUpload] = useState<{ file: File; upload: RecordedUpload } | null>(null);
  // Enregistrements interrompus retrouvés sur l'appareil (le plus récent d'abord).
  const [interrupted, setInterrupted] = useState<InterruptedRecording[]>([]);
  const [recorderBusy, setRecorderBusy] = useState(false);
  const { notifyEnabled, setNotify } = useNotifyPreference();
  const job = useTranscriptionJob({ notifyEnabled, onResume: setMode });
  const { phase, error, setError, result, partialTranscript, startLoading, handleProgress, handleResult, handleJobError } = job;
  const resultRef = useRef<HTMLDivElement>(null);
  const { t } = useTranslation();
  const { lang } = useLanguage();

  async function handleNotifyToggle(checked: boolean) {
    if (!(await setNotify(checked))) setError(t("notify.blocked"));
  }

  useEffect(() => {
    if (phase === "done") {
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 200);
    }
  }, [phase]);

  // Un autre fichier (ou un nouvel enregistrement) remplace celui-ci : ses copies ne serviront plus.
  useEffect(() => {
    if (recordingUpload && recordingUpload.file !== file) {
      const { recordingId, localId } = recordingUpload.upload;
      if (recordingId) void cancelRecording(recordingId, lang);
      void forgetLocalRecording(localId);
      setRecordingUpload(null);
    }
  }, [file, recordingUpload, lang]);

  // Au chargement : un enregistrement interrompu (onglet planté, page quittée…) est-il resté sur l'appareil ?
  useEffect(() => {
    let active = true;
    void findInterruptedRecordings().then((found) => {
      if (active) setInterrupted(found);
    });
    return () => {
      active = false;
    };
  }, []);

  async function handleResumeInterrupted() {
    const item = interrupted[0];
    if (!item || loading || recorderBusy) return;
    startLoading(t("home.status.uploading"));

    try {
      const data = await processInterrupted(item, {
        mode,
        lang,
        onUploadProgress: (sent, total) => job.setStatusText(t("recovery.status.uploading", { sent, total })),
        onProgress: handleProgress,
        onJobStarted: (jobId) => savePendingJob({ jobId, mode, lang }),
      });
      setInterrupted((current) => current.slice(1));
      handleResult(data, mode);
    } catch (e) {
      handleJobError(e);
    }
  }

  async function handleDiscardInterrupted() {
    const item = interrupted[0];
    if (!item || !window.confirm(t("recovery.discardConfirm"))) return;
    await discardInterrupted(item, lang);
    setInterrupted((current) => current.slice(1));
  }

  async function handleSubmit() {
    if (recorderBusy) return;
    if (!file) {
      setError(t("home.errors.noFile"));
      return;
    }
    startLoading(t("home.status.uploading"));

    const segmented = recordingUpload && recordingUpload.file === file ? recordingUpload.upload : null;
    const onJobStarted = (jobId: string) => {
      savePendingJob({ jobId, mode, lang });
      // Le traitement a démarré : la sauvegarde locale de l'enregistrement n'a plus d'utilité.
      if (segmented) void forgetLocalRecording(segmented.localId);
    };
    setRecordingUpload(null);

    try {
      let data: TranscribeResult;
      if (segmented?.complete && segmented.recordingId) {
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

        {interrupted.length > 0 && !loading && !recorderBusy && (
          <RecoveryBanner
            item={interrupted[0]}
            moreCount={interrupted.length - 1}
            busy={controlsDisabled}
            onResume={handleResumeInterrupted}
            onDiscard={handleDiscardInterrupted}
          />
        )}

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
            setRecordingUpload(upload ? { file: recording, upload } : null);
            setError(null);
          }}
        />

        {error && (
          <div className="error-banner" role="alert">
            ⚠️ {error}
            {partialTranscript && <> {t("home.errors.partialRecovered")}</>}
          </div>
        )}

        <ModeSelector mode={mode} onChange={setMode} disabled={controlsDisabled} />

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
            <div><strong>{t("home.progress.title")}</strong><p role="status" aria-live="polite" aria-atomic="true">{job.statusText}</p></div>
          </div>
          <ProgressSteps activeId={job.activeStep} mode={mode} />
          <p className="processing-note">{t(job.isResumed ? "home.progress.resumed" : "home.progress.note")}</p>
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
