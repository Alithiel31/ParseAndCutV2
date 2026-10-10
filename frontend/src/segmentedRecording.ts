import { segmentFilename, sleep } from "./audioUtils";
import { cancelRecording, createRecording, SegmentUploadError, uploadSegment } from "./api";
import type { Lang } from "./i18n";
import * as store from "./recordingStore";

// Durée d'un segment tant que le serveur n'a pas annoncé la sienne.
const DEFAULT_SEGMENT_SECONDS = 300;
// Attentes entre deux tentatives (envoi d'un segment, création de la session) ; la dernière se répète.
const RETRY_DELAYS_MS = [2000, 4000, 8000, 16000, 30000];
// À l'arrêt, temps maximal d'attente de la session serveur et de l'envoi des derniers segments.
const DRAIN_TIMEOUT_MS = 10000;
// Le segment en cours est écrit localement toutes les secondes : un plantage ne perd que ~1 s.
const CHUNK_MS = 1000;
const HEARTBEAT_MS = 10000;

export interface SegmentSyncStatus {
  sent: number;
  total: number;
  // Un segment n'a pas pu être envoyé de façon définitive (pas seulement en attente).
  failed: boolean;
}

export interface RecordedUpload {
  // Identifiant de la sauvegarde locale de cet enregistrement.
  localId: string;
  // Session serveur, ou null si elle n'a pas pu être créée à temps.
  recordingId: string | null;
  // Tous les segments sont sur le serveur : on peut lancer le traitement sans renvoyer le fichier.
  complete: boolean;
}

interface PendingSegment {
  index: number;
  blob: Blob;
  attempts: number;
}

function newLocalId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * Enregistre le même flux micro en segments autonomes (un fichier complet toutes
 * les ~5 min), les sauvegarde sur l'appareil (IndexedDB) et les envoie au serveur
 * au fil de l'eau.
 *
 * C'est un filet de sécurité *en plus* de l'enregistrement continu de
 * AudioRecorder : rien de tout ça ne bloque l'enregistrement, et le fichier
 * complet reste disponible en repli. Si l'onglet disparaît, la sauvegarde locale
 * permet de reprendre (voir recovery.ts).
 */
export class SegmentedRecording {
  readonly localId = newLocalId();

  private recorder: MediaRecorder | null = null;
  private timer: number | null = null;
  private heartbeat: number | null = null;
  private lastTick = 0;
  private elapsedSec = 0;
  private paused = false;
  private segmentSeconds = DEFAULT_SEGMENT_SECONDS;
  private startedAt = 0;

  private startedCount = 0; // numéro du prochain segment : attribué au DÉMARRAGE de l'enregistreur
  private queue: PendingSegment[] = [];
  private sent = 0;
  private total = 0;
  private failed = false;
  private working = false;
  private idleWaiters: Array<() => void> = [];
  private writes = new Set<Promise<unknown>>();

  private cancelled = false; // abandon : plus rien ne doit partir
  private detached = false; // page quittée : on garde la sauvegarde locale, on cesse d'insister
  private serverAbandoned = false; // la copie serveur ne sert plus (repli sur le fichier complet)
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
    this.startedAt = Date.now();
    this.saveSession();

    // La session serveur se crée en parallèle (et se retente si le réseau manque) : le premier
    // segment est déjà en cours d'enregistrement, aucune seconde n'est perdue le temps de la requête.
    this.ready = this.createServerSession();

    this.recorder = this.startRecorder();
    this.lastTick = Date.now();
    this.timer = window.setInterval(() => this.tick(), 1000);
    this.heartbeat = window.setInterval(() => this.saveSession(), HEARTBEAT_MS);
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
  async stop(): Promise<RecordedUpload> {
    await this.stopRecording();
    // Tout est écrit localement avant de rendre la main : fermer l'onglet juste après ne perd rien.
    await Promise.allSettled([...this.writes]);
    this.saveSession();

    const created = await Promise.race([this.ready, sleep(DRAIN_TIMEOUT_MS).then(() => false)]);
    if (created) await Promise.race([this.whenIdle(), sleep(DRAIN_TIMEOUT_MS)]);

    const complete =
      created && !this.failed && this.queue.length === 0 && this.total > 0 && this.sent === this.total;
    return { localId: this.localId, recordingId: this.recordingId, complete };
  }

  /**
   * La page est quittée pendant l'enregistrement : on termine proprement le segment en cours,
   * mais on GARDE tout (sauvegarde locale et copie serveur) pour pouvoir reprendre plus tard.
   */
  detach(): void {
    this.detached = true;
    void this.stopRecording();
    this.wakeIdleWaiters();
  }

  /** La copie serveur ne sert plus (repli sur le fichier complet) : on la supprime, la sauvegarde locale reste. */
  abandonServerCopy(): void {
    this.serverAbandoned = true;
    this.queue = [];
    const recordingId = this.recordingId;
    this.recordingId = null;
    if (recordingId) void cancelRecording(recordingId, this.lang);
    this.saveSession();
    this.wakeIdleWaiters();
  }

