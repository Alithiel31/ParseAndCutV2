import { useTranslation } from "../i18n";
import { STEPS } from "../steps";
import type { TranscribeMode } from "../api";

interface ProgressStepsProps {
  activeId: string;
  mode: TranscribeMode;
}

export default function ProgressSteps({ activeId, mode }: ProgressStepsProps) {
  const { t } = useTranslation();
  const visibleSteps = mode === "transcript" ? STEPS.filter((step) => step.id !== "step-llm") : STEPS;
  const activeIdx = visibleSteps.findIndex((s) => s.id === activeId);

  return (
    <ol className="progress-steps" aria-label={t("home.progress.label")}>
      {visibleSteps.map((s, idx) => {
        const done = idx < activeIdx;
        let cls = "step-badge";
        if (done) cls += " done";
        else if (idx === activeIdx) cls += " active";
        return (
          <li key={s.id} className={cls} aria-current={idx === activeIdx ? "step" : undefined}>
            {done && <span className="step-check" aria-hidden="true">✓</span>}
            {t(s.labelKey)}
            {done && <span className="sr-only"> {t("steps.done")}</span>}
          </li>
        );
      })}
    </ol>
  );
}
