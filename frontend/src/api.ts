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

export class ApiError extends Error {}

async function lireErreur(response: Response, lang: Lang): Promise<never> {
  // Repli local (pas un composant, donc pas de useTranslation()) utilisé
  // uniquement quand le backend n'a pas pu renvoyer de `detail` traduit
  // (ex. réponse non-JSON).
  const err = await response
    .json()
    .catch(() => ({ detail: translate(lang, "api.httpError", { status: response.status }) }));
  throw new ApiError(err.detail || translate(lang, "api.genericError", { status: response.status }));
}

export async function transcribeAudio(
  file: File,
  mode: TranscribeMode = "summary",
  lang: Lang = "fr",
  onProgress?: (progress: JobProgress) => void
): Promise<TranscribeResult> {
  const formData = new FormData();
  formData.append("audio", file);
  formData.append("mode", mode);
  formData.append("lang", lang);

  const startResponse = await fetch(`${API_URL}/api/transcribe/start`, {
    method: "POST",
    body: formData,
  });

  if (!startResponse.ok) {
    await lireErreur(startResponse, lang);
  }

  const { job_id: jobId } = (await startResponse.json()) as { job_id: string };

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
    });
  }
}
