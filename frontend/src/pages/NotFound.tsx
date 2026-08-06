import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <main className="card">
      <title>Page introuvable · Assistant Transcripteur IA</title>

      <div className="result-header">
        <h2>🧭 Page introuvable</h2>
        <Link to="/" className="btn-secondary legal-back">← Retour</Link>
      </div>

      <p>Cette adresse ne correspond à aucune page de l'application.</p>
    </main>
  );
}
