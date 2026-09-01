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
}

export default function DropZone({ onFileSelected, onError, selectedFileLabel }: DropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const { t } = useTranslation();

  function handleFile(file: File | undefined) {
    if (!file) return;
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      onError(t("dropzone.tooLarge", { maxMb: MAX_SIZE_MB }));
      return;
    }
    onFileSelected(file);
  }

  function onDrop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setDragOver(false);
    handleFile(e.dataTransfer.files?.[0]);
  }

  function onChange(e: ChangeEvent<HTMLInputElement>) {
    handleFile(e.target.files?.[0]);
  }

  return (
    <>
      <label
        htmlFor="audioFile"
        className={`drop-zone${dragOver ? " drag-over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
      >
        <span className="icon">☁️</span>
        <span className="text">{t("dropzone.hint")}</span>
        <input
          ref={inputRef}
          type="file"
          id="audioFile"
          accept="audio/*"
          hidden
          onChange={onChange}
        />
      </label>
      <div className="file-name-display">{selectedFileLabel}</div>
    </>
  );
}