  /** Abandonne tout : arrête l'enregistrement, supprime la copie serveur et la sauvegarde locale. */
  discard(): void {
    this.cancelled = true;
    this.clearTimers();
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
    void Promise.allSettled([...this.writes]).then(() => store.deleteRecording(this.localId));
    this.wakeIdleWaiters();
  }

  private async stopRecording(): Promise<void> {
    this.clearTimers();
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
  }

  private clearTimers(): void {
    if (this.timer !== null) window.clearInterval(this.timer);
    if (this.heartbeat !== null) window.clearInterval(this.heartbeat);
    this.timer = null;
    this.heartbeat = null;
  }

  private track<T>(promise: Promise<T>): void {
    this.writes.add(promise);
    void promise.finally(() => this.writes.delete(promise));
  }

  private saveSession(): void {
    this.track(
      store.putSession({
        localId: this.localId,
        lang: this.lang,
        mimeType: this.mimeType,
        segmentSeconds: this.segmentSeconds,
        startedAt: this.startedAt,
        updatedAt: Date.now(),
        recordingId: this.recordingId,
      })
    );
  }

  private async createServerSession(): Promise<boolean> {
    for (let attempt = 0; !this.cancelled && !this.detached && !this.serverAbandoned; attempt++) {
      try {
        const session = await createRecording(this.lang);
        if (this.cancelled || this.serverAbandoned) {
          void cancelRecording(session.recordingId, this.lang);
          return false;
        }
        this.recordingId = session.recordingId;
        this.segmentSeconds = session.segmentSeconds || DEFAULT_SEGMENT_SECONDS;
        this.saveSession();
        return true;
      } catch {
        await sleep(RETRY_DELAYS_MS[Math.min(attempt, RETRY_DELAYS_MS.length - 1)]);
      }
    }
    return false;
  }

  private startRecorder(): MediaRecorder {
    const recorder = new MediaRecorder(this.stream, this.mimeType ? { mimeType: this.mimeType } : undefined);
    const index = this.startedCount++;
    const chunks: Blob[] = [];
    let seq = 0;

    recorder.ondataavailable = (event) => {
      if (event.data.size === 0) return;
      chunks.push(event.data);
      // Copie locale du segment en cours : de quoi le reconstituer si la page disparaît ici.
      this.track(store.putChunk(this.localId, index, seq++, event.data));
    };
    recorder.onstop = () => {
      this.onSegmentRecorded(index, new Blob(chunks, { type: recorder.mimeType || this.mimeType || "audio/webm" }));
    };
    recorder.start(CHUNK_MS);
    return recorder;
  }

  // Le temps se mesure à l'horloge, pas au nombre de ticks : un onglet en arrière-plan
  // voit ses minuteries ralenties, ce qui retarderait la coupure des segments.
  private tick(): void {
    const now = Date.now();
    if (!this.paused) this.elapsedSec += (now - this.lastTick) / 1000;
    this.lastTick = now;

    if (!this.paused && this.elapsedSec >= this.segmentSeconds) {
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
      // Le navigateur refuse deux enregistreurs sur le même flux : on garde le segment en
      // cours (il se terminera à l'arrêt) et on cesse de segmenter.
      this.startedCount--;
      this.clearTimers();
      return;
    }
    this.elapsedSec = 0;
    if (previous && previous.state !== "inactive") previous.stop();
  }

  private onSegmentRecorded(index: number, blob: Blob): void {
    if (this.cancelled) return;
    this.total++;

    // Sauvegarde locale d'abord (la copie du segment complet remplace ses morceaux)…
    this.track(
      store.putSegment({ localId: this.localId, index, blob }).then(() => store.deleteChunksOfSegment(this.localId, index))
    );

    // …puis envoi. Un segment vide est quand même envoyé : il garde la numérotation continue.
    if (!this.serverAbandoned) {
      this.queue.push({ index, blob, attempts: 0 });
      void this.pump();
    }
    this.emit();
  }

  private async pump(): Promise<void> {
    if (this.working) return;
    this.working = true;

    if (!(await this.ready)) {
      this.working = false;
      this.wakeIdleWaiters();
      return;
    }

    while (this.queue.length > 0 && !this.cancelled && !this.serverAbandoned && this.recordingId) {
      const segment = this.queue[0];
      try {
        await uploadSegment(
          this.recordingId,
          segment.index,
          segment.blob,
          segmentFilename(segment.index, segment.blob.type),
          this.lang
        );
        this.queue.shift();
        this.sent++;
      } catch (error) {
        if (error instanceof SegmentUploadError && error.retryable) {
          // Page quittée : inutile d'insister, la sauvegarde locale permettra de reprendre.
          if (this.detached) break;
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
    if (this.queue.length > 0 && !this.cancelled && !this.detached && !this.serverAbandoned) return;
    for (const resolve of this.idleWaiters.splice(0)) resolve();
  }
}
