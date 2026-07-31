import { useLanguage } from "../i18n/LanguageContext";

export function PdfViewer({ storageUrl, fileName }: { storageUrl?: string; fileName?: string }) {
  const { t } = useLanguage();
  if (!storageUrl) {
    return <p>{t("No PDF is available for preview.", "미리볼 PDF가 없습니다.")}</p>;
  }

  return <iframe title={fileName ?? t("PDF preview", "PDF 미리보기")} src={storageUrl} />;
}
