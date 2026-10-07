import { useLanguage, useTranslation, type Lang } from "../i18n";

const OPTIONS: { value: Lang; flag: string; code: string; name: string }[] = [
  { value: "fr", flag: "🇫🇷", code: "FR", name: "Français" },
  { value: "en", flag: "🇬🇧", code: "EN", name: "English" },
];

export default function LanguageSwitcher() {
  const { lang, setLang } = useLanguage();
  const { t } = useTranslation();

  return (
    <div className="lang-switcher" role="radiogroup" aria-label={t("langSwitcher.label")}>
      {OPTIONS.map((opt) => (
        <label key={opt.value} className={`lang-option${lang === opt.value ? " active" : ""}`}>
          <input
            type="radio"
            name="lang"
            value={opt.value}
            checked={lang === opt.value}
            onChange={() => setLang(opt.value)}
          />
          <span aria-hidden="true">{opt.flag} {opt.code}</span>
          <span className="sr-only" lang={opt.value}>{opt.name}</span>
        </label>
      ))}
    </div>
  );
}
