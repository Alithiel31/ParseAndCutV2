import { Link } from "react-router-dom";

// English translation (MVP-level, not a certified legal translation).
// Keep in sync with MentionsLegalesContent.fr.tsx — the underlying legal
// notice (French hosting-law disclosure, art. 6-III-2 LCEN) still applies
// regardless of UI language, since the service is hosted and published
// under French law.
export default function MentionsLegalesContentEn() {
  return (
    <>
      <h3>Publisher</h3>
      <p>
        Alithiel31
        <br />
        Contact: <a href="mailto:contact@alithiel31.dev">contact@alithiel31.dev</a>
      </p>
      <p>
        The service is published by an individual, on a non-professional and non-profit basis.
        Under article 6-III-2 of French law n° 2004-575 of 21 June 2004 for confidence in the
        digital economy ("LCEN"), a non-professional publisher who wishes to remain anonymous may
        publish only the name of their host, to whom their identity has been disclosed.
      </p>

      <h3>Publication director</h3>
      <p>Alithiel31</p>

      <h3>Host</h3>
      <p>
        Cloudflare, Inc.
        <br />
        101 Townsend Street, San Francisco, CA 94107, United States
        <br />
        <a href="https://www.cloudflare.com" target="_blank" rel="noopener noreferrer">
          www.cloudflare.com
        </a>
      </p>

      <h3>Nature of the service</h3>
      <p>
        "AI Transcription Assistant" (ParseAndCut) is a free audio transcription and study-sheet
        generation service, available at{" "}
        <a href="https://parseandcut.alithiel31.dev">parseandcut.alithiel31.dev</a> and
        distributed as an Android app. It carries no advertising, no commercial partnership, and
        no financial transaction.
      </p>

      <h3>Intellectual property</h3>
      <p>
        The source code is published under the MIT license and available at{" "}
        <a
          href="https://github.com/Alithiel31/ParseAndCutV2"
          target="_blank"
          rel="noopener noreferrer"
        >
          github.com/Alithiel31/ParseAndCutV2
        </a>. Content uploaded by users and generated study sheets remain their property.
      </p>
      <p>
        Trademarks and models mentioned belong to their respective owners: Groq is a trademark of
        Groq, Inc.; Whisper and the structuring model used are models from OpenAI, Inc., used
        here through Groq's API.
      </p>

      <h3>Technical credits</h3>
      <p>
        Service built with FastAPI, React, Vite, and FFmpeg — all published under free/open-source
        licenses.
      </p>

      <h3>Personal data</h3>
      <p>
        The processing carried out is described in the{" "}
        <Link to="/politique-de-confidentialite">privacy policy</Link>.
      </p>

      <h3>Reporting unlawful content</h3>
      <p>
        Any report can be sent to{" "}
        <a href="mailto:contact@alithiel31.dev">contact@alithiel31.dev</a>.
      </p>

      <p>
        See also:{" "}
        <Link to="/politique-de-confidentialite">privacy policy</Link> ·{" "}
        <Link to="/cgu">terms of use</Link>
      </p>
    </>
  );
}
