import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authApi } from "../api/auth.api";
import { isMockApi } from "../api/client";
import { Brand } from "../components/Brand";
import { LanguageToggle } from "../components/LanguageToggle";
import { useLanguage } from "../i18n/LanguageContext";
import {
  authenticateDemoAccount,
  saveDemoSession,
  type LoginRole,
} from "../auth/demoAccounts";
import { useSignupAuth } from "../auth/SignupAuthContext";

const roleRoutes: Record<LoginRole, string> = {
  Supplier: "/supplier",
  Buyer: "/buyer",
  Investor: "/investor",
};

export function LoginPage() {
  const [role, setRole] = useState<LoginRole>("Supplier");
  const [loginError, setLoginError] = useState<string>();
  const navigate = useNavigate();
  const { t } = useLanguage();
  const privyAuth = useSignupAuth();

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") ?? "");
    const password = String(formData.get("password") ?? "");
    const remember = formData.get("remember") === "on";

    if (privyAuth.authenticated) await privyAuth.logout();

    if (isMockApi) {
      const account = authenticateDemoAccount(role, email, password);
      if (!account) {
        setLoginError(t(
          "Check the selected role, email, and password.",
          "선택한 역할, 이메일, 비밀번호를 확인해 주세요.",
        ));
        return;
      }
      saveDemoSession(account, remember);
    } else {
      try {
        const account = await authApi.login(role, email, password);
        saveDemoSession(account, remember, account.accessToken);
      } catch {
        setLoginError(t(
          "Check the selected role, email, and password.",
          "선택한 역할, 이메일, 비밀번호를 확인해 주세요.",
        ));
        return;
      }
    }

    setLoginError(undefined);
    navigate(roleRoutes[role]);
  };

  return (
    <div className="screen-stage login-stage">
      <div className="login-shell">
        <section className="login-hero" aria-label="InvoiceX introduction">
          <Brand className="login-hero__brand" />
          <div className="login-hero__copy">
            <p className="login-hero__title">{t("Connect verified invoices to funding and investment opportunities.", "검증된 인보이스를 자금조달과 투자 기회로 연결하세요.")}</p>
            <p className="login-hero__description">
              {t(
                "Connect supplier funding with automated investment through Buyer Verification and AI-powered risk assessment, with settlement executed transparently on Solana.",
                "구매기업 확인과 AI 기반 위험 분석으로 공급기업의 조기정산과 투자자의 자동 투자를 연결하고, 정산은 Solana에서 투명하게 처리합니다.",
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
                  onClick={() => {
                    setRole(item);
                    setLoginError(undefined);
                  }}
                >
                  {t(item, item === "Supplier" ? "공급자" : item === "Buyer" ? "구매자" : "투자자")}
                </button>
              ))}
            </div>

            <label className="login-field">
              <span>{t("Company email", "회사 이메일")}</span>
              <input
                type="email"
                name="email"
                placeholder="name@company.com"
                aria-invalid={Boolean(loginError)}
                onInput={() => setLoginError(undefined)}
                required
              />
            </label>

            <label className="login-field">
              <span>{t("Password", "비밀번호")}</span>
              <input
                type="password"
                name="password"
                placeholder="••••••••••••"
                aria-invalid={Boolean(loginError)}
                onInput={() => setLoginError(undefined)}
                required
              />
            </label>

            <div className="login-options">
              <label className="remember-option">
                <input type="checkbox" name="remember" />
                <span>{t("Keep me signed in", "로그인 상태 유지")}</span>
              </label>
              <a href="#forgot-password">{t("Forgot password?", "비밀번호를 잊으셨나요?")}</a>
            </div>

            {loginError && <p className="login-error" role="alert">{loginError}</p>}
            <button className="primary-button login-submit" type="submit">{t("Sign in", "로그인")}</button>
            <Link className="signup-change-email" to="/signup">
              {t("Sign in with verified email", "회원가입한 이메일로 로그인")}
            </Link>
            <p className="login-form__foot">
              {t("New to InvoiceX?", "InvoiceX가 처음이신가요?")}{" "}
              <Link to="/signup">{t("Create a company account", "회사 계정 만들기")}</Link>
            </p>
          </form>
        </section>
      </div>
    </div>
  );
}
