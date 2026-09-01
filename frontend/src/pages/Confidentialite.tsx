import LegalPage from "../components/LegalPage";
import ConfidentialiteContentFr from "../content/legal/ConfidentialiteContent.fr";
import ConfidentialiteContentEn from "../content/legal/ConfidentialiteContent.en";
import { useLanguage, useTranslation } from "../i18n";

export default function Confidentialite() {
  const { lang } = useLanguage();
  const { t } = useTranslation();
  const Content = lang === "en" ? ConfidentialiteContentEn : ConfidentialiteContentFr;

  return (
    <LegalPage title={t("legal.confidentialite.title")} updatedAt={t("legal.confidentialite.date")}>
      <Content />
    </LegalPage>
  );
}
