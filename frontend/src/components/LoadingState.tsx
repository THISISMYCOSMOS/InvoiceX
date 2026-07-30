import { useLanguage } from "../i18n/LanguageContext";

export function LoadingState({ label }: { label?: string }) {
  const { t } = useLanguage();
  return <p role="status">{label ?? t("Loading", "불러오는 중")}</p>;
}
