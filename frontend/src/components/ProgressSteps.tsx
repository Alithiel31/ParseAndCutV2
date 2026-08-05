export interface Step {
  id: string;
  label: string;
}

export const STEPS: Step[] = [
  { id: "step-upload", label: "📤 Envoi" },
  { id: "step-cut", label: "✂️ Découpage" },
  { id: "step-whisper", label: "🎙️ Transcription" },
  { id: "step-llm", label: "🧠 Structuration" },
];

interface ProgressStepsProps {
  activeId: string;
  done: boolean;
}

export default function ProgressSteps({ activeId, done }: ProgressStepsProps) {
  const activeIdx = STEPS.findIndex((s) => s.id === activeId);

  return (
    <div className="progress-steps">
      {STEPS.map((s, idx) => {
        let cls = "step-badge";
        if (done || idx < activeIdx) cls += " done";
        else if (idx === activeIdx) cls += " active";
        return (
          <span key={s.id} className={cls}>
            {s.label}
          </span>
        );
      })}
    </div>
  );
}
