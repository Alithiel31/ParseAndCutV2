export interface TranscribeStats {
  chunks: number;
  transcription_chars: number;
}

export interface TranscribeResult {
  markdown: string;
  stats: TranscribeStats;
}

// URL de l'API backend (FastAPI ParseAndCutV2).
// En prod : vide (chaîne relative) — nginx sert le frontend ET reverse-proxy /api/*
// vers le backend en local sur le Pi, donc tout passe par le même domaine
// (parseandcut.alithiel31.dev), pas de backend exposé séparément.
// En dev : VITE_API_URL=http://localhost:5000 pour taper directement sur uvicorn.
const API_URL = import.meta.env.VITE_API_URL || "";

export class ApiError extends Error {}

export async function transcribeAudio(file: File): Promise<TranscribeResult> {
  const formData = new FormData();
  formData.append("audio", file);

  const response = await fetch(`${API_URL}/api/transcribe`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const err = await response
      .json()
      .catch(() => ({ detail: `Erreur HTTP ${response.status}` }));
    throw new ApiError(err.detail || `Erreur ${response.status}`);
  }

  return response.json();
}
