import fr from "./fr";
import en from "./en";
import { useLanguage } from "./LanguageContext";

export type TranslationKey = keyof typeof fr;
type Params = Record<string, string | number>;

const DICTIONARIES = { fr, en } as const;

function interpolate(template: string, params?: Params): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (match, key) =>
    key in params ? String(params[key]) : match
  );
}

export function translate(lang: keyof typeof DICTIONARIES, key: TranslationKey, params?: Params): string {
  return interpolate(DICTIONARIES[lang][key], params);
}

export function useTranslation() {
  const { lang } = useLanguage();
  return { t: (key: TranslationKey, params?: Params) => translate(lang, key, params) };
}
