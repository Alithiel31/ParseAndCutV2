import { useEffect, useState, type ReactNode } from "react";
import { LanguageContext, type Lang } from "./context";

const STORAGE_KEY = "pac_lang";

function detectInitialLang(): Lang {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "fr" || stored === "en") return stored;
  } catch {
    // localStorage indisponible (navigation privée, etc.) : on retombe sur la détection navigateur
  }
  return navigator.language?.toLowerCase().startsWith("fr") ? "fr" : "en";
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(detectInitialLang);

  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      // navigation privée / stockage désactivé : la langue reste valide pour la session en cours
    }
  }, [lang]);

  return <LanguageContext.Provider value={{ lang, setLang }}>{children}</LanguageContext.Provider>;
}
