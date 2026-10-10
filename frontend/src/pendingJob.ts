import type { TranscribeMode } from "./api";
import type { Lang } from "./i18n";

// Job de traitement en cours, gardé sur l'appareil pour reprendre son suivi
// après un rechargement de page.
const PENDING_JOB_STORAGE_KEY = "pac_pending_job";

export interface PendingJob {
  jobId: string;
  mode: TranscribeMode;
  lang: Lang;
}

export function readPendingJob(): PendingJob | null {
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

export function savePendingJob(job: PendingJob) {
  try {
    localStorage.setItem(PENDING_JOB_STORAGE_KEY, JSON.stringify(job));
  } catch {
    // Le suivi continue dans l'onglet même si le stockage local est indisponible.
  }
}

export function clearPendingJob() {
  try {
    localStorage.removeItem(PENDING_JOB_STORAGE_KEY);
  } catch {
    // Le job est terminé ; le stockage local peut être indisponible.
  }
}
