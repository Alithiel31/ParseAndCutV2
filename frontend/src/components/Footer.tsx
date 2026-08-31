import { NavLink } from "react-router-dom";
import { useTranslation } from "../i18n";

export default function Footer() {
  const { t } = useTranslation();

  return (
    <footer className="site-footer">
      <nav aria-label={t("footer.navLabel")}>
        <NavLink to="/mentions-legales">{t("footer.legal")}</NavLink>
        <span aria-hidden="true">·</span>
        <NavLink to="/politique-de-confidentialite">{t("footer.privacy")}</NavLink>
        <span aria-hidden="true">·</span>
        <NavLink to="/cgu">{t("footer.terms")}</NavLink>
      </nav>
      <p>{t("footer.tagline")}</p>
    </footer>
  );
}
