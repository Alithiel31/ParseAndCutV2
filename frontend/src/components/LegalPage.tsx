import type { ReactNode } from "react";
import { Link } from "react-router-dom";

interface LegalPageProps {
  title: string;
  updatedAt: string;
  children: ReactNode;
}

export default function LegalPage({ title, updatedAt, children }: LegalPageProps) {
  return (
    <main className="card">
      {/* React 19 remonte automatiquement <title> dans le <head> */}
      <title>{`${title} · Assistant Transcripteur IA`}</title>

      <div className="result-header">
        <h2>{title}</h2>
        <Link to="/" className="btn-secondary legal-back">← Retour</Link>
      </div>

      <p className="legal-updated">Dernière mise à jour : {updatedAt}</p>

      <div className="markdown-body">{children}</div>
    </main>
  );
}
