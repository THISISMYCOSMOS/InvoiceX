import { useLanguage } from "../i18n/LanguageContext";

export function ExplorerLink({ signature }: { signature: string }) {
  const { t } = useLanguage();
  return <a href={`https://explorer.solana.com/tx/${encodeURIComponent(signature)}?cluster=devnet`} target="_blank" rel="noreferrer">{t("View on Solana Explorer", "Solana Explorer에서 보기")}</a>;
}
