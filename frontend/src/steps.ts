import type { TranslationKey } from "./i18n";

// Étapes du traitement affichées par ProgressSteps (suivies par useTranscriptionJob).
export interface Step {
  id: string;
  labelKey: TranslationKey;
}

export const STEPS: Step[] = [
  { id: "step-upload", labelKey: "steps.step-upload" },
  { id: "step-cut", labelKey: "steps.step-cut" },
  { id: "step-whisper", labelKey: "steps.step-whisper" },
  { id: "step-llm", labelKey: "steps.step-llm" },
];
