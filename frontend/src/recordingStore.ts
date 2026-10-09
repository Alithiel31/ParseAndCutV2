import type { Lang } from "./i18n";

/**
 * Sauvegarde locale (IndexedDB) d'un enregistrement micro en cours : si l'onglet
 * plante, si le téléphone redémarre ou si la page est quittée, l'audio déjà
 * enregistré reste sur l'appareil et peut être repris au chargement suivant.
 *
 * Trois magasins :
 *  - sessions : un enregistrement (identifiant local, session serveur éventuelle…)
 *  - segments : les segments terminés (fichiers webm complets), gardés jusqu'à ce
 *    que le traitement ait démarré — même une fois envoyés, au cas où la copie
 *    du serveur aurait expiré entre-temps
 *  - chunks   : les morceaux d'une seconde du segment EN COURS, pour ne perdre que
 *    ~1 s si la page disparaît au milieu d'un segment
 *
 * Tout est facultatif : si IndexedDB est indisponible (navigation privée, quota…),
 * chaque fonction échoue en silence et l'enregistrement continue sans cette sécurité.
 */

const DB_NAME = "pac-recordings";
const DB_VERSION = 1;

export interface StoredSession {
  localId: string;
  lang: Lang;
  mimeType: string;
  segmentSeconds: number;
  startedAt: number;
  // Dernier signe de vie : distingue un enregistrement abandonné d'un autre onglet encore actif.
  updatedAt: number;
  // Session serveur éventuelle (copie en ligne des segments), null si elle n'a pas pu être créée.
  recordingId: string | null;
}

export interface StoredSegment {
  localId: string;
  index: number;
  blob: Blob;
}

export interface StoredChunk {
  localId: string;
  index: number;
  seq: number;
  blob: Blob;
}

let dbPromise: Promise<IDBDatabase | null> | null = null;

function openDb(): Promise<IDBDatabase | null> {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve) => {
    try {
      if (typeof indexedDB === "undefined") {
        resolve(null);
        return;
      }
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = () => {
        const db = request.result;
        db.createObjectStore("sessions", { keyPath: "localId" });
        db.createObjectStore("segments", { keyPath: ["localId", "index"] });
        db.createObjectStore("chunks", { keyPath: ["localId", "index", "seq"] });
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => resolve(null);
      request.onblocked = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
  return dbPromise;
}

function wrap<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// Exécute `action` dans une transaction ; renvoie `fallback` si le stockage est
// indisponible ou si l'opération échoue.
async function run<T>(
  stores: string[],
  mode: IDBTransactionMode,
  fallback: T,
  action: (tx: IDBTransaction) => Promise<T>
): Promise<T> {
  try {
    const db = await openDb();
    if (!db) return fallback;
    const tx = db.transaction(stores, mode);
    const done = new Promise<void>((resolve, reject) => {
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error);
    });
    const result = await action(tx);
    await done;
    return result;
  } catch {
    return fallback;
  }
}

// Intervalle de clés [localId, …] : tout ce qui appartient à un enregistrement.
const ofRecording = (localId: string) => IDBKeyRange.bound([localId], [localId, []]);

export function putSession(session: StoredSession): Promise<boolean> {
  return run(["sessions"], "readwrite", false, async (tx) => {
    await wrap(tx.objectStore("sessions").put(session));
    return true;
  });
}

export function listSessions(): Promise<StoredSession[]> {
  return run(["sessions"], "readonly", [] as StoredSession[], (tx) => wrap(tx.objectStore("sessions").getAll()));
}

export function putSegment(segment: StoredSegment): Promise<boolean> {
  return run(["segments"], "readwrite", false, async (tx) => {
    await wrap(tx.objectStore("segments").put(segment));
    return true;
  });
}

export function listSegments(localId: string): Promise<StoredSegment[]> {
  return run(["segments"], "readonly", [] as StoredSegment[], (tx) =>
    wrap(tx.objectStore("segments").getAll(ofRecording(localId)))
  );
}

export function putChunk(localId: string, index: number, seq: number, blob: Blob): Promise<boolean> {
  const chunk: StoredChunk = { localId, index, seq, blob };
  return run(["chunks"], "readwrite", false, async (tx) => {
    await wrap(tx.objectStore("chunks").put(chunk));
    return true;
  });
}

export function listChunks(localId: string): Promise<StoredChunk[]> {
  return run(["chunks"], "readonly", [] as StoredChunk[], (tx) =>
    wrap(tx.objectStore("chunks").getAll(ofRecording(localId)))
  );
}

// Les morceaux d'un segment devenu inutile (le segment complet est enregistré).
export function deleteChunksOfSegment(localId: string, index: number): Promise<boolean> {
  return run(["chunks"], "readwrite", false, async (tx) => {
    await wrap(tx.objectStore("chunks").delete(IDBKeyRange.bound([localId, index], [localId, index, []])));
    return true;
  });
}

/** Supprime un enregistrement et tout ce qui s'y rattache. */
export function deleteRecording(localId: string): Promise<boolean> {
  return run(["sessions", "segments", "chunks"], "readwrite", false, async (tx) => {
    await wrap(tx.objectStore("sessions").delete(localId));
    await wrap(tx.objectStore("segments").delete(ofRecording(localId)));
    await wrap(tx.objectStore("chunks").delete(ofRecording(localId)));
    return true;
  });
}
