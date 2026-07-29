export function PdfViewer({ storageUrl, fileName }: { storageUrl?: string; fileName?: string }) {
  if (!storageUrl) {
    return <p>미리볼 PDF가 없습니다.</p>;
  }

  return <iframe title={fileName ?? "PDF 미리보기"} src={storageUrl} />;
}
