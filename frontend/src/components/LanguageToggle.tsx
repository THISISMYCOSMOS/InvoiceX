import { Translate } from "@phosphor-icons/react";
import { useLanguage } from "../i18n/LanguageContext";

export function LanguageToggle({ className = "" }: { className?: string }) {
  const { language, toggleLanguage } = useLanguage();
  const isEnglish = language === "en";

  return (
    <button
      className={`language-toggle ${className}`.trim()}
      type="button"
      aria-label={isEnglish ? "한국어로 전환" : "Switch to English"}
      onClick={toggleLanguage}
    >
      <Translate aria-hidden="true" size={14} weight="bold" />
      <span>{isEnglish ? "한국어" : "EN"}</span>
    </button>
  );
}
