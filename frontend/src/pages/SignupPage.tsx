import { useEffect, useState, type ClipboardEvent, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { getAuthMe, getOtpClock, onboardCompany, type CompanyType } from "../api/onboarding.api";
import { useSignupAuth } from "../auth/SignupAuthContext";

type SignupStep = "email" | "verification" | "role" | "company" | "complete";
type CompanyRole = "supplier" | "buyer" | "investor";
type OtpDeadline = { expiresAtServerMs: number; serverOffsetMs: number };

const roles: Record<CompanyRole, { korean: string; english: string; description: string }> = {
  supplier: {
    korean: "공급기업",
    english: "Supplier",
    description: "매출채권을 등록하고 조기정산을 받을 수 있습니다.",
  },
  buyer: {
    korean: "구매기업",
    english: "Buyer",
    description: "거래 내용을 확인하고 만기일에 대금을 정산합니다.",
  },
  investor: {
    korean: "투자기관",
    english: "Investor",
    description: "투자 정책을 설정하고 검증된 매출채권에 Agent를 통해 자동 투자합니다.",
  },
};

const companyTypes: Record<CompanyRole, CompanyType> = {
  supplier: "SUPPLIER",
  buyer: "BUYER",
  investor: "INVESTOR",
};

const sideCopy: Record<SignupStep, string> = {
  email: "신뢰할 수 있는 기업 계정을 위해 업무용 이메일을 먼저 확인합니다.",
  verification: "보안을 위해 이메일로 전달된 6자리 코드를 확인합니다.",
  role: "가입 후 이용할 기능과 대시보드를 기업의 역할에 맞게 설정하세요.",
  company: "기업 기본정보를 등록하고 InvoiceX 계정을 완성하세요.",
  complete: "기업 계정이 즉시 활성화되었어요. 이제 역할별 대시보드에서 시작해보세요.",
};

export function SignupPage() {
  const navigate = useNavigate();
  const signupAuth = useSignupAuth();
  const [step, setStep] = useState<SignupStep>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState(["", "", "", "", "", ""]);
  const [otpDeadline, setOtpDeadline] = useState<OtpDeadline | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const [role, setRole] = useState<CompanyRole>("supplier");
  const [companyName, setCompanyName] = useState("");
  const [businessRegistrationNumber, setBusinessRegistrationNumber] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactTitle, setContactTitle] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [nextPath, setNextPath] = useState("/login");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (step !== "verification" || !otpDeadline) return;

    const getRemainingSeconds = () => Math.max(
      0,
      Math.ceil((otpDeadline.expiresAtServerMs - (Date.now() + otpDeadline.serverOffsetMs)) / 1000),
    );
    const intervalId = window.setInterval(() => {
      const nextRemainingSeconds = getRemainingSeconds();
      setRemainingSeconds(nextRemainingSeconds);
      if (nextRemainingSeconds === 0) window.clearInterval(intervalId);
    }, 250);
    return () => window.clearInterval(intervalId);
  }, [otpDeadline, step]);

  const syncOtpDeadline = async () => {
    const requestStartedAt = Date.now();
    const otpClock = await getOtpClock();
    const responseReceivedAt = Date.now();
    const estimatedClientTimeAtServerResponse = requestStartedAt
      + ((responseReceivedAt - requestStartedAt) / 2);
    setOtpDeadline({
      expiresAtServerMs: otpClock.serverTimeMs + (otpClock.expiresInSeconds * 1000),
      serverOffsetMs: otpClock.serverTimeMs - estimatedClientTimeAtServerResponse,
    });
    setRemainingSeconds(otpClock.expiresInSeconds);
  };

  const submitEmail = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (!signupAuth.configured) {
      setError("Privy App ID가 설정되지 않아 이메일 인증을 시작할 수 없습니다.");
      return;
    }
    setSubmitting(true);
    try {
      if (signupAuth.authenticated) await signupAuth.logout();
      await signupAuth.sendCode(email.trim());
      await syncOtpDeadline();
      setCode(["", "", "", "", "", ""]);
      setStep("verification");
    } catch (cause) {
      setError(toErrorMessage(cause, "인증 코드를 보내지 못했습니다."));
    } finally {
      setSubmitting(false);
    }
  };

  const submitCode = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    const verificationCode = code.join("");
    if (remainingSeconds === 0) {
      setError("인증 코드가 만료되었습니다. 코드를 재전송해 주세요.");
      return;
    }
    if (verificationCode.length !== 6) {
      setError("6자리 인증 코드를 모두 입력해 주세요.");
      return;
    }
    setSubmitting(true);
    try {
      await signupAuth.verifyCode(verificationCode);
      const accessToken = await signupAuth.getAccessToken();
      if (!accessToken) throw new Error("Privy Access Token을 확인할 수 없습니다.");
      const authMe = await getAuthMe(accessToken);
      setEmail(authMe.user.email);
      if (authMe.onboardingStatus === "COMPLETED") {
        navigate(authMe.nextPath);
        return;
      }
      setStep("role");
    } catch (cause) {
      if (isInvalidVerificationCode(cause)) {
        setCode(["", "", "", "", "", ""]);
        document.getElementById("verification-code-0")?.focus();
      }
      setError(toVerificationErrorMessage(cause));
    } finally {
      setSubmitting(false);
    }
  };

  const submitCompany = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const accessToken = await signupAuth.getAccessToken();
      if (!accessToken) throw new Error("로그인 세션이 만료되었습니다. 이메일 인증부터 다시 진행해 주세요.");
      const result = await onboardCompany(accessToken, {
        company: {
          name: companyName,
          type: companyTypes[role],
          businessRegistrationNumber,
        },
        representative: {
          name: contactName,
          title: contactTitle,
          phone: contactPhone,
        },
      });
      if (result.onboardingStatus !== "COMPLETED" || !result.embeddedWallet) {
        throw new Error("사용자 지갑 생성이 완료되지 않았습니다. 다시 시도해 주세요.");
      }
      setNextPath(result.nextPath);
      setStep("complete");
    } catch (cause) {
      setError(toErrorMessage(cause, "기업 등록을 완료하지 못했습니다."));
    } finally {
      setSubmitting(false);
    }
  };

  const resendCode = async () => {
    setError(null);
    setSubmitting(true);
    try {
      await signupAuth.sendCode(email.trim());
      await syncOtpDeadline();
      setCode(["", "", "", "", "", ""]);
      document.getElementById("verification-code-0")?.focus();
    } catch (cause) {
      setError(toErrorMessage(cause, "인증 코드를 다시 보내지 못했습니다."));
    } finally {
      setSubmitting(false);
    }
  };

  const changeEmail = async () => {
    setError(null);
    setSubmitting(true);
    try {
      await signupAuth.logout();
      setCode(["", "", "", "", "", ""]);
      setOtpDeadline(null);
      setRemainingSeconds(0);
      setStep("email");
    } catch (cause) {
      setError(toErrorMessage(cause, "인증 세션을 초기화하지 못했습니다."));
    } finally {
      setSubmitting(false);
    }
  };

  const goBack = () => {
    if (step === "email") {
      navigate("/login");
      return;
    }

    setError(null);

    const previousStep: Record<Exclude<SignupStep, "email">, SignupStep> = {
      verification: "email",
      role: "verification",
      company: "role",
      complete: "company",
    };
    setStep(previousStep[step]);
  };

  const updateCode = (index: number, value: string) => {
    setError(null);
    const digit = value.replace(/\D/g, "").slice(-1);
    setCode((current) => current.map((item, itemIndex) => itemIndex === index ? digit : item));
    if (digit && index < code.length - 1) {
      document.getElementById(`verification-code-${index + 1}`)?.focus();
    }
  };

  const pasteCode = (event: ClipboardEvent<HTMLInputElement>) => {
    const pastedDigits = event.clipboardData.getData("text").replace(/\D/g, "").slice(0, code.length);
    if (pastedDigits.length <= 1) return;

    event.preventDefault();
    setError(null);
    setCode(code.map((_, index) => pastedDigits[index] ?? ""));
    document.getElementById(`verification-code-${Math.min(pastedDigits.length, code.length) - 1}`)?.focus();
  };

  return (
    <div className="screen-stage signup-stage">
      <main className="signup-shell">
        <aside className="signup-brand-panel" aria-label="InvoiceX company account introduction">
          <div>
            <p className="signup-brand">Invoice<span>X</span></p>
            <div className="signup-brand-copy">
              <p>CREATE COMPANY ACCOUNT</p>
              <h2>{sideCopy[step]}</h2>
            </div>
          </div>
          <p className="signup-brand-foot">Solana-based supply chain finance platform</p>
        </aside>

        <section className="signup-panel">
          <header className="signup-top-row">
            <button className="signup-back" type="button" onClick={goBack}>
              {step === "email" ? "← 로그인으로" : "← 이전 단계"}
            </button>
            <p>이미 계정이 있나요? <button type="button" onClick={() => navigate("/login")}>로그인</button></p>
          </header>

          {error && <p className="signup-error" role="alert">{error}</p>}

          {step === "email" && (
            <form className="signup-content signup-content--standard" onSubmit={submitEmail}>
              <Progress current="1 / 3 기업 이메일 인증" width="one-third" />
              <h1>기업 이메일을 인증해주세요</h1>
              <p className="signup-description">InvoiceX에서 사용할 기업의 업무용 이메일을 입력해주세요. 입력한 이메일로 6자리 인증 코드를 보내드립니다.</p>
              <label className="signup-field signup-field--email">
                <span>기업 이메일</span>
                <input aria-label="기업 이메일" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@company.com" required />
                <small>기업에서 업무용으로 사용하는 이메일을 입력해주세요.</small>
              </label>
              <button className="signup-primary-button" disabled={submitting || !signupAuth.ready} type="submit">
                {submitting ? "전송 중..." : "인증 코드 받기"}
              </button>
            </form>
          )}

          {step === "verification" && (
            <form className="signup-content signup-content--standard signup-verification" onSubmit={submitCode}>
              <Progress current="1 / 3 기업 이메일 인증" width="one-third" />
              <h1>인증 코드를 입력해주세요</h1>
              <p className="signup-description"><strong>{email || "name@company.com"}</strong>으로 6자리 인증 코드를 보내드렸습니다.</p>
              <fieldset className="signup-field signup-code-field">
                <legend>인증 코드</legend>
                <div className="signup-code-inputs">
                  {code.map((value, index) => (
                    <input
                      aria-label={`${index + 1}번째 인증 코드`}
                      autoComplete={index === 0 ? "one-time-code" : "off"}
                      id={`verification-code-${index}`}
                      inputMode="numeric"
                      key={index}
                      maxLength={1}
                      onChange={(event) => updateCode(index, event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Backspace" && !value && index > 0) document.getElementById(`verification-code-${index - 1}`)?.focus();
                      }}
                      onPaste={pasteCode}
                      value={value}
                    />
                  ))}
                </div>
                <div className="signup-code-meta">
                  <span>
                    인증 코드 유효시간 <strong>{formatRemainingTime(remainingSeconds)}</strong>
                  </span>
                  <button disabled={submitting} type="button" onClick={resendCode}>코드를 받지 못하셨나요? <strong>재전송</strong></button>
                </div>
              </fieldset>
              <button className="signup-primary-button" disabled={submitting || remainingSeconds === 0} type="submit">
                {submitting ? "확인 중..." : "인증 완료"}
              </button>
              <button className="signup-change-email" disabled={submitting} type="button" onClick={changeEmail}>다른 이메일 사용하기</button>
            </form>
          )}

          {step === "role" && (
            <section className="signup-content signup-content--wide signup-role-step">
              <Progress current="2 / 3 기업 유형 선택" width="two-thirds" />
              <p className="signup-success-toast">이메일 인증이 완료되었습니다.</p>
              <h1>어떤 유형의 기업인가요?</h1>
              <p className="signup-description">InvoiceX에서 수행할 역할에 맞는 기업 유형을 선택해주세요.</p>
              <div className="signup-role-list" role="radiogroup" aria-label="기업 유형">
                {(Object.keys(roles) as CompanyRole[]).map((item) => (
                  <button
                    aria-checked={role === item}
                    className={`signup-role-option signup-role-option--${item}`}
                    key={item}
                    onClick={() => setRole(item)}
                    role="radio"
                    type="button"
                  >
                    <span className="signup-role-copy">
                      <strong>{roles[item].korean}</strong><em>{roles[item].english}</em>
                      <small>{roles[item].description}</small>
                    </span>
                    <span className="signup-role-radio" aria-hidden="true" />
                  </button>
                ))}
              </div>
              <button className="signup-primary-button" type="button" onClick={() => setStep("company")}>다음</button>
            </section>
          )}

          {step === "company" && (
            <form className="signup-content signup-content--wide signup-company-step" onSubmit={submitCompany}>
              <Progress current="3 / 3 기업 정보 입력" width="complete" />
              <h1>기업 정보를 입력해주세요.</h1>
              <p className="signup-description">InvoiceX에서 거래 및 정산에 필요한 기업의 기본정보를 등록합니다.</p>
              <div className="signup-company-fields">
                <label className="signup-field"><span>기업명</span><input aria-label="기업명" value={companyName} onChange={(event) => setCompanyName(event.target.value)} placeholder="예: 인보이스엑스 주식회사" required /></label>
                <label className="signup-field"><span>사업자등록번호</span><input aria-label="사업자등록번호" value={businessRegistrationNumber} onChange={(event) => setBusinessRegistrationNumber(event.target.value)} placeholder="000-00-00000" required /></label>
                <label className="signup-field"><span>담당자명</span><input aria-label="담당자명" value={contactName} onChange={(event) => setContactName(event.target.value)} placeholder="예: 홍길동" required /></label>
                <label className="signup-field"><span>담당자 직책</span><input aria-label="담당자 직책" value={contactTitle} onChange={(event) => setContactTitle(event.target.value)} placeholder="예: 재무팀 매니저" required /></label>
                <label className="signup-field signup-field--full"><span>담당자 연락처</span><input aria-label="담당자 연락처" value={contactPhone} onChange={(event) => setContactPhone(event.target.value)} placeholder="010-0000-0000" required /></label>
              </div>
              <div className="signup-verified-email"><span>인증된 이메일 · {email || "finance@company.com"}</span><strong>인증 완료</strong></div>
              <button className="signup-primary-button" disabled={submitting} type="submit">
                {submitting ? "사용자 지갑 생성 중..." : "기업 등록 완료"}
              </button>
              <p className="signup-company-note">별도의 서류 제출이나 관리자 승인 없이 제출 즉시 계정이 활성화됩니다.</p>
            </form>
          )}

          {step === "complete" && (
            <section className="signup-complete">
              <h1>기업 계정 생성이 완료되었습니다!</h1>
              <p>이제 InvoiceX에서 매출채권 등록, 투자 및 정산 기능을<br />이용할 수 있습니다.</p>
              <div className="signup-summary-card">
                <strong>{companyName || "ABC 주식회사"}</strong>
                <div><span>기업 유형</span><b>{roles[role].korean} · {roles[role].english}</b></div>
                <div><span>{contactName || "홍길동"} · {contactTitle || "재무팀 매니저"}</span></div>
              </div>
              <span className="signup-role-chip">가입 완료 · 활성화</span>
              <button className="signup-primary-button" type="button" onClick={() => navigate(nextPath)}>InvoiceX 시작하기</button>
            </section>
          )}
        </section>
      </main>
    </div>
  );
}

function toErrorMessage(cause: unknown, fallback: string): string {
  return cause instanceof Error && cause.message ? cause.message : fallback;
}

function isInvalidVerificationCode(cause: unknown): boolean {
  return cause instanceof Error && /invalid email and code combination/i.test(cause.message);
}

function toVerificationErrorMessage(cause: unknown): string {
  if (isInvalidVerificationCode(cause)) {
    return "인증 코드가 일치하지 않습니다. 가장 최근에 받은 코드를 입력하거나 재전송해 주세요.";
  }
  return toErrorMessage(cause, "인증 코드를 확인하지 못했습니다.");
}

function formatRemainingTime(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function Progress({ current, width }: { current: string; width: "one-third" | "two-thirds" | "complete" }) {
  return (
    <div className="signup-progress">
      <div><strong>{current}</strong><span>기업 계정 설정</span></div>
      <i><b className={`signup-progress__fill signup-progress__fill--${width}`} /></i>
    </div>
  );
}
