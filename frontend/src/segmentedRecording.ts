import { cancelRecording, createRecording, SegmentUploadError, uploadSegment } from "./api";
import type { Lang } from "./i18n";

// Durée d'un segment tant que le serveur n'a pas annoncé la sienne.
const DEFAULT_SEGMENT_SECONDS = 300;
// Attentes entre deux tentatives d'envoi d'un même segment (la dernière se répète).
const RETRY_DELAYS_MS = [2000, 4000, 8000, 16000, 30000];
// À l'arrêt, temps maximal d'attente de l'envoi des derniers segments.
const DRAIN_TIMEOUT_MS = 10000;

export interface SegmentSyncStatus {
  sent: number;
  total: number;
  // Un segment n'a pas pu être envoyé de façon définitive (pas seulement en attente).
  failed: boolean;
}

export interface RecordedUpload {
  recordingId: string;
  // Tous les segments sont sur le serveur : on peut lancer le traitement sans renvoyer le fichier.
  complete: boolean;
}

interface PendingSegment {
  index: number;
  blob: Blob;
  attempts: number;
}

function extensionFor(mimeType: string): string {
  if (mimeType.includes("mp4")) return "mp4";
  if (mimeType.includes("ogg")) return "ogg";
  return "webm";
}

const sleep = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms));

/**
 * Enregistre le même flux micro en segments autonomes (un fichier complet toutes
 * les ~5 min) et les envoie au serveur au fil de l'eau.
 *
 * C'est un filet de sécurité *en plus* de l'enregistrement continu de
 * AudioRecorder : si la création de la session ou un envoi échoue, rien ne
 * bloque l'enregistrement, et le fichier complet reste disponible en repli.
 */
export class SegmentedRecording {
  private recorder: MediaRecorder | null = null;
  private timer: number | null = null;
  private lastTick = 0;
  private elapsedSec = 0;
  private paused = false;
  private segmentSeconds = DEFAULT_SEGMENT_SECONDS;

  private nextIndex = 0;
  private queue: PendingSegment[] = [];
  private sent = 0;
  private total = 0;
  private failed = false;
  private working = false;
  private idleWaiters: Array<() => void> = [];

  private disabled = false;
  private cancelled = false;
  private recordingId: string | null = null;
  private ready: Promise<boolean> = Promise.resolve(false);

  private readonly stream: MediaStream;
  private readonly mimeType: string;
  private readonly lang: Lang;
  private readonly onStatus?: (status: SegmentSyncStatus) => void;

  constructor(
    stream: MediaStream,
    mimeType: string,
    lang: Lang,
    onStatus?: (status: SegmentSyncStatus) => void
  ) {
    this.stream = stream;
    this.mimeType = mimeType;
    this.lang = lang;
    this.onStatus = onStatus;
  }

  start(): void {
    // La session serveur se crée en parallèle : le premier segment est déjà en
    // cours d'enregistrement, aucune seconde n'est perdue le temps de la requête.
    this.ready = createRecording(this.lang)
      .then((session) => {
        this.recordingId = session.recordingId;
        this.segmentSeconds = session.segmentSeconds || DEFAULT_SEGMENT_SECONDS;
        return true;
      })
      .catch(() => {
        this.disabled = true;
        this.queue = [];
        return false;
      });

    this.recorder = this.startRecorder();
    this.lastTick = Date.now();
    this.timer = window.setInterval(() => this.tick(), 1000);
  }

  pause(): void {
    this.paused = true;
    if (this.recorder?.state === "recording") this.recorder.pause();
  }

  resume(): void {
    this.paused = false;
    this.lastTick = Date.now();
    if (this.recorder?.state === "paused") this.recorder.resume();
  }

  /** Termine l'enregistrement et attend (brièvement) l'envoi des derniers segments. */
  async stop(): Promise<RecordedUpload | null> {
    this.clearTimer();

    const recorder = this.recorder;
    this.recorder = null;
    if (recorder && recorder.state !== "inactive") {
      await new Promise<void>((resolve) => {
        const previous = recorder.onstop;
        recorder.onstop = (event) => {
          previous?.call(recorder, event);
          resolve();
        };
        recorder.stop();
      });
    }

    if (this.disabled || !(await this.ready) || !this.recordingId) return null;

    await Promise.race([this.whenIdle(), sleep(DRAIN_TIMEOUT_MS)]);

    const complete = !this.failed && this.queue.length === 0 && this.total > 0 && this.sent === this.total;
    return { recordingId: this.recordingId, complete };
  }

