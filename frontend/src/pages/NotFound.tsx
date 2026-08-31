import { Link } from "react-router-dom";
import { useTranslation } from "../i18n";

export default function NotFound() {
  const { t } = useTranslation();

  return (
    <main className="card">
      <title>{`${t("notFound.pageTitle")} · ${t("meta.appName")}`}</title>

      <div className="result-header">
        <h2>{t("notFound.title")}</h2>
        <Link to="/" className="btn-secondary legal-back">{t("common.back")}</Link>
      </div>

      <p>{t("notFound.body")}</p>
    </main>
  );
}
