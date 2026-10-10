import type { Lang } from "./i18n";
import { translate } from "./i18n";

export type TranscribeMode = "summary" | "transcript";
export type TranscribeStep = "upload" | "cutting" | "whisper" | "llm";

export interface TranscribeStats {
  chunks: number;
  transcription_chars: number;
}

export interface TranscribeResult {
  mode: TranscribeMode;
  markdown?: string;
  transcript?: string;
  stats: TranscribeStats;
}

export interface JobProgress {
  step: TranscribeStep;
  chunkCurrent?: number;
  chunkTotal?: number;
  summaryCurrent?: number;
  summaryTotal?: number;
}

// URL de l'API backend (FastAPI ParseAndCutV2).
// En prod : vide (chaîne relative) — nginx sert le frontend ET reverse-proxy /api/*
// vers le backend en local sur le Pi, donc tout passe par le même domaine
// (parseandcut.alithiel31.dev), pas de backend exposé séparément.
// En dev : VITE_API_URL=http://localhost:5000 pour taper directement sur uvicorn.
const API_URL = import.meta.env.VITE_API_URL || "";

// Le pipeline (découpage + transcription Whisper chunk par chunk + résumé
// IA) est traité en tâche de fond côté backend : une seule requête HTTP
// synchrone dépasserait le timeout fixe de 100s imposé par Cloudflare
// (edge response timeout, non réglable en dehors du plan Enterprise) dès
// qu'un fichier dépasse quelques minutes d'audio — d'où le HTTP 524
// observé sur les fichiers plus longs. On démarre donc un job côté
// backend (POST /api/transcribe/start) puis on sonde son état
// (GET /api/transcribe/status/:id) à intervalle régulier : chaque requête
// individuelle reste rapide, seul le job en tâche de fond est long.
const POLL_INTERVAL_MS = 3000;
const MAX_POLL_MS = 30 * 60 * 1000; // garde-fou : 30 min sans résultat = abandon

export class ApiError extends Error {
  // Texte déjà transcrit avant l'échec du job (quota, réseau, panne du résumé IA…).
  partialTranscript?: string;
  // Code HTTP de la réponse en erreur, si l'erreur vient d'une réponse du serveur.
  status?: number;

  constructor(message: string, partialTranscript?: string, status?: number) {
    super(message);
    this.partialTranscript = partialTranscript;
    this.status = status;
  }
}

// Échec d'envoi d'un segment d'enregistrement. `retryable` : coupure réseau,
// 429 ou erreur serveur (ça peut passer plus tard) ; sinon (404, 413, 415…) le
// renvoyer à l'identique échouerait à chaque fois.
export class SegmentUploadError extends Error {
  retryable: boolean;

  constructor(message: string, retryable: boolean) {
    super(message);
    this.retryable = retryable;
  }
}

async function lireErreur(response: Response, lang: Lang): Promise<never> {
  // Repli local (pas un composant, donc pas de useTranslation()) utilisé
  // uniquement quand le backend n'a pas pu renvoyer de `detail` traduit
  // (ex. réponse non-JSON).
  const err = await response
    .json()
    .catch(() => ({ detail: translate(lang, "api.httpError", { status: response.status }) }));
  throw new ApiError(
    err.detail || translate(lang, "api.genericError", { status: response.status }),
    typeof err.partial_transcript === "string" && err.partial_transcript ? err.partial_transcript : undefined,
    response.status
  );
}

export async function transcribeAudio(
  file: File,
  mode: TranscribeMode = "summary",
  lang: Lang = "fr",
  onProgress?: (progress: JobProgress) => void,
  onJobStarted?: (jobId: string) => void
): Promise<TranscribeResult> {
  const formData = new FormData();
  formData.append("audio", file);
  formData.append("mode", mode);
  formData.append("lang", lang);

  return startAndFollowJob("/api/transcribe/start", formData, lang, onProgress, onJobStarted);
}

