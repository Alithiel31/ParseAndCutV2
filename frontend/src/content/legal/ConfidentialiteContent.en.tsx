import { Link } from "react-router-dom";

// English translation (MVP-level, not a certified legal translation).
// Keep in sync with ConfidentialiteContent.fr.tsx — same structure, same
// sections. GDPR/CNIL references are kept as-is since this service and its
// data flows remain governed by French/EU law regardless of UI language.
export default function ConfidentialiteContentEn() {
  return (
    <>
      <p>
        This policy describes the personal data processing carried out by the "AI Transcription
        Assistant" service (ParseAndCut), available at{" "}
        <a href="https://parseandcut.alithiel31.dev">parseandcut.alithiel31.dev</a> and through
        the Android app of the same name, which displays this same site.
      </p>

      <h3>1. Data controller</h3>
      <p>
        Alithiel31, non-professional publisher of the service.
        <br />
        Contact: <a href="mailto:contact@alithiel31.dev">contact@alithiel31.dev</a>
      </p>
      <p>
        No data protection officer has been appointed: the conditions of article 37 of the GDPR
        are not met for this service.
      </p>

      <h3>2. Data processed</h3>
      <ul>
        <li>
          <strong>The audio file you upload</strong>: its content, name, and size.
        </li>
        <li>
          <strong>Data derived from it</strong>: the transcribed text and the generated study
          sheet.
        </li>
        <li>
          <strong>Technical connection data</strong>: IP address, HTTP headers, and user agent,
          sent to the server with every request.
        </li>
      </ul>
      <p>
        <strong>No account data is collected</strong>: the service requires no registration, no
        username, no password, and no email address.
      </p>
      <p>
        An audio recording may contain personal data about third parties (the voice of an
        instructor, colleagues, or other participants). The resulting responsibilities are
        detailed in the <Link to="/cgu">terms of use</Link>.
      </p>

      <h3>3. Purposes and legal bases</h3>
      <ul>
        <li>
          <strong>Providing the requested transcript and study sheet</strong> — performance of
          the service you request (GDPR article 6.1.b).
        </li>
        <li>
          <strong>Operating and securing the server</strong> (technical logs) — legitimate
          interest (GDPR article 6.1.f).
        </li>
      </ul>
      <p>No data is used for advertising, profiling, or resale purposes.</p>

      <h3>4. Recipients</h3>
      <p>The content you upload is transmitted to <strong>a single provider</strong>:</p>
      <ul>
        <li>
          <strong>Groq, Inc.</strong> (United States), which performs the automatic transcription
          (<code>whisper-large-v3</code> model) and then the text formatting (
          <code>openai/gpt-oss-120b</code> model). Audio segments, then the transcribed text, are
          sent to it via its API. Its processing is governed by its own privacy policy:{" "}
          <a href="https://groq.com/privacy-policy/" target="_blank" rel="noopener noreferrer">
            groq.com/privacy-policy
          </a>.
        </li>
      </ul>
      <p>
        In addition, <strong>Cloudflare, Inc.</strong> (United States) acts as a technical
        intermediary that hosts the site and encrypts traffic: all traffic passes through its
        infrastructure.
      </p>
      <p>
        There is no other recipient. The service uses no audience-measurement tool, no
        advertising network, and no third-party analytics service.
      </p>

      <h3>5. Transfers outside the European Union</h3>
      <p>
        As Groq, Inc. and Cloudflare, Inc. are established in the United States, audio segments,
        transcribed text, and connection data are transferred outside the European Union, under
        chapter V of the GDPR (articles 44 et seq.). The applicable safeguards are those
        published by each of these providers; we invite you to review their respective policies
        before uploading a sensitive recording.
      </p>

      <h3>6. Retention period</h3>
      <p>This is the most important point about this service: it retains nothing.</p>
      <ul>
        <li>
          The audio file is written to a temporary server directory only during processing, then{" "}
          <strong>deleted at the end of the request</strong>, including when an error occurs
          along the way.
        </li>
        <li>
          The file is split into ten-minute segments; each segment is{" "}
          <strong>deleted immediately after it is transcribed</strong>.
        </li>
        <li>
          The transcript and generated study sheet are processed <strong>in memory only</strong>,
          returned to your browser, and never written to disk. The service has no database.
        </li>
        <li>
          The effective retention period is therefore that of the processing itself: a few
          seconds to a few minutes.
        </li>
        <li>
          The server's technical logs record the file name, its size, the number of segments, and
          the number of characters transcribed. <strong>The transcript content itself is not
          logged.</strong> These logs are kept for the duration of the server's log rotation.
        </li>
      </ul>
      <p>
        The generated study sheet then only exists in your browser, for the duration of the
        session: closing or reloading the page makes it disappear. Remember to copy it if you
        want to keep it.
      </p>

      <h3>7. Cookies and trackers</h3>
      <p>
        <strong>The service sets no cookies</strong>, uses no advertising tracker, and performs
        no audience measurement. It stores nothing in your browser's local storage.
      </p>
      <p>
        Only a technical "service worker" cache stores the interface files (code, styles, icons)
        to allow the app to be installed and displayed offline. This cache contains no personal
        data and transcription requests are never stored in it. Being strictly necessary for the
        service, it is exempt from consent under article 82 of the French Data Protection Act
        ("loi Informatique et Libertés") — which is why no cookie banner is shown.
      </p>
      <p>
        Cloudflare may, for security reasons, set a cookie strictly necessary to protect the site
        against abuse. It serves no advertising tracking purpose.
      </p>

      <h3>8. Security</h3>
      <ul>
        <li>All exchanges are end-to-end encrypted over HTTPS.</li>
        <li>No persistent storage of content, so no leak is possible after the fact.</li>
        <li>The uploaded file name is sanitized before being written to the server.</li>
        <li>Accepted file formats and sizes are restricted.</li>
        <li>The absence of accounts removes any risk tied to compromised credentials.</li>
      </ul>

      <h3>9. Your rights</h3>
      <p>
        You have the rights of access, rectification, erasure, restriction, objection, and
        portability provided for in articles 15 to 22 of the GDPR.
      </p>
      <p>
        In full transparency: since the service uses no account and does not retain processed
        content, there is in practice no data to disclose to you or erase once your request is
        complete. These rights can therefore only be exercised over the connection data present
        in the technical logs.
      </p>
      <p>
        For any request: <a href="mailto:contact@alithiel31.dev">contact@alithiel31.dev</a>. You
        may also file a complaint with the CNIL (the French data protection authority) — 3 place
        de Fontenoy, TSA 80715, 75334 Paris Cedex 07, France —{" "}
        <a href="https://www.cnil.fr">www.cnil.fr</a>.
      </p>

      <h3>10. Automated decision-making</h3>
      <p>
        Transcription and study-sheet generation are fully automated, but they produce no legal
        effect or similarly significant effect on you within the meaning of GDPR article 22.
      </p>

      <h3>11. Minors</h3>
      <p>
        The service is not intended for people under fifteen without the consent of the holder of
        parental authority (GDPR article 8 and the French Data Protection Act).
      </p>

      <h3>12. Changes to this policy</h3>
      <p>
        This policy may be changed to reflect changes to the service. The last-updated date
        appears at the top of this page.
      </p>

      <p>
        See also: <Link to="/cgu">terms of use</Link> ·{" "}
        <Link to="/mentions-legales">legal notice</Link>
      </p>
    </>
  );
}
