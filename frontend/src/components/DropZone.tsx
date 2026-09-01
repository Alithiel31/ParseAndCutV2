import { useRef, useState, type DragEvent, type ChangeEvent } from "react";

const MAX_SIZE_MB = 300;

interface DropZoneProps {
  onFileSelected: (file: File) => void;
  onError: (message: string) => void;
  selectedFileLabel: string;
}

export default function DropZone({ onFileSelected, onError, selectedFileLabel }: DropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  function handleFile(file: File | undefined) {
    if (!file) return;
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      onError(`Fichier trop volumineux (max ${MAX_SIZE_MB} Mo).`);
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
        <span className="text">Glissez votre fichier audio ici ou cliquez pour choisir</span>
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
