import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Brand } from "../components/Brand";
import { LanguageToggle } from "../components/LanguageToggle";
import { useLanguage } from "../i18n/LanguageContext";

type LoginRole = "Supplier" | "Buyer" | "Investor";

const roleRoutes: Record<LoginRole, string> = {
  Supplier: "/supplier",
  Buyer: "/buyer",
  Investor: "/investor",
};

export function LoginPage() {
  const [role, setRole] = useState<LoginRole>("Supplier");
  const navigate = useNavigate();
  const { t } = useLanguage();

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    navigate(roleRoutes[role]);
  };

  return (
    <div className="screen-stage login-stage">
      <div className="login-shell">
        <section className="login-hero" aria-label="InvoiceX introduction">
          <Brand className="login-hero__brand" />
          <div className="login-hero__copy">
            <p className="login-hero__title">{t("Turn verified invoices into faster working capital.", "검증된 인보이스를 더 빠른 운전자금으로 전환하세요.")}</p>
            <p className="login-hero__description">
              {t(
                "Manage the complete journey with Buyer Verification and AI Risk Passport, from early funding to settlement.",
                "구매자 검증과 AI Risk Passport로 조기 자금조달부터 정산까지 전체 여정을 관리하세요.",
              )}
            </p>
          </div>
          <p className="login-hero__foot">{t("Solana-based supply chain finance platform", "Solana 기반 공급망 금융 플랫폼")}</p>
        </section>

        <section className="login-panel">
          <LanguageToggle className="login-language-toggle" />
          <form className="login-form" onSubmit={onSubmit}>
            <span className="eyebrow">{t("WELCOME BACK", "다시 오신 것을 환영합니다")}</span>
            <h1>{t("Sign in to InvoiceX", "InvoiceX에 로그인")}</h1>
            <p className="login-form__intro">{t("Select your company role and sign in.", "회사 역할을 선택하고 로그인하세요.")}</p>

            <div className="role-tabs" aria-label="Company role">
              {(Object.keys(roleRoutes) as LoginRole[]).map((item) => (
                <button
                  className="role-tab"
                  type="button"
                  aria-pressed={role === item}
                  key={item}
                  onClick={() => setRole(item)}
                >
                  {t(item, item === "Supplier" ? "공급자" : item === "Buyer" ? "구매자" : "투자자")}
                </button>
              ))}
            </div>

            <label className="login-field">
              <span>{t("Company email", "회사 이메일")}</span>
              <input type="email" name="email" placeholder="name@company.com" required />
            </label>

            <label className="login-field">
              <span>{t("Password", "비밀번호")}</span>
              <input type="password" name="password" placeholder="••••••••••••" required />
            </label>

            <div className="login-options">
              <label className="remember-option">
                <input type="checkbox" name="remember" />
                <span>{t("Keep me signed in", "로그인 상태 유지")}</span>
              </label>
              <a href="#forgot-password">{t("Forgot password?", "비밀번호를 잊으셨나요?")}</a>
            </div>

            <button className="primary-button login-submit" type="submit">{t("Sign in", "로그인")}</button>
            <p className="login-form__foot">
              {t("New to InvoiceX?", "InvoiceX가 처음이신가요?")}{" "}
              <a href="#create-account">{t("Create a company account", "회사 계정 만들기")}</a>
            </p>
          </form>
        </section>
      </div>
    </div>
  );
}
