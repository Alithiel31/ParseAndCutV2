import {
  ApiError,
  cancelRecording,
  createRecording,
  SegmentUploadError,
  transcribeRecording,
  uploadSegment,
  type JobProgress,
  type TranscribeMode,
  type TranscribeResult,
} from "./api";
import { translate, type Lang } from "./i18n";
import * as store from "./recordingStore";

/**
 * Reprise d'un enregistrement interrompu (onglet planté, page quittée, téléphone
 * redémarré) à partir de la sauvegarde locale de recordingStore.
 */

// Au-delà, la sauvegarde locale est supprimée : elle ne sera plus jamais reprise.
const EXPIRY_MS = 24 * 60 * 60 * 1000;
// Un enregistrement qui a donné signe de vie il y a moins longtemps est peut-être encore
// actif dans un autre onglet : on ne propose pas de le reprendre.
const ACTIVE_WINDOW_MS = 30 * 1000;
const UPLOAD_ATTEMPTS = 3;

export interface InterruptedRecording {
  session: store.StoredSession;
  segmentCount: number;
  // Durée approximative de ce qui a été enregistré (± quelques secondes).
  approxSeconds: number;
}

interface Piece {
  index: number;
  blob: Blob;
}

/**
 * Tous les segments d'un enregistrement, dans l'ordre. Un segment dont seuls les
 * morceaux d'une seconde ont été écrits (page disparue en plein segment) est
 * reconstitué en les mettant bout à bout : c'est un fichier valide, juste tronqué.
 */
async function rebuildSegments(session: store.StoredSession): Promise<Piece[]> {
  const [segments, chunks] = await Promise.all([store.listSegments(session.localId), store.listChunks(session.localId)]);

  const complete = new Map<number, Blob>();
  for (const segment of segments) complete.set(segment.index, segment.blob);

  const partial = new Map<number, store.StoredChunk[]>();
  for (const chunk of chunks) {
    if (complete.has(chunk.index)) continue;
    partial.set(chunk.index, [...(partial.get(chunk.index) ?? []), chunk]);
  }
  for (const [index, group] of partial) {
    group.sort((a, b) => a.seq - b.seq);
    complete.set(index, new Blob(group.map((c) => c.blob), { type: session.mimeType || "audio/webm" }));
  }

  return [...complete.entries()]
    .sort(([a], [b]) => a - b)
    .map(([index, blob]) => ({ index, blob }))
    .filter((piece) => piece.blob.size > 0);
}

/** Les enregistrements interrompus, le plus récent d'abord. Purge au passage les trop anciens ou vides. */
export async function findInterruptedRecordings(): Promise<InterruptedRecording[]> {
  const now = Date.now();
  const found: InterruptedRecording[] = [];

  for (const session of await store.listSessions()) {
    if (now - session.startedAt > EXPIRY_MS) {
      await store.deleteRecording(session.localId);
      continue;
    }
    if (now - session.updatedAt < ACTIVE_WINDOW_MS) continue;

    const pieces = await rebuildSegments(session);
    if (pieces.length === 0) {
      await store.deleteRecording(session.localId);
      continue;
    }
    found.push({
      session,
      segmentCount: pieces.length,
      approxSeconds: Math.max(0, (session.updatedAt - session.startedAt) / 1000),
    });
  }

  return found.sort((a, b) => b.session.startedAt - a.session.startedAt);
}

function extensionFor(mimeType: string): string {
  if (mimeType.includes("mp4")) return "mp4";
  if (mimeType.includes("ogg")) return "ogg";
  return "webm";
}

const sleep = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms));

async function uploadWithRetry(
  recordingId: string,
  position: number,
  blob: Blob,
  extension: string,
  lang: Lang
): Promise<void> {
  for (let attempt = 1; ; attempt++) {
    try {
      await uploadSegment(recordingId, position, blob, `segment-${String(position).padStart(4, "0")}.${extension}`, lang);
      return;
    } catch (error) {
      const retryable = error instanceof SegmentUploadError && error.retryable;
      if (!retryable || attempt >= UPLOAD_ATTEMPTS) {
        throw new ApiError(translate(lang, "recovery.error.upload"));
      }
      await sleep(2000 * attempt);
    }
  }
}

/**
 * Envoie la sauvegarde locale vers une session serveur NEUVE (peu importe l'état de
 * l'ancienne, qui a pu expirer), puis lance le traitement. La sauvegarde locale n'est
 * supprimée qu'une fois le job démarré : un échec d'envoi laisse tout reprenable.
 */
export async function processInterrupted(
  item: InterruptedRecording,
  options: {
    mode: TranscribeMode;
    lang: Lang;
    onUploadProgress: (sent: number, total: number) => void;
    onProgress: (progress: JobProgress) => void;
    onJobStarted: (jobId: string) => void;
  }
): Promise<TranscribeResult> {
  const { session } = item;
  const { mode, lang } = options;

  const pieces = await rebuildSegments(session);
  if (pieces.length === 0) throw new ApiError(translate(lang, "recovery.error.empty"));

  const recording = await createRecording(lang);
  const extension = extensionFor(session.mimeType);
  try {
    // Numérotation recontinuée à partir de 0 : le serveur exige une suite sans trou.
    for (const [position, piece] of pieces.entries()) {
      options.onUploadProgress(position, pieces.length);
      await uploadWithRetry(recording.recordingId, position, piece.blob, extension, lang);
    }
    options.onUploadProgress(pieces.length, pieces.length);
  } catch (error) {
    void cancelRecording(recording.recordingId, lang);
    throw error;
  }

  // L'ancienne copie serveur (si elle existe encore) ne sert plus.
  if (session.recordingId) void cancelRecording(session.recordingId, lang);

  return transcribeRecording(recording.recordingId, mode, lang, options.onProgress, (jobId) => {
    void store.deleteRecording(session.localId);
    options.onJobStarted(jobId);
  });
}

/** Supprime définitivement un enregistrement interrompu (sauvegarde locale et copie serveur). */
export async function discardInterrupted(item: InterruptedRecording, lang: Lang): Promise<void> {
  if (item.session.recordingId) await cancelRecording(item.session.recordingId, lang);
  await store.deleteRecording(item.session.localId);
}

/** À appeler quand le traitement d'un enregistrement a démarré : la sauvegarde locale n'a plus d'utilité. */
export function forgetLocalRecording(localId: string): Promise<boolean> {
  return store.deleteRecording(localId);
}
