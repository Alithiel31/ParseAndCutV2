import { useTranslation } from "../i18n";

interface UpdateBannerProps {
  onUpdate: () => void;
  onDismiss: () => void;
}

export default function UpdateBanner({ onUpdate, onDismiss }: UpdateBannerProps) {
  const { t } = useTranslation();

  return (
    <div className="update-banner">
      <span>{t("updateBanner.text")}</span>
      <button className="btn-secondary" onClick={onUpdate}>
        {t("updateBanner.update")}
      </button>
      <button className="btn-secondary" onClick={onDismiss}>
        {t("updateBanner.later")}
      </button>
    </div>
  );
}
