import { useLanguage } from "../i18n/LanguageContext";

/** Uses the URL the backend built, so the cluster always matches the chain it used. */
export function ExplorerLink({ explorerUrl }: { explorerUrl: string }) {
  const { t } = useLanguage();
  return <a href={explorerUrl} target="_blank" rel="noreferrer">{t("View on Solana Explorer", "Solana Explorer에서 보기")}</a>;
}
