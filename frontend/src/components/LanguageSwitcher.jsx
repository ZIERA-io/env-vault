import { useI18n, LANGS } from "../i18n.jsx";
import Icon from "./Icon.jsx";

// 언어 선택 드롭다운 (헤더 / 인증 화면 공용)
export default function LanguageSwitcher({ compact = false }) {
  const { lang, setLang, t } = useI18n();
  return (
    <label className="relative inline-flex items-center" title={t("lang.label")}>
      <Icon
        name="globe"
        size={16}
        className="pointer-events-none absolute left-2.5 text-slate-400"
      />
      <select
        aria-label={t("lang.label")}
        value={lang}
        onChange={(e) => setLang(e.target.value)}
        className={`cursor-pointer appearance-none rounded-lg border border-slate-300 bg-white py-1.5 pl-8 pr-7 text-sm text-slate-700 outline-none transition hover:bg-slate-50 focus:border-brand-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800 ${
          compact ? "" : "min-w-[7rem]"
        }`}
      >
        {LANGS.map((l) => (
          <option key={l.code} value={l.code}>
            {l.label}
          </option>
        ))}
      </select>
      <span className="pointer-events-none absolute right-2 text-slate-400">▾</span>
    </label>
  );
}
