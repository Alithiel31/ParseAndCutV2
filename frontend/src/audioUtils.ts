// Petits utilitaires partagés par l'enregistreur, l'envoi par segments et la reprise.

// Extension de fichier attendue par le backend pour un type MIME produit par MediaRecorder.
export function extensionForMimeType(mimeType: string): string {
  if (mimeType.includes("mp4")) return "mp4";
  if (mimeType.includes("ogg")) return "ogg";
  if (mimeType.includes("wav")) return "wav";
  if (mimeType.includes("mpeg")) return "mp3";
  return "webm";
}

// Nom de fichier d'un segment envoyé au serveur (segment-0003.webm…).
export function segmentFilename(index: number, mimeType: string): string {
  return `segment-${String(index).padStart(4, "0")}.${extensionForMimeType(mimeType)}`;
}

export const sleep = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms));
