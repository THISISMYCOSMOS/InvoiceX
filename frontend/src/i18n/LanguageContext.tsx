/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type Language = "en" | "ko";

interface LanguageContextValue {
  language: Language;
  toggleLanguage: () => void;
  t: (english: string, korean: string) => string;
}

const STORAGE_KEY = "invoicex-language";

const LanguageContext = createContext<LanguageContextValue>({
  language: "en",
  toggleLanguage: () => undefined,
  t: (english) => english,
});

function getInitialLanguage(): Language {
  return window.localStorage.getItem(STORAGE_KEY) === "ko" ? "ko" : "en";
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(getInitialLanguage);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, language);
    document.documentElement.lang = language;
  }, [language]);

  const value = useMemo<LanguageContextValue>(() => ({
    language,
    toggleLanguage: () => setLanguage((current) => current === "en" ? "ko" : "en"),
    t: (english, korean) => language === "ko" ? korean : english,
  }), [language]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  return useContext(LanguageContext);
}
