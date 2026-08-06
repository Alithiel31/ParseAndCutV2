import { Link } from "react-router-dom";
import LegalPage from "../components/LegalPage";

export default function MentionsLegales() {
  return (
    <LegalPage title="⚖️ Mentions légales" updatedAt="6 août 2026">
      <h3>Éditeur</h3>
      <p>
        Alithiel31
        <br />
        Contact : <a href="mailto:contact@alithiel31.dev">contact@alithiel31.dev</a>
      </p>
      <p>
        Le service est édité par un particulier, à titre non professionnel et sans but lucratif.
        Conformément à l'article 6-III-2 de la loi n° 2004-575 du 21 juin 2004 pour la confiance
        dans l'économie numérique, l'éditeur non professionnel qui souhaite préserver son
        anonymat peut ne publier que le nom de son hébergeur, à qui son identité est communiquée.
      </p>

      <h3>Directeur de la publication</h3>
      <p>Alithiel31</p>

      <h3>Hébergeur</h3>
      <p>
        Cloudflare, Inc.
        <br />
        101 Townsend Street, San Francisco, CA 94107, États-Unis
        <br />
        <a href="https://www.cloudflare.com" target="_blank" rel="noopener noreferrer">
          www.cloudflare.com
        </a>
      </p>

      <h3>Nature du service</h3>
      <p>
        « Assistant Transcripteur IA » (ParseAndCut) est un service gratuit de transcription
        audio et de génération de fiches de révision, accessible sur{" "}
        <a href="https://parseandcut.alithiel31.dev">parseandcut.alithiel31.dev</a> et distribué
        sous forme d'application Android. Il ne comporte aucune publicité, aucun partenariat
        commercial et aucune transaction financière.
      </p>

      <h3>Propriété intellectuelle</h3>
      <p>
        Le code source est publié sous licence MIT et consultable à l'adresse{" "}
        <a
          href="https://github.com/Alithiel31/ParseAndCutV2"
          target="_blank"
          rel="noopener noreferrer"
        >
          github.com/Alithiel31/ParseAndCutV2
        </a>. Les contenus déposés par les utilisateurs et les fiches générées restent leur
        propriété.
      </p>
      <p>
        Les marques et modèles cités appartiennent à leurs titulaires respectifs : Groq est une
        marque de Groq, Inc. ; Llama est un modèle de Meta Platforms, Inc. ; Whisper est un
        modèle d'OpenAI, ici utilisé par l'intermédiaire de l'interface de programmation de Groq.
      </p>

      <h3>Crédits techniques</h3>
      <p>
        Service construit avec FastAPI, React, Vite et FFmpeg — tous publiés sous licence libre.
      </p>

      <h3>Données personnelles</h3>
      <p>
        Les traitements réalisés sont décrits dans la{" "}
        <Link to="/politique-de-confidentialite">politique de confidentialité</Link>.
      </p>

      <h3>Signalement d'un contenu illicite</h3>
      <p>
        Tout signalement peut être adressé à{" "}
        <a href="mailto:contact@alithiel31.dev">contact@alithiel31.dev</a>.
      </p>

      <p>
        Voir aussi :{" "}
        <Link to="/politique-de-confidentialite">politique de confidentialité</Link> ·{" "}
        <Link to="/cgu">conditions générales d'utilisation</Link>
      </p>
    </LegalPage>
  );
}
