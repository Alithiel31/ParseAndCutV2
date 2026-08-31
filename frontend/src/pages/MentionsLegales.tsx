import LegalPage from "../components/LegalPage";
import MentionsLegalesContentFr from "../content/legal/MentionsLegalesContent.fr";
import MentionsLegalesContentEn from "../content/legal/MentionsLegalesContent.en";
import { useLanguage, useTranslation } from "../i18n";

export default function MentionsLegales() {
  const { lang } = useLanguage();
  const { t } = useTranslation();
  const Content = lang === "en" ? MentionsLegalesContentEn : MentionsLegalesContentFr;

  return (
    <LegalPage title={t("legal.mentionsLegales.title")} updatedAt={t("legal.mentionsLegales.date")}>
      <Content />
    </LegalPage>
  );
}
