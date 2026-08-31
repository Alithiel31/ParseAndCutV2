import { useTranslation, type TranslationKey } from "../i18n";

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

interface ProgressStepsProps {
  activeId: string;
  done: boolean;
}

export default function ProgressSteps({ activeId, done }: ProgressStepsProps) {
  const { t } = useTranslation();
  const activeIdx = STEPS.findIndex((s) => s.id === activeId);

  return (
    <div className="progress-steps">
      {STEPS.map((s, idx) => {
        let cls = "step-badge";
        if (done || idx < activeIdx) cls += " done";
        else if (idx === activeIdx) cls += " active";
        return (
          <span key={s.id} className={cls}>
            {t(s.labelKey)}
          </span>
        );
      })}
    </div>
  );
}
