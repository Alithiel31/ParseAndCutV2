import LegalPage from "../components/LegalPage";
import CguContentFr from "../content/legal/CguContent.fr";
import CguContentEn from "../content/legal/CguContent.en";
import { useLanguage, useTranslation } from "../i18n";

export default function Cgu() {
  const { lang } = useLanguage();
  const { t } = useTranslation();
  const Content = lang === "en" ? CguContentEn : CguContentFr;

  return (
    <LegalPage title={t("legal.cgu.title")} updatedAt={t("legal.cgu.date")}>
      <Content />
    </LegalPage>
  );
}
