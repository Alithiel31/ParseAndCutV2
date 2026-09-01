import { Link } from "react-router-dom";

// Contenu français des CGU. Garder en synchronisation manuelle avec
// CguContent.en.tsx (traduction MVP, pas de garantie juridique).
export default function CguContentFr() {
  return (
    <>
      <h3>1. Objet</h3>
      <p>
        Les présentes conditions régissent l'utilisation du service « Assistant Transcripteur
        IA » (ParseAndCut), accessible sur{" "}
        <a href="https://parseandcut.alithiel31.dev">parseandcut.alithiel31.dev</a> et via
        l'application Android du même nom. Utiliser le service vaut acceptation de ces
        conditions.
      </p>

      <h3>2. Description du service</h3>
      <p>
        Le service transcrit automatiquement un enregistrement audio, puis met en forme le texte
        obtenu sous forme d'une fiche de révision en Markdown. Il est{" "}
        <strong>gratuit, sans publicité et sans création de compte</strong>.
      </p>
      <ul>
        <li>Formats acceptés : mp3, mp4, wav, m4a, ogg, webm, flac, aac, opus.</li>
        <li>Taille maximale : 100 Mo par fichier.</li>
        <li>Le fichier est découpé en segments de dix minutes avant traitement.</li>
        <li>
          La transcription et la mise en forme sont réalisées par des modèles d'intelligence
          artificielle exploités par un prestataire tiers (Groq, Inc.).
        </li>
      </ul>

      <h3>3. Accès et disponibilité</h3>
      <p>
        Le service est auto-hébergé et fourni sans engagement de disponibilité. Il peut être
        interrompu, modifié, limité ou arrêté à tout moment, sans préavis ni indemnité,
        notamment pour maintenance ou en cas d'indisponibilité des services tiers dont il
        dépend.
      </p>

      <h3>4. Vos obligations</h3>
      <p>En déposant un fichier, vous garantissez que :</p>
      <ul>
        <li>
          <strong>vous détenez les droits nécessaires sur l'enregistrement</strong> et, le cas
          échéant, l'autorisation des personnes enregistrées — l'enregistrement d'un cours
          suppose généralement l'accord de l'enseignant ou de l'établissement, et toute personne
          dispose d'un droit sur sa voix et son image (article 9 du Code civil) ;
        </li>
        <li>
          <strong>l'enregistrement ne contient pas de données sensibles</strong> au sens de
          l'article 9 du RGPD (santé, opinions politiques, convictions religieuses, orientation
          sexuelle, données biométriques…) ni d'informations couvertes par un secret
          professionnel — médical, judiciaire ou d'affaires ;
        </li>
        <li>l'enregistrement ne présente aucun caractère illicite.</li>
      </ul>
      <p>
        Lorsque vous déposez un enregistrement contenant des données concernant des tiers, vous
        en êtes le responsable de traitement et vous en assumez les obligations.
      </p>

      <h3>5. Fiabilité des résultats</h3>
      <p>
        La transcription et la fiche sont produites automatiquement. Elles{" "}
        <strong>peuvent contenir des erreurs, des omissions ou des affirmations inventées</strong>{" "}
        par les modèles utilisés. Le service est fourni « en l'état », sans garantie d'exactitude,
        d'exhaustivité ni d'adéquation à un usage particulier.
      </p>
      <p>
        Les fiches générées ne doivent pas être utilisées comme source unique, ni servir de base
        à une décision importante — en particulier dans un contexte scolaire, professionnel,
        médical ou juridique. Vérifiez systématiquement les résultats auprès de la source
        d'origine.
      </p>

      <h3>6. Propriété intellectuelle</h3>
      <ul>
        <li>
          Le code source du service est publié sous licence MIT :{" "}
          <a
            href="https://github.com/Alithiel31/ParseAndCutV2"
            target="_blank"
            rel="noopener noreferrer"
          >
            github.com/Alithiel31/ParseAndCutV2
          </a>.
        </li>
        <li>
          Vous conservez l'intégralité de vos droits sur les enregistrements que vous déposez.
          L'éditeur ne revendique aucun droit sur les fiches générées à partir de vos contenus.
        </li>
      </ul>

      <h3>7. Responsabilité</h3>
      <p>
        Le service est fourni gratuitement par un particulier, à titre non professionnel. La
        responsabilité de l'éditeur ne saurait être engagée pour les dommages résultant de
        l'utilisation du service, de l'inexactitude des résultats produits ou de son
        indisponibilité, dans les limites permises par le droit applicable.
      </p>

      <h3>8. Dépendance à des services tiers</h3>
      <p>
        Le fonctionnement du service suppose la transmission de votre contenu à Groq, Inc. aux
        fins de transcription et de mise en forme. Les modalités de ce traitement sont détaillées
        dans la <Link to="/politique-de-confidentialite">politique de confidentialité</Link>.
        Une indisponibilité de ce prestataire entraîne celle du service.
      </p>

      <h3>9. Données personnelles</h3>
      <p>
        Les traitements de données personnelles sont décrits dans la{" "}
        <Link to="/politique-de-confidentialite">politique de confidentialité</Link>, qui fait
        partie intégrante des présentes conditions.
      </p>

      <h3>10. Suspension</h3>
      <p>
        L'accès au service peut être restreint ou suspendu en cas d'usage abusif, automatisé à
        grande échelle, ou manifestement contraire aux présentes conditions.
      </p>

      <h3>11. Modification des conditions</h3>
      <p>
        Ces conditions peuvent être modifiées à tout moment. La version applicable est celle
        publiée sur cette page, dont la date de mise à jour figure en haut.
      </p>

      <h3>12. Droit applicable</h3>
      <p>
        Les présentes conditions sont soumises au droit français. En cas de litige, une solution
        amiable sera recherchée en priorité, par courrier électronique à l'adresse{" "}
        <a href="mailto:contact@alithiel31.dev">contact@alithiel31.dev</a>.
      </p>

      <p>
        Voir aussi :{" "}
        <Link to="/politique-de-confidentialite">politique de confidentialité</Link> ·{" "}
        <Link to="/mentions-legales">mentions légales</Link>
      </p>
    </>
  );
}
