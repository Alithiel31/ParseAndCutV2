import { useLanguage, useTranslation, type Lang } from "../i18n";

const OPTIONS: { value: Lang; label: string }[] = [
  { value: "fr", label: "🇫🇷 FR" },
  { value: "en", label: "🇬🇧 EN" },
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
          <span>{opt.label}</span>
        </label>
      ))}
    </div>
  );
}
