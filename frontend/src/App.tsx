import { useEffect } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { useRegisterSW } from "virtual:pwa-register/react";
import "./App.css";
import Footer from "./components/Footer";
import UpdateBanner from "./components/UpdateBanner";

export default function App() {
  const { pathname } = useLocation();

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
      <header>
        <h1>
          <Link to="/">🎓 Assistant Transcripteur <span>IA</span></Link>
        </h1>
        <p>Transcription Whisper · Structuration par IA · PWA installable</p>
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
