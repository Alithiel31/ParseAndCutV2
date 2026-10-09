import type { InterruptedRecording } from "../recovery";
import { useLanguage, useTranslation } from "../i18n";

interface RecoveryBannerProps {
  item: InterruptedRecording;
  // D'autres enregistrements interrompus existent après celui-ci.
  moreCount: number;
  busy: boolean;
  onResume: () => void;
  onDiscard: () => void;
}

export default function RecoveryBanner({ item, moreCount, busy, onResume, onDiscard }: RecoveryBannerProps) {
  const { t } = useTranslation();
  const { lang } = useLanguage();

  const started = new Date(item.session.startedAt).toLocaleString(lang === "fr" ? "fr-FR" : "en-GB", {
    dateStyle: "short",
    timeStyle: "short",
  });
  const minutes = Math.max(1, Math.round(item.approxSeconds / 60));

  return (
    <section className="recovery-banner" aria-labelledby="recovery-title">
      <h3 id="recovery-title">🛟 {t("recovery.title")}</h3>
      <p>{t("recovery.description", { date: started, minutes, count: item.segmentCount })}</p>
      {moreCount > 0 && <p className="recorder-hint">{t("recovery.more", { count: moreCount })}</p>}
      <div className="recorder-actions">
        <button type="button" className="btn-recorder" onClick={onResume} disabled={busy}>
          {t("recovery.resume")}
        </button>
        <button type="button" className="btn-recorder btn-recorder-secondary" onClick={onDiscard} disabled={busy}>
          {t("recovery.discard")}
        </button>
      </div>
    </section>
  );
}
