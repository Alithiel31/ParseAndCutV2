import { Link } from "react-router-dom";
import LegalPage from "../components/LegalPage";

export default function Confidentialite() {
  return (
    <LegalPage title="🔒 Politique de confidentialité" updatedAt="6 août 2026">
      <p>
        Cette politique décrit les traitements de données personnelles réalisés par le service
        « Assistant Transcripteur IA » (ParseAndCut), accessible sur{" "}
        <a href="https://parseandcut.alithiel31.dev">parseandcut.alithiel31.dev</a> et via
        l'application Android du même nom, qui affiche ce même site.
      </p>

      <h3>1. Responsable du traitement</h3>
      <p>
        Alithiel31, éditeur non professionnel du service.
        <br />
        Contact : <a href="mailto:contact@alithiel31.dev">contact@alithiel31.dev</a>
      </p>
      <p>
        Aucun délégué à la protection des données n'a été désigné : les conditions de
        l'article 37 du RGPD ne sont pas réunies pour ce service.
      </p>

      <h3>2. Données traitées</h3>
      <ul>
        <li>
          <strong>Le fichier audio que vous déposez</strong> : son contenu, son nom et sa taille.
        </li>
        <li>
          <strong>Les données qui en dérivent</strong> : le texte transcrit et la fiche de
          révision générée.
        </li>
        <li>
          <strong>Des données techniques de connexion</strong> : adresse IP, en-têtes HTTP et
          agent utilisateur, transmis au serveur lors de chaque requête.
        </li>
      </ul>
      <p>
        <strong>Aucune donnée de compte n'est collectée</strong> : le service ne demande ni
        inscription, ni identifiant, ni mot de passe, ni adresse e-mail.
      </p>
      <p>
        Un enregistrement audio peut contenir des données personnelles de tiers (la voix d'un
        enseignant, de collègues ou d'autres participants). Les responsabilités qui en découlent
        sont précisées dans les <Link to="/cgu">conditions générales d'utilisation</Link>.
      </p>

      <h3>3. Finalités et bases légales</h3>
      <ul>
        <li>
          <strong>Fournir la transcription et la fiche demandées</strong> — exécution du service
          que vous demandez (article 6.1.b du RGPD).
        </li>
        <li>
          <strong>Assurer le fonctionnement et la sécurité du serveur</strong> (journaux
          techniques) — intérêt légitime (article 6.1.f du RGPD).
        </li>
      </ul>
      <p>
        Aucune donnée n'est utilisée à des fins publicitaires, de profilage ou de revente.
      </p>

      <h3>4. Destinataires</h3>
      <p>
        Le contenu que vous déposez est transmis à <strong>un seul prestataire</strong> :
      </p>
      <ul>
        <li>
          <strong>Groq, Inc.</strong> (États-Unis), qui exécute la transcription automatique
          (modèle <code>whisper-large-v3</code>) puis la mise en forme du texte (modèle{" "}
          <code>llama-3.3-70b-versatile</code>). Les segments audio, puis le texte transcrit,
          lui sont envoyés via son interface de programmation. Ses traitements sont régis par sa
          propre politique de confidentialité :{" "}
          <a href="https://groq.com/privacy-policy/" target="_blank" rel="noopener noreferrer">
            groq.com/privacy-policy
          </a>.
        </li>
      </ul>
      <p>
        S'y ajoute <strong>Cloudflare, Inc.</strong> (États-Unis), intermédiaire technique qui
        assure la mise en ligne du site et le chiffrement des échanges : le trafic transite par
        son infrastructure.
      </p>
      <p>
        Il n'existe aucun autre destinataire. Le service n'utilise ni outil de mesure d'audience,
        ni régie publicitaire, ni service tiers d'analyse.
      </p>

      <h3>5. Transferts hors Union européenne</h3>
      <p>
        Groq, Inc. et Cloudflare, Inc. étant établis aux États-Unis, les segments audio, le texte
        transcrit et les données de connexion font l'objet d'un transfert hors de l'Union
        européenne, encadré par le chapitre V du RGPD (articles 44 et suivants). Les garanties
        applicables sont celles publiées par chacun de ces prestataires ; nous vous invitons à
        consulter leurs politiques respectives avant de déposer un enregistrement sensible.
      </p>

      <h3>6. Durée de conservation</h3>
      <p>C'est le point le plus important de ce service : il ne conserve rien.</p>
      <ul>
        <li>
          Le fichier audio est écrit dans un répertoire temporaire du serveur uniquement pendant
          le traitement, puis <strong>supprimé en fin de requête</strong>, y compris lorsqu'une
          erreur survient en cours de route.
        </li>
        <li>
          Le fichier est découpé en segments de dix minutes ; chaque segment est{" "}
          <strong>supprimé immédiatement après sa transcription</strong>.
        </li>
        <li>
          La transcription et la fiche générée sont traitées <strong>en mémoire uniquement</strong>,
          renvoyées à votre navigateur, et ne sont jamais écrites sur disque. Le service ne
          dispose d'aucune base de données.
        </li>
        <li>
          La durée effective de conservation est donc celle du traitement : de quelques secondes
          à quelques minutes.
        </li>
        <li>
          Les journaux techniques du serveur enregistrent le nom du fichier, sa taille, le nombre
          de segments et le nombre de caractères transcrits.{" "}
          <strong>Le contenu de la transcription n'y figure pas.</strong> Ces journaux sont
          conservés le temps de la rotation des journaux du serveur.
        </li>
      </ul>
      <p>
        La fiche générée n'existe ensuite que dans votre navigateur, le temps de la session :
        fermer ou recharger la page la fait disparaître. Pensez à la copier si vous souhaitez la
        conserver.
      </p>

      <h3>7. Cookies et traceurs</h3>
      <p>
        <strong>Le service ne dépose aucun cookie</strong>, n'utilise aucun traceur publicitaire
        et ne réalise aucune mesure d'audience. Il n'enregistre rien dans le stockage local de
        votre navigateur.
      </p>
      <p>
        Seul un cache technique de type « service worker » conserve les fichiers de l'interface
        (code, styles, icônes) afin de permettre l'installation de l'application et son
        affichage hors connexion. Ce cache ne contient aucune donnée personnelle et les requêtes
        de transcription n'y sont jamais stockées. Strictement nécessaire au service, il est
        exempté de consentement au sens de l'article 82 de la loi Informatique et Libertés —
        c'est pourquoi aucun bandeau cookies ne vous est présenté.
      </p>
      <p>
        Cloudflare peut, pour des raisons de sécurité, déposer un cookie strictement nécessaire
        à la protection du site contre les abus. Il ne sert à aucune finalité de suivi
        publicitaire.
      </p>

      <h3>8. Sécurité</h3>
      <ul>
        <li>Les échanges sont chiffrés de bout en bout en HTTPS.</li>
        <li>Aucun stockage persistant du contenu, donc aucune fuite possible a posteriori.</li>
        <li>Le nom du fichier déposé est assaini avant écriture sur le serveur.</li>
        <li>Les formats et la taille des fichiers acceptés sont restreints.</li>
        <li>L'absence de compte supprime tout risque lié à des identifiants compromis.</li>
      </ul>

      <h3>9. Vos droits</h3>
      <p>
        Vous disposez des droits d'accès, de rectification, d'effacement, de limitation,
        d'opposition et de portabilité prévus aux articles 15 à 22 du RGPD.
      </p>
      <p>
        En toute transparence : le service n'utilisant pas de compte et ne conservant pas les
        contenus traités, il n'existe en pratique aucune donnée à vous communiquer ni à effacer
        une fois votre requête terminée. Ces droits ne peuvent donc s'exercer que sur les
        données de connexion présentes dans les journaux techniques.
      </p>
      <p>
        Pour toute demande : <a href="mailto:contact@alithiel31.dev">contact@alithiel31.dev</a>.
        Vous pouvez également introduire une réclamation auprès de la CNIL — 3 place de
        Fontenoy, TSA 80715, 75334 Paris Cedex 07 — <a href="https://www.cnil.fr">www.cnil.fr</a>.
      </p>

      <h3>10. Décision automatisée</h3>
      <p>
        La transcription et la génération de la fiche sont entièrement automatisées, mais elles
        ne produisent aucun effet juridique ni aucun effet significatif à votre égard au sens de
        l'article 22 du RGPD.
      </p>

      <h3>11. Mineurs</h3>
      <p>
        Le service n'est pas destiné aux personnes de moins de quinze ans sans l'accord du
        titulaire de l'autorité parentale (article 8 du RGPD et loi Informatique et Libertés).
      </p>

      <h3>12. Modification de la politique</h3>
      <p>
        Cette politique peut être modifiée pour refléter une évolution du service. La date de
        dernière mise à jour figure en haut de cette page.
      </p>

      <p>
        Voir aussi : <Link to="/cgu">conditions générales d'utilisation</Link> ·{" "}
        <Link to="/mentions-legales">mentions légales</Link>
      </p>
    </LegalPage>
  );
}
