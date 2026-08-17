import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

type SignupStep = "email" | "verification" | "role" | "company" | "complete";
type CompanyRole = "supplier" | "buyer" | "investor";

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

const dashboardRoutes: Record<CompanyRole, string> = {
  supplier: "/supplier",
  buyer: "/buyer",
  investor: "/investor",
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
  const [step, setStep] = useState<SignupStep>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState(["", "", "", "", "", ""]);
  const [role, setRole] = useState<CompanyRole>("supplier");
  const [companyName, setCompanyName] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactTitle, setContactTitle] = useState("");

  const submitEmail = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStep("verification");
  };

  const submitCode = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStep("role");
  };

  const submitCompany = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStep("complete");
  };

  const goBack = () => {
    if (step === "email") {
      navigate("/login");
      return;
    }

    const previousStep: Record<Exclude<SignupStep, "email">, SignupStep> = {
      verification: "email",
      role: "verification",
      company: "role",
      complete: "company",
    };
    setStep(previousStep[step]);
  };

  const updateCode = (index: number, value: string) => {
    const digit = value.replace(/\D/g, "").slice(-1);
    setCode((current) => current.map((item, itemIndex) => itemIndex === index ? digit : item));
    if (digit && index < code.length - 1) {
      document.getElementById(`verification-code-${index + 1}`)?.focus();
    }
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

          {step === "email" && (
            <form className="signup-content signup-content--standard" onSubmit={submitEmail}>
              <Progress current="1 / 3 기업 이메일 인증" width="one-third" />
              <h1>기업 이메일을 인증해주세요</h1>
              <p className="signup-description">InvoiceX에서 사용할 기업의 업무용 이메일을 입력해주세요. 입력한 이메일로 6자리 인증 코드를 보내드립니다.</p>
              <label className="signup-field signup-field--email">
                <span>기업 이메일</span>
                <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@company.com" required />
                <small>기업에서 업무용으로 사용하는 이메일을 입력해주세요.</small>
              </label>
              <button className="signup-primary-button" type="submit">인증 코드 받기</button>
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
                      id={`verification-code-${index}`}
                      inputMode="numeric"
                      key={index}
                      maxLength={1}
                      onChange={(event) => updateCode(index, event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Backspace" && !value && index > 0) document.getElementById(`verification-code-${index - 1}`)?.focus();
                      }}
                      value={value}
                    />
                  ))}
                </div>
                <div className="signup-code-meta">
                  <span>인증 코드 유효시간 <strong>04:59</strong></span>
                  <button type="button" onClick={() => setCode(["", "", "", "", "", ""])}>코드를 받지 못하셨나요? <strong>재전송</strong></button>
                </div>
              </fieldset>
              <button className="signup-primary-button" type="submit">인증 완료</button>
              <button className="signup-change-email" type="button" onClick={() => setStep("email")}>다른 이메일 사용하기</button>
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
                <label className="signup-field"><span>기업명</span><input value={companyName} onChange={(event) => setCompanyName(event.target.value)} placeholder="예: 인보이스엑스 주식회사" required /></label>
                <label className="signup-field"><span>사업자등록번호</span><input placeholder="000-00-00000" required /></label>
                <label className="signup-field"><span>담당자명</span><input value={contactName} onChange={(event) => setContactName(event.target.value)} placeholder="예: 홍길동" required /></label>
                <label className="signup-field"><span>담당자 직책</span><input value={contactTitle} onChange={(event) => setContactTitle(event.target.value)} placeholder="예: 재무팀 매니저" required /></label>
                <label className="signup-field signup-field--full"><span>담당자 연락처</span><input placeholder="010-0000-0000" required /></label>
              </div>
              <div className="signup-verified-email"><span>인증된 이메일 · {email || "finance@company.com"}</span><strong>인증 완료</strong></div>
              <button className="signup-primary-button" type="submit">기업 등록 완료</button>
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
              <span className="signup-role-chip">기업 인증 완료 · 활성화</span>
              <button className="signup-primary-button" type="button" onClick={() => navigate(dashboardRoutes[role])}>InvoiceX 시작하기</button>
            </section>
          )}
        </section>
      </main>
    </div>
  );
}

function Progress({ current, width }: { current: string; width: "one-third" | "two-thirds" | "complete" }) {
  return (
    <div className="signup-progress">
      <div><strong>{current}</strong><span>기업 계정 설정</span></div>
      <i><b className={`signup-progress__fill signup-progress__fill--${width}`} /></i>
    </div>
  );
}
