import { Link } from "react-router-dom";

// English translation (MVP-level, not a certified legal translation).
// Keep in sync with CguContent.fr.tsx — same structure, same sections.
export default function CguContentEn() {
  return (
    <>
      <h3>1. Purpose</h3>
      <p>
        These terms govern the use of the "AI Transcription Assistant" service (ParseAndCut),
        available at{" "}
        <a href="https://parseandcut.alithiel31.dev">parseandcut.alithiel31.dev</a> and through
        the Android app of the same name. Using the service constitutes acceptance of these
        terms.
      </p>

      <h3>2. Description of the service</h3>
      <p>
        The service automatically transcribes an audio recording, then formats the resulting
        text as a Markdown study sheet. It is{" "}
        <strong>free, ad-free, and requires no account creation</strong>.
      </p>
      <ul>
        <li>Accepted formats: mp3, mp4, wav, m4a, ogg, webm, flac, aac, opus.</li>
        <li>Maximum size: 300 MB per file.</li>
        <li>The file is split into ten-minute segments before processing.</li>
        <li>
          Transcription and formatting are performed by artificial intelligence models operated
          by a third-party provider (Groq, Inc.).
        </li>
      </ul>

      <h3>3. Access and availability</h3>
      <p>
        The service is self-hosted and provided without any availability commitment. It may be
        interrupted, modified, limited, or discontinued at any time, without notice or
        compensation, in particular for maintenance or in case of unavailability of the
        third-party services it depends on.
      </p>

      <h3>4. Your obligations</h3>
      <p>By uploading a file, you warrant that:</p>
      <ul>
        <li>
          <strong>you hold the necessary rights to the recording</strong> and, where applicable,
          the consent of the people recorded — recording a class generally requires the
          agreement of the instructor or institution, and everyone has a right to their own
          voice and image (article 9 of the French Civil Code, applicable to this service);
        </li>
        <li>
          <strong>the recording does not contain sensitive data</strong> within the meaning of
          article 9 of the GDPR (health, political opinions, religious beliefs, sexual
          orientation, biometric data, etc.) nor information covered by professional secrecy —
          medical, judicial, or business;
        </li>
        <li>the recording is not unlawful in any way.</li>
      </ul>
      <p>
        When you upload a recording containing data about third parties, you are the data
        controller for that processing and bear the corresponding obligations.
      </p>

      <h3>5. Reliability of results</h3>
      <p>
        The transcript and study sheet are produced automatically. They{" "}
        <strong>may contain errors, omissions, or fabricated statements</strong> introduced by
        the models used. The service is provided "as is", with no guarantee of accuracy,
        completeness, or fitness for a particular purpose.
      </p>
      <p>
        Generated study sheets should not be used as a sole source, nor as the basis for an
        important decision — especially in an academic, professional, medical, or legal context.
        Always verify results against the original source.
      </p>

      <h3>6. Intellectual property</h3>
      <ul>
        <li>
          The service's source code is published under the MIT license:{" "}
          <a
            href="https://github.com/Alithiel31/ParseAndCutV2"
            target="_blank"
            rel="noopener noreferrer"
          >
            github.com/Alithiel31/ParseAndCutV2
          </a>.
        </li>
        <li>
          You retain full rights to the recordings you upload. The publisher claims no rights
          over study sheets generated from your content.
        </li>
      </ul>

      <h3>7. Liability</h3>
      <p>
        The service is provided free of charge by an individual, on a non-professional basis.
        The publisher's liability cannot be engaged for damages resulting from the use of the
        service, the inaccuracy of the results produced, or its unavailability, to the extent
        permitted by applicable law.
      </p>

      <h3>8. Reliance on third-party services</h3>
      <p>
        Operating the service requires transmitting your content to Groq, Inc. for transcription
        and formatting purposes. The terms of this processing are detailed in the{" "}
        <Link to="/politique-de-confidentialite">privacy policy</Link>. Unavailability of this
        provider results in unavailability of the service.
      </p>

      <h3>9. Personal data</h3>
      <p>
        Personal data processing is described in the{" "}
        <Link to="/politique-de-confidentialite">privacy policy</Link>, which forms an integral
        part of these terms.
      </p>

      <h3>10. Suspension</h3>
      <p>
        Access to the service may be restricted or suspended in the event of abusive use,
        large-scale automated use, or use manifestly contrary to these terms.
      </p>

      <h3>11. Changes to these terms</h3>
      <p>
        These terms may be changed at any time. The applicable version is the one published on
        this page, whose last-updated date appears at the top.
      </p>

      <h3>12. Governing law</h3>
      <p>
        These terms are governed by French law. In the event of a dispute, an amicable solution
        will be sought first, by email at{" "}
        <a href="mailto:contact@alithiel31.dev">contact@alithiel31.dev</a>.
      </p>

      <p>
        See also:{" "}
        <Link to="/politique-de-confidentialite">privacy policy</Link> ·{" "}
        <Link to="/mentions-legales">legal notice</Link>
      </p>
    </>
  );
}
