import { useEffect, useRef, useState } from "react";
import { useTranslation } from "../i18n";

const MAX_RECORDING_BYTES = 100 * 1024 * 1024;
const MIME_CANDIDATES = ["audio/webm;codecs=opus", "audio/mp4", "audio/webm", "audio/ogg;codecs=opus"];

type RecorderPhase = "idle" | "preparing" | "recording" | "paused" | "stopping" | "ready" | "error";

interface AudioRecorderProps {
  disabled: boolean;
  onActivityChange: (active: boolean) => void;
  onRecordingStart: () => void;
  onFileReady: (file: File) => void;
}

function formatTime(milliseconds: number): string {
  const totalSeconds = Math.floor(milliseconds / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return [hours, minutes, seconds].map((value) => String(value).padStart(2, "0")).join(":");
}

function extensionForMimeType(mimeType: string): string {
  if (mimeType.includes("mp4")) return "mp4";
  if (mimeType.includes("ogg")) return "ogg";
  if (mimeType.includes("wav")) return "wav";
  if (mimeType.includes("mpeg")) return "mp3";
  return "webm";
}

export default function AudioRecorder({ disabled, onActivityChange, onRecordingStart, onFileReady }: AudioRecorderProps) {
  const [phase, setPhase] = useState<RecorderPhase>("idle");
  const [elapsedMs, setElapsedMs] = useState(0);
  const [recordedBytes, setRecordedBytes] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [recordedFile, setRecordedFile] = useState<File | null>(null);
  const [recordedUrl, setRecordedUrl] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const bytesRef = useRef(0);
  const sizeExceededRef = useRef(false);
  const recorderFailedRef = useRef(false);
  const { t } = useTranslation();

  useEffect(() => {
    if (!recordedFile) {
      setRecordedUrl(null);
      return;
    }
    const url = URL.createObjectURL(recordedFile);
    setRecordedUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [recordedFile]);

  useEffect(() => {
    if (phase !== "recording") return;
    const timer = window.setInterval(() => setElapsedMs((value) => value + 1000), 1000);
    return () => window.clearInterval(timer);
  }, [phase]);

  useEffect(() => () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
  }, []);

  function closeStream() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    recorderRef.current = null;
  }

  function describeStartError(reason: unknown): string {
    if (reason instanceof DOMException) {
      if (reason.name === "NotAllowedError" || reason.name === "SecurityError") return t("recorder.error.permission");
      if (reason.name === "NotFoundError" || reason.name === "DevicesNotFoundError") return t("recorder.error.noMicrophone");
      if (reason.name === "NotReadableError" || reason.name === "TrackStartError") return t("recorder.error.microphoneBusy");
    }
    return t("recorder.error.generic");
  }

  async function startRecording() {
    if (disabled || phase === "preparing" || phase === "recording" || phase === "paused" || phase === "stopping") return;
    setError(null);
    setAnnouncement("");
    setPhase("preparing");
    onActivityChange(true);

    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError(t("recorder.error.unsupported"));
      setPhase("error");
      setAnnouncement(t("recorder.status.error"));
      onActivityChange(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mimeType = MIME_CANDIDATES.find((candidate) => MediaRecorder.isTypeSupported(candidate));
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      recorderRef.current = recorder;
      chunksRef.current = [];
      bytesRef.current = 0;
      sizeExceededRef.current = false;
      recorderFailedRef.current = false;
      setElapsedMs(0);
      setRecordedBytes(0);
      setRecordedFile(null);

      recorder.ondataavailable = (event) => {
        if (event.data.size === 0) return;
        chunksRef.current.push(event.data);
        bytesRef.current += event.data.size;
        setRecordedBytes(bytesRef.current);
        if (bytesRef.current > MAX_RECORDING_BYTES && !sizeExceededRef.current) {
          sizeExceededRef.current = true;
          setError(t("recorder.error.tooLarge", { maxMb: 100 }));
          if (recorder.state !== "inactive") recorder.stop();
        }
      };

      recorder.onerror = () => {
        recorderFailedRef.current = true;
        setError(t("recorder.error.generic"));
        setAnnouncement(t("recorder.status.error"));
        if (recorder.state !== "inactive") recorder.stop();
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        closeStream();
        onActivityChange(false);

        if (sizeExceededRef.current || recorderFailedRef.current || blob.size === 0) {
          if (!sizeExceededRef.current && !recorderFailedRef.current) setError(t("recorder.error.empty"));
          setPhase("error");
          setAnnouncement(t("recorder.status.error"));
          return;
        }

        const mimeType = blob.type || "audio/webm";
        const file = new File([blob], `enregistrement-audio.${extensionForMimeType(mimeType)}`, { type: mimeType });
        setRecordedFile(file);
        onFileReady(file);
        setPhase("ready");
        setAnnouncement(t("recorder.status.ready"));
      };

      recorder.start(1000);
      onRecordingStart();
      setPhase("recording");
      setAnnouncement(t("recorder.status.recording"));
    } catch (reason) {
      closeStream();
      setError(describeStartError(reason));
      setPhase("error");
      setAnnouncement(t("recorder.status.error"));
      onActivityChange(false);
    }
  }

  function pauseRecording() {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state !== "recording") return;
    recorder.pause();
    setPhase("paused");
    setAnnouncement(t("recorder.status.paused"));
  }

  function resumeRecording() {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state !== "paused") return;
    recorder.resume();
    setPhase("recording");
    setAnnouncement(t("recorder.status.recording"));
  }

  function stopRecording() {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    setPhase("stopping");
    setAnnouncement(t("recorder.status.stopping"));
    recorder.stop();
  }

  const timeLabel = formatTime(elapsedMs);
  const busy = phase === "preparing" || phase === "recording" || phase === "paused" || phase === "stopping";

  return (
    <section className={`audio-recorder${phase === "recording" ? " is-recording" : ""}`} aria-labelledby="recorder-title">
      <div className="recorder-header">
        <span className="recorder-icon" aria-hidden="true">●</span>
        <div>
          <h3 id="recorder-title">{t("recorder.title")}</h3>
          <p>{t("recorder.description")}</p>
        </div>
      </div>

      {busy && (
        <div className="recorder-live">
          <span className="recording-dot" aria-hidden="true" />
          <span role="timer" aria-live="off" aria-label={t("recorder.timerAria", { time: timeLabel })}>{timeLabel}</span>
          <span className="recorder-size">{t("recorder.size", { size: (recordedBytes / 1024 / 1024).toFixed(1) })}</span>
          {phase === "paused" && <strong>{t("recorder.paused")}</strong>}
          {phase === "preparing" && <strong>{t("recorder.preparing")}</strong>}
          {phase === "stopping" && <strong>{t("recorder.finalizing")}</strong>}
        </div>
      )}

      {error && <p className="recorder-error" role="alert">{error}</p>}

      {phase === "ready" && recordedUrl && (
        <div className="recording-preview">
          <p>{t("recorder.preview", { name: recordedFile?.name ?? "" })}</p>
          <audio controls src={recordedUrl} preload="metadata">{t("recorder.audioUnsupported")}</audio>
        </div>
      )}

      <div className="recorder-actions">
        {(phase === "idle" || phase === "error" || phase === "ready") && (
          <button type="button" className="btn-recorder" onClick={startRecording} disabled={disabled}>
            {phase === "ready" || phase === "error" ? t("recorder.again") : t("recorder.start")}
          </button>
        )}
        {phase === "preparing" && <button type="button" className="btn-recorder" disabled>{t("recorder.preparing")}</button>}
        {phase === "recording" && (
          <>
            <button type="button" className="btn-recorder btn-recorder-secondary" onClick={pauseRecording}>{t("recorder.pause")}</button>
            <button type="button" className="btn-recorder btn-recorder-stop" onClick={stopRecording}>{t("recorder.stop")}</button>
          </>
        )}
        {phase === "paused" && (
          <>
            <button type="button" className="btn-recorder" onClick={resumeRecording}>{t("recorder.resume")}</button>
            <button type="button" className="btn-recorder btn-recorder-stop" onClick={stopRecording}>{t("recorder.stop")}</button>
          </>
        )}
        {phase === "stopping" && <button type="button" className="btn-recorder" disabled>{t("recorder.finalizing")}</button>}
      </div>

      <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">{announcement}</p>
    </section>
  );
}
