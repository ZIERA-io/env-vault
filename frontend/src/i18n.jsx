import { createContext, useContext, useState, useCallback, useEffect } from "react";
import { translations, LANGS } from "./translations.js";

const I18nContext = createContext();
const KEY = "env_vault_lang";

function detectLang() {
  const saved = localStorage.getItem(KEY);
  if (saved && translations[saved]) return saved;
  const nav = (navigator.language || "en").slice(0, 2).toLowerCase();
  return translations[nav] ? nav : "en";
}

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(detectLang);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((l) => {
    if (translations[l]) {
      localStorage.setItem(KEY, l);
      setLangState(l);
    }
  }, []);

  const t = useCallback(
    (key, vars) => {
      let s = translations[lang]?.[key] ?? translations.en[key] ?? key;
      if (vars) {
        for (const [k, v] of Object.entries(vars)) {
          s = s.split(`{${k}}`).join(String(v));
        }
      }
      return s;
    },
    [lang]
  );

  return (
    <I18nContext.Provider value={{ lang, setLang, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export const useI18n = () => useContext(I18nContext);
export { LANGS };
