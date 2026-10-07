import { useRef, useState, type DragEvent, type ChangeEvent } from "react";
import { useTranslation } from "../i18n";

// Alignée sur le plafond réel de Cloudflare (100 Mo sur les plans Free/Pro) :
// un fichier plus gros passe la validation ici mais reste bloqué en silence
// par le proxy avant même d'atteindre le backend.
const MAX_SIZE_MB = 100;

interface DropZoneProps {
  onFileSelected: (file: File) => void;
  onError: (message: string) => void;
  selectedFileLabel: string;
  disabled?: boolean;
}

export default function DropZone({ onFileSelected, onError, selectedFileLabel, disabled = false }: DropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const { t } = useTranslation();

  function handleFile(file: File | undefined) {
    if (!file || disabled) return;
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      onError(t("dropzone.tooLarge", { maxMb: MAX_SIZE_MB }));
      return;
    }
    onFileSelected(file);
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    handleFile(e.dataTransfer.files?.[0]);
  }

  function onChange(e: ChangeEvent<HTMLInputElement>) {
    handleFile(e.target.files?.[0]);
  }

  return (
    <>
      <div
        className={`drop-zone${dragOver ? " drag-over" : ""}`}
        aria-disabled={disabled}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
      >
        <span className="drop-zone-icon" aria-hidden="true">♫</span>
        <div className="drop-zone-copy">
          <strong>{t("dropzone.title")}</strong>
          <span className="text">{t("dropzone.hint")}</span>
        </div>
        <button
          type="button"
          className="btn-file-picker"
          onClick={() => inputRef.current?.click()}
          disabled={disabled}
        >
          {t("dropzone.choose")}
        </button>
        <input
          ref={inputRef}
          type="file"
          id="audioFile"
          accept="audio/*"
          hidden
          disabled={disabled}
          onChange={onChange}
        />
        <span className="drop-zone-limit">{t("dropzone.limits", { maxMb: MAX_SIZE_MB })}</span>
      </div>
      {selectedFileLabel && <div className="file-name-display" aria-live="polite">{selectedFileLabel}</div>}
    </>
  );
}
