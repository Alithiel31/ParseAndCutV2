import type { TranscribeMode } from "../api";
import { useTranslation } from "../i18n";

interface ModeSelectorProps {
  mode: TranscribeMode;
  onChange: (mode: TranscribeMode) => void;
  disabled: boolean;
}

const OPTIONS = [
  { value: "summary", icon: "✦", label: "home.mode.summary", description: "home.mode.summaryDescription" },
  { value: "transcript", icon: "≋", label: "home.mode.transcript", description: "home.mode.transcriptDescription" },
] as const;

export default function ModeSelector({ mode, onChange, disabled }: ModeSelectorProps) {
  const { t } = useTranslation();

  return (
    <div className="mode-selector" role="radiogroup" aria-label={t("home.modeSelector.label")}>
      {OPTIONS.map((option) => (
        <label key={option.value} className={`mode-option${mode === option.value ? " active" : ""}`}>
          <input
            type="radio"
            name="mode"
            value={option.value}
            checked={mode === option.value}
            onChange={() => onChange(option.value)}
            disabled={disabled}
          />
          <span className="mode-icon" aria-hidden="true">{option.icon}</span>
          <span className="mode-copy"><strong>{t(option.label)}</strong><small>{t(option.description)}</small></span>
        </label>
      ))}
    </div>
  );
}
