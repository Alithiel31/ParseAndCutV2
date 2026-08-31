import { useEffect } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { useRegisterSW } from "virtual:pwa-register/react";
import "./App.css";
import Footer from "./components/Footer";
import UpdateBanner from "./components/UpdateBanner";
import LanguageSwitcher from "./components/LanguageSwitcher";
import { useTranslation } from "./i18n";

export default function App() {
  const { pathname } = useLocation();
  const { t } = useTranslation();

  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW(_url, registration) {
      // Vérifie les mises à jour périodiquement
      if (registration) {
        setInterval(() => registration.update(), 60 * 60 * 1000);
      }
    },
  });

  // Sans data router, react-router ne réinitialise pas le défilement entre les pages
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return (
    <div className="container">
      <title>{t("meta.title")}</title>
      <meta name="description" content={t("meta.description")} />

      <header>
        <LanguageSwitcher />
        <h1>
          <Link to="/">🎓 {t("meta.appName")}</Link>
        </h1>
        <p>{t("header.tagline")}</p>
      </header>

      <Outlet />

      <Footer />

      {needRefresh && (
        <UpdateBanner
          onUpdate={() => updateServiceWorker(true)}
          onDismiss={() => setNeedRefresh(false)}
        />
      )}
    </div>
  );
}
