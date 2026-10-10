import { createContext, useContext } from "react";

export type Lang = "fr" | "en";

export interface LanguageContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
}

// Séparé de LanguageProvider.tsx : un fichier de composants ne doit exporter que des
// composants pour que le rechargement à chaud (Fast Refresh) fonctionne.
export const LanguageContext = createContext<LanguageContextValue | null>(null);

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage() doit être utilisé sous <LanguageProvider>");
  return ctx;
}
