import { useLanguage } from "../i18n/LanguageContext";

export function ErrorState({ error }: { error: unknown }) {
  const { t } = useLanguage();
  const message = error instanceof Error ? error.message : t("Unable to process the request.", "요청을 처리할 수 없습니다.");
  return <p role="alert">{message}</p>;
}
