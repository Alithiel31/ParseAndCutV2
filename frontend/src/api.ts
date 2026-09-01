import type { Lang } from "./i18n";
import { translate } from "./i18n";

export type TranscribeMode = "summary" | "transcript";

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

// URL de l'API backend (FastAPI ParseAndCutV2).
// En prod : vide (chaîne relative) — nginx sert le frontend ET reverse-proxy /api/*
// vers le backend en local sur le Pi, donc tout passe par le même domaine
// (parseandcut.alithiel31.dev), pas de backend exposé séparément.
// En dev : VITE_API_URL=http://localhost:5000 pour taper directement sur uvicorn.
const API_URL = import.meta.env.VITE_API_URL || "";

export class ApiError extends Error {}

export async function transcribeAudio(
  file: File,
  mode: TranscribeMode = "summary",
  lang: Lang = "fr"
): Promise<TranscribeResult> {
  const formData = new FormData();
  formData.append("audio", file);
  formData.append("mode", mode);
  formData.append("lang", lang);

  const response = await fetch(`${API_URL}/api/transcribe`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    // Repli local (pas un composant, donc pas de useTranslation()) utilisé
    // uniquement quand le backend n'a pas pu renvoyer de `detail` traduit
    // (ex. réponse non-JSON).
    const err = await response
      .json()
      .catch(() => ({ detail: translate(lang, "api.httpError", { status: response.status }) }));
    throw new ApiError(err.detail || translate(lang, "api.genericError", { status: response.status }));
  }

  return response.json();
}
