import { Check, LockKey } from "@phosphor-icons/react";
import { useLanguage } from "../i18n/LanguageContext";

export function DocumentAnalysisLoadingScreen() {
  const { t } = useLanguage();

  return (
    <section
      className="document-analysis-loading"
      aria-labelledby="document-analysis-loading-title"
      aria-busy="true"
      aria-live="polite"
    >
      <div className="document-analysis-loading__content">
        <h1 id="document-analysis-loading-title">
          {t("Identifying your invoice documents", "인보이스 문서를 식별하고 있어요")}
        </h1>
        <p className="document-analysis-loading__description">
          {t(
            "We are reading each uploaded file and organizing the information needed for verification.",
            "업로드한 문서를 읽고 검증에 필요한 정보를 정리하고 있습니다.",
          )}
        </p>

        <div
          className="document-analysis-loading__track"
          role="progressbar"
          aria-label={t("Document analysis in progress", "문서 분석 진행 중")}
        >
          <span />
        </div>

        <ol className="document-analysis-loading__steps">
          <li className="is-complete">
            <span><Check aria-hidden="true" size={13} weight="bold" /></span>
            {t("Documents uploaded securely", "문서 업로드 완료")}
          </li>
          <li className="is-active" aria-current="step">
            <span aria-hidden="true" />
            {t("Identifying documents and extracting fields", "문서 식별 및 항목 추출 중")}
          </li>
          <li>
            <span aria-hidden="true" />
            {t("Preparing the review screen", "검토 화면 준비")}
          </li>
        </ol>

        <p className="document-analysis-loading__notice">
          <LockKey aria-hidden="true" size={14} weight="fill" />
          {t(
            "Keep this window open. The review screen will appear automatically when analysis is complete.",
            "창을 닫지 마세요. 분석이 끝나면 검토 화면으로 자동 이동합니다.",
          )}
        </p>
      </div>
    </section>
  );
}