// Démarre un job de traitement (POST qui renvoie `job_id`) puis le suit jusqu'au résultat.
async function startAndFollowJob(
  path: string,
  formData: FormData,
  lang: Lang,
  onProgress?: (progress: JobProgress) => void,
  onJobStarted?: (jobId: string) => void
): Promise<TranscribeResult> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    await lireErreur(response, lang);
  }

  const { job_id: jobId } = (await response.json()) as { job_id: string };
  onJobStarted?.(jobId);

  return followTranscriptionJob(jobId, lang, onProgress);
}

// --- Enregistrement par segments (POST /api/recordings…) ---
// Le navigateur envoie l'audio au fil de la réunion, par segments autonomes :
// un onglet qui plante ou une coupure réseau ne fait plus perdre tout
// l'enregistrement. Le traitement final réutilise le même job que /start.

export interface RecordingSession {
  recordingId: string;
  segmentSeconds: number;
}

export async function createRecording(lang: Lang): Promise<RecordingSession> {
  const response = await fetch(`${API_URL}/api/recordings?lang=${lang}`, { method: "POST" });
  if (!response.ok) {
    await lireErreur(response, lang);
  }
  const data = await response.json();
  return { recordingId: data.recording_id, segmentSeconds: data.segment_seconds };
}

export async function uploadSegment(
  recordingId: string,
  index: number,
  blob: Blob,
  filename: string,
  lang: Lang
): Promise<void> {
  const formData = new FormData();
  formData.append("audio", blob, filename);
  formData.append("lang", lang);

  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/recordings/${recordingId}/segments/${index}`, {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new SegmentUploadError("network", true);
  }

  if (!response.ok) {
    const retryable = response.status === 408 || response.status === 429 || response.status >= 500;
    throw new SegmentUploadError(`HTTP ${response.status}`, retryable);
  }
}

// Meilleur effort : le serveur nettoie de toute façon un enregistrement abandonné.
export async function cancelRecording(recordingId: string, lang: Lang): Promise<void> {
  try {
    await fetch(`${API_URL}/api/recordings/${recordingId}/cancel?lang=${lang}`, { method: "POST" });
  } catch {
    // hors ligne : rien à faire
  }
}

// Termine un enregistrement par segments et suit le job comme un envoi classique.
export async function transcribeRecording(
  recordingId: string,
  mode: TranscribeMode = "summary",
  lang: Lang = "fr",
  onProgress?: (progress: JobProgress) => void,
  onJobStarted?: (jobId: string) => void
): Promise<TranscribeResult> {
  const formData = new FormData();
  formData.append("mode", mode);
  formData.append("lang", lang);

  return startAndFollowJob(`/api/recordings/${recordingId}/finish`, formData, lang, onProgress, onJobStarted);
}

export async function resumeTranscription(
  jobId: string,
  lang: Lang = "fr",
  onProgress?: (progress: JobProgress) => void
): Promise<TranscribeResult> {
  return followTranscriptionJob(jobId, lang, onProgress);
}

async function followTranscriptionJob(
  jobId: string,
  lang: Lang,
  onProgress?: (progress: JobProgress) => void
): Promise<TranscribeResult> {
  const deadline = Date.now() + MAX_POLL_MS;
  for (;;) {
    if (Date.now() > deadline) {
      throw new ApiError(translate(lang, "api.timeout"));
    }

    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));

    const statusResponse = await fetch(
      `${API_URL}/api/transcribe/status/${jobId}?lang=${lang}`
    );

    if (!statusResponse.ok) {
      await lireErreur(statusResponse, lang);
    }

    const data = await statusResponse.json();

    if (data.status === "done") {
      const { status: _status, ...result } = data;
      return result as TranscribeResult;
    }

    onProgress?.({
      step: (data.step as TranscribeStep) || "whisper",
      chunkCurrent: data.chunk_current ?? undefined,
      chunkTotal: data.chunk_total ?? undefined,
      summaryCurrent: data.summary_current ?? undefined,
      summaryTotal: data.summary_total ?? undefined,
    });
  }
}