  /** Abandonne : arrête tout et supprime l'audio déjà envoyé au serveur. */
  discard(): void {
    this.cancelled = true;
    this.clearTimer();
    this.queue = [];
    const recorder = this.recorder;
    this.recorder = null;
    if (recorder) {
      recorder.onstop = null;
      recorder.ondataavailable = null;
      if (recorder.state !== "inactive") {
        try {
          recorder.stop();
        } catch {
          // déjà arrêté
        }
      }
    }
    if (this.recordingId) void cancelRecording(this.recordingId, this.lang);
    this.wakeIdleWaiters();
  }

  private clearTimer(): void {
    if (this.timer !== null) {
      window.clearInterval(this.timer);
      this.timer = null;
    }
  }

  private startRecorder(): MediaRecorder {
    const recorder = new MediaRecorder(this.stream, this.mimeType ? { mimeType: this.mimeType } : undefined);
    const chunks: Blob[] = [];
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunks.push(event.data);
    };
    recorder.onstop = () => {
      this.onSegmentRecorded(new Blob(chunks, { type: recorder.mimeType || this.mimeType || "audio/webm" }));
    };
    recorder.start();
    return recorder;
  }

  // Le temps se mesure à l'horloge, pas au nombre de ticks : un onglet en arrière-plan
  // voit ses minuteries ralenties, ce qui retarderait la coupure des segments.
  private tick(): void {
    const now = Date.now();
    if (!this.paused) this.elapsedSec += (now - this.lastTick) / 1000;
    this.lastTick = now;

    if (!this.paused && !this.disabled && this.elapsedSec >= this.segmentSeconds) {
      this.rotate();
    }
  }

  // Le nouveau segment démarre AVANT l'arrêt de l'ancien : quelques millisecondes se
  // chevauchent plutôt que de laisser un trou au milieu d'un mot.
  private rotate(): void {
    const previous = this.recorder;
    try {
      this.recorder = this.startRecorder();
    } catch {
      // Le navigateur refuse deux enregistreurs sur le même flux : on garde l'enregistrement
      // continu seul, sans segmentation.
      this.disabled = true;
      this.clearTimer();
      return;
    }
    this.elapsedSec = 0;
    if (previous && previous.state !== "inactive") previous.stop();
  }

  private onSegmentRecorded(blob: Blob): void {
    if (this.disabled || this.cancelled || blob.size === 0) return;
    // Numérotation à l'arrivée : un segment vide ne laisse pas de trou dans la suite.
    this.queue.push({ index: this.nextIndex++, blob, attempts: 0 });
    this.total++;
    this.emit();
    void this.pump();
  }

  private async pump(): Promise<void> {
    if (this.working) return;
    this.working = true;

    if (!(await this.ready)) {
      this.working = false;
      this.wakeIdleWaiters();
      return;
    }

    while (this.queue.length > 0 && !this.cancelled && this.recordingId) {
      const segment = this.queue[0];
      try {
        await uploadSegment(
          this.recordingId,
          segment.index,
          segment.blob,
          `segment-${String(segment.index).padStart(4, "0")}.${extensionFor(segment.blob.type)}`,
          this.lang
        );
        this.queue.shift();
        this.sent++;
      } catch (error) {
        if (error instanceof SegmentUploadError && error.retryable) {
          const delay = RETRY_DELAYS_MS[Math.min(segment.attempts, RETRY_DELAYS_MS.length - 1)];
          segment.attempts++;
          await sleep(delay);
          continue;
        }
        // Définitif (enregistrement expiré, segment refusé…) : inutile de réessayer.
        this.queue.shift();
        this.failed = true;
      }
      this.emit();
    }

    this.working = false;
    this.wakeIdleWaiters();
  }

  private emit(): void {
    this.onStatus?.({ sent: this.sent, total: this.total, failed: this.failed });
  }

  private whenIdle(): Promise<void> {
    if (!this.working && this.queue.length === 0) return Promise.resolve();
    return new Promise((resolve) => this.idleWaiters.push(resolve));
  }

  private wakeIdleWaiters(): void {
    if (this.queue.length > 0 && !this.cancelled && !this.disabled) return;
    for (const resolve of this.idleWaiters.splice(0)) resolve();
  }
}
