import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { SignupPage } from "./SignupPage";

const mocks = vi.hoisted(() => ({
  ensureEmbeddedSolanaWallet: vi.fn(),
  getAccessToken: vi.fn(),
  getAuthMe: vi.fn(),
  getOtpClock: vi.fn(),
  linkEmbeddedWallet: vi.fn(),
  logout: vi.fn(),
  onboardCompany: vi.fn(),
  sendCode: vi.fn(),
  verifyCode: vi.fn(),
}));

vi.mock("../auth/SignupAuthContext", () => ({
  useSignupAuth: () => ({
    authenticated: false,
    configured: true,
    ready: true,
    ensureEmbeddedSolanaWallet: mocks.ensureEmbeddedSolanaWallet,
    getAccessToken: mocks.getAccessToken,
    logout: mocks.logout,
    sendCode: mocks.sendCode,
    verifyCode: mocks.verifyCode,
  }),
}));

vi.mock("../api/onboarding.api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/onboarding.api")>();
  return {
    ...actual,
    getAuthMe: mocks.getAuthMe,
    getOtpClock: mocks.getOtpClock,
    linkEmbeddedWallet: mocks.linkEmbeddedWallet,
    onboardCompany: mocks.onboardCompany,
  };
});

beforeEach(() => {
  vi.clearAllMocks();
  window.localStorage.clear();
  window.sessionStorage.clear();
  mocks.getAccessToken.mockResolvedValue("privy-access-token");
  mocks.ensureEmbeddedSolanaWallet.mockResolvedValue({
    address: "SolanaAddress",
    created: true,
  });
  mocks.logout.mockResolvedValue(undefined);
  mocks.getAuthMe.mockResolvedValue({
    user: { email: "finance@company.com" },
    onboardingStatus: "NEEDS_COMPANY_PROFILE",
    nextPath: "/signup",
  });
  mocks.getOtpClock.mockResolvedValue({
    serverTimeMs: Date.now(),
    expiresInSeconds: 300,
  });
  mocks.onboardCompany.mockResolvedValue({
    embeddedWallet: {
      id: "wal_1",
      privyUserId: "did:privy:user-1",
      address: "SolanaAddress",
    },
    onboardingStatus: "COMPLETED",
    nextPath: "/supplier",
  });
  mocks.linkEmbeddedWallet.mockResolvedValue({
    embeddedWallet: { address: "SolanaAddress" },
    onboardingStatus: "COMPLETED",
    nextPath: "/investor",
  });
});

test("prefills the company email when wallet authentication redirects to signup", () => {
  render(
    <MemoryRouter initialEntries={[{ pathname: "/signup", state: { email: "investor@company.com" } }]}>
      <SignupPage />
    </MemoryRouter>,
  );

  expect(screen.getByLabelText("기업 이메일")).toHaveValue("investor@company.com");
});

test("completes signup only after the onboarding API creates the user-owned wallet", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><SignupPage /></MemoryRouter>);

  await user.type(screen.getByLabelText("기업 이메일"), "finance@company.com");
  await user.click(screen.getByRole("button", { name: "인증 코드 받기" }));
  expect(mocks.sendCode).toHaveBeenCalledWith("finance@company.com");

  for (const [index, digit] of [..."123456"].entries()) {
    await user.type(screen.getByLabelText(`${index + 1}번째 인증 코드`), digit);
  }
  await user.click(screen.getByRole("button", { name: "인증 완료" }));
  expect(mocks.verifyCode).toHaveBeenCalledWith("123456");
  expect(mocks.getAuthMe).toHaveBeenCalledWith("privy-access-token");

  await user.click(screen.getByRole("button", { name: "다음" }));
  await user.type(screen.getByLabelText("기업명"), "인보이스엑스 주식회사");
  expect(screen.getByLabelText("국가 코드")).toHaveTextContent("KR");
  await user.type(screen.getByLabelText("기업 등록번호"), "1234567890");
  expect(screen.getByLabelText("기업 등록번호")).toHaveValue("123-45-67890");
  await user.type(screen.getByLabelText("담당자명"), "홍길동");
  await user.type(screen.getByLabelText("담당자 직책"), "재무팀 매니저");
  await user.type(screen.getByLabelText("담당자 연락처"), "01012345678");
  expect(screen.getByLabelText("담당자 연락처")).toHaveValue("010-1234-5678");
  await user.type(screen.getByLabelText("비밀번호"), "member-password-123");
  await user.type(screen.getByLabelText("비밀번호 확인"), "member-password-123");
  await user.click(screen.getByRole("button", { name: "기업 등록 완료" }));

  expect(mocks.onboardCompany).toHaveBeenCalledWith("privy-access-token", {
    company: {
      name: "인보이스엑스 주식회사",
      type: "SUPPLIER",
      countryCode: "KR",
      registrationNumber: "123-45-67890",
    },
    representative: {
      name: "홍길동",
      title: "재무팀 매니저",
      phone: "010-1234-5678",
    },
    password: "member-password-123",
    embeddedWalletAddress: "SolanaAddress",
  });
  expect(await screen.findByRole("heading", { name: "기업 계정 생성이 완료되었습니다!" }))
    .toBeInTheDocument();
});

test("allows buyers to register with a US EIN", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><SignupPage /></MemoryRouter>);

  await user.type(screen.getByLabelText("기업 이메일"), "buyer@halcyon.com");
  await user.click(screen.getByRole("button", { name: "인증 코드 받기" }));
  for (const [index, digit] of [..."123456"].entries()) {
    await user.type(screen.getByLabelText(`${index + 1}번째 인증 코드`), digit);
  }
  await user.click(screen.getByRole("button", { name: "인증 완료" }));
  await user.click(screen.getByRole("radio", { name: /구매기업/ }));
  await user.click(screen.getByRole("button", { name: "다음" }));

  expect(screen.getByLabelText("국가 코드")).toHaveTextContent("US");
  expect(screen.getByLabelText("기업 등록번호")).toHaveAttribute("placeholder", "예: 12-3456789");
  await user.type(screen.getByLabelText("기업명"), "Halcyon Robotics Ltd");
  await user.type(screen.getByLabelText("기업 등록번호"), "123456789");
  expect(screen.getByLabelText("기업 등록번호")).toHaveValue("12-3456789");
  await user.type(screen.getByLabelText("담당자명"), "Alex Kim");
  await user.type(screen.getByLabelText("담당자 직책"), "Finance Lead");
  await user.type(screen.getByLabelText("담당자 연락처"), "01012345678");
  await user.type(screen.getByLabelText("비밀번호"), "member-password-123");
  await user.type(screen.getByLabelText("비밀번호 확인"), "member-password-123");
  await user.click(screen.getByRole("button", { name: "기업 등록 완료" }));

  expect(mocks.onboardCompany).toHaveBeenCalledWith("privy-access-token", expect.objectContaining({
    company: {
      name: "Halcyon Robotics Ltd",
      type: "BUYER",
      countryCode: "US",
      registrationNumber: "12-3456789",
    },
  }));
});

test("signs an existing Privy member into the stored company route", async () => {
  mocks.getAuthMe.mockResolvedValue({
    user: { email: "finance@company.com" },
    company: { name: "Supplier One", type: "SUPPLIER" },
    embeddedWallet: { address: "SolanaAddress" },
    onboardingStatus: "COMPLETED",
    nextPath: "/supplier",
  });
  window.localStorage.setItem("invoicex-demo-session", "stale-demo-session");
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/signup"]}>
      <Routes>
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/supplier" element={<h1>Supplier member dashboard</h1>} />
      </Routes>
    </MemoryRouter>,
  );

  await user.type(screen.getByLabelText("기업 이메일"), "finance@company.com");
  await user.click(screen.getByRole("button", { name: "인증 코드 받기" }));
  screen.getByLabelText("1번째 인증 코드").focus();
  await user.paste("123456");
  await user.click(screen.getByRole("button", { name: "인증 완료" }));

  expect(await screen.findByRole("heading", { name: "Supplier member dashboard" }))
    .toBeInTheDocument();
  expect(window.localStorage.getItem("invoicex-demo-session")).toBeNull();
});

test("repairs a completed account whose embedded wallet record is missing", async () => {
  mocks.getAuthMe.mockResolvedValue({
    user: { email: "investor@company.com" },
    company: { name: "Investor One", type: "INVESTOR" },
    embeddedWallet: null,
    onboardingStatus: "COMPLETED",
    nextPath: "/investor",
  });
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/signup"]}>
      <Routes>
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/investor" element={<h1>Investor dashboard</h1>} />
      </Routes>
    </MemoryRouter>,
  );

  await user.type(screen.getByLabelText("기업 이메일"), "investor@company.com");
  await user.click(screen.getByRole("button", { name: "인증 코드 받기" }));
  screen.getByLabelText("1번째 인증 코드").focus();
  await user.paste("123456");
  await user.click(screen.getByRole("button", { name: "인증 완료" }));

  expect(mocks.ensureEmbeddedSolanaWallet).toHaveBeenCalledTimes(1);
  expect(mocks.linkEmbeddedWallet).toHaveBeenCalledWith(
    "privy-access-token",
    "SolanaAddress",
  );
  expect(await screen.findByRole("heading", { name: "Investor dashboard" }))
    .toBeInTheDocument();
});

test("does not show completion when wallet provisioning is incomplete", async () => {
  mocks.onboardCompany.mockResolvedValue({
    embeddedWallet: null,
    onboardingStatus: "PROVISIONING_EMBEDDED_WALLET",
    nextPath: "/signup",
  });
  const user = userEvent.setup();
  render(<MemoryRouter><SignupPage /></MemoryRouter>);

  await user.type(screen.getByLabelText("기업 이메일"), "finance@company.com");
  await user.click(screen.getByRole("button", { name: "인증 코드 받기" }));
  for (const [index, digit] of [..."123456"].entries()) {
    await user.type(screen.getByLabelText(`${index + 1}번째 인증 코드`), digit);
  }
  await user.click(screen.getByRole("button", { name: "인증 완료" }));
  await user.click(screen.getByRole("button", { name: "다음" }));
  await user.type(screen.getByLabelText("기업명"), "인보이스엑스");
  await user.type(screen.getByLabelText("기업 등록번호"), "123-45-67890");
  await user.type(screen.getByLabelText("담당자명"), "홍길동");
  await user.type(screen.getByLabelText("담당자 직책"), "매니저");
  await user.type(screen.getByLabelText("담당자 연락처"), "010-1234-5678");
  await user.type(screen.getByLabelText("비밀번호"), "member-password-123");
  await user.type(screen.getByLabelText("비밀번호 확인"), "member-password-123");
  await user.click(screen.getByRole("button", { name: "기업 등록 완료" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("사용자 지갑 생성이 완료되지 않았습니다.");
  expect(screen.queryByRole("heading", { name: "기업 계정 생성이 완료되었습니다!" }))
    .not.toBeInTheDocument();
});

test("distributes a pasted verification code across all six inputs", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><SignupPage /></MemoryRouter>);

  await user.type(screen.getByLabelText("기업 이메일"), "finance@company.com");
  await user.click(screen.getByRole("button", { name: "인증 코드 받기" }));

  const firstInput = screen.getByLabelText("1번째 인증 코드");
  firstInput.focus();
  await user.paste("123456");

  for (const [index, digit] of [..."123456"].entries()) {
    expect(screen.getByLabelText(`${index + 1}번째 인증 코드`)).toHaveValue(digit);
  }
  expect(screen.getByLabelText("6번째 인증 코드")).toHaveFocus();
});

test("shows an actionable message and clears an invalid verification code", async () => {
  mocks.verifyCode.mockRejectedValueOnce(new Error("Invalid email and code combination"));
  const user = userEvent.setup();
  render(<MemoryRouter><SignupPage /></MemoryRouter>);

  await user.type(screen.getByLabelText("기업 이메일"), "finance@company.com");
  await user.click(screen.getByRole("button", { name: "인증 코드 받기" }));
  const firstInput = screen.getByLabelText("1번째 인증 코드");
  firstInput.focus();
  await user.paste("123456");
  await user.click(screen.getByRole("button", { name: "인증 완료" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "인증 코드가 일치하지 않습니다. 가장 최근에 받은 코드를 입력하거나 재전송해 주세요.",
  );
  expect(firstInput).toHaveValue("");
  expect(firstInput).toHaveFocus();
});

test("retries a transient Privy token synchronization failure after OTP succeeds", async () => {
  const transientTokenError = Object.assign(
    new Error("Privy access token이 유효하지 않거나 만료되었습니다."),
    { code: "PRIVY_TOKEN_INVALID", status: 401 },
  );
  mocks.getAccessToken
    .mockResolvedValueOnce(null)
    .mockResolvedValue("privy-access-token");
  mocks.getAuthMe
    .mockRejectedValueOnce(transientTokenError)
    .mockResolvedValueOnce({
      user: { email: "finance@company.com" },
      onboardingStatus: "NEEDS_COMPANY_PROFILE",
      nextPath: "/signup",
    });
  const user = userEvent.setup();
  render(<MemoryRouter><SignupPage /></MemoryRouter>);

  await user.type(screen.getByLabelText("기업 이메일"), "finance@company.com");
  await user.click(screen.getByRole("button", { name: "인증 코드 받기" }));
  screen.getByLabelText("1번째 인증 코드").focus();
  await user.paste("123456");
  await user.click(screen.getByRole("button", { name: "인증 완료" }));

  expect(await screen.findByRole("radiogroup", { name: "기업 유형" }, { timeout: 4_000 }))
    .toBeInTheDocument();
  expect(mocks.verifyCode).toHaveBeenCalledTimes(1);
  expect(mocks.getAccessToken).toHaveBeenCalledTimes(3);
  expect(mocks.getAuthMe).toHaveBeenCalledTimes(2);
});

test("counts down from the server clock and disables verification at expiration", async () => {
  mocks.getOtpClock.mockResolvedValueOnce({
    serverTimeMs: Date.now(),
    expiresInSeconds: 1,
  });
  const user = userEvent.setup();
  render(<MemoryRouter><SignupPage /></MemoryRouter>);

  await user.type(screen.getByLabelText("기업 이메일"), "finance@company.com");
  await user.click(screen.getByRole("button", { name: "인증 코드 받기" }));

  expect(mocks.getOtpClock).toHaveBeenCalledTimes(1);
  await waitFor(
    () => expect(screen.getByText("00:00")).toBeInTheDocument(),
    { timeout: 2_000 },
  );
  expect(screen.getByRole("button", { name: "인증 완료" })).toBeDisabled();
});

test("syncs the OTP clock before sending both initial and replacement codes", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><SignupPage /></MemoryRouter>);

  await user.type(screen.getByLabelText("기업 이메일"), "finance@company.com");
  await user.click(screen.getByRole("button", { name: "인증 코드 받기" }));
  await user.click(screen.getByRole("button", { name: /재전송/ }));

  expect(mocks.getOtpClock).toHaveBeenCalledTimes(2);
  expect(mocks.sendCode).toHaveBeenCalledTimes(2);
  expect(mocks.getOtpClock.mock.invocationCallOrder[0])
    .toBeLessThan(mocks.sendCode.mock.invocationCallOrder[0]);
  expect(mocks.getOtpClock.mock.invocationCallOrder[1])
    .toBeLessThan(mocks.sendCode.mock.invocationCallOrder[1]);
});

test("keeps the current OTP valid when clock sync fails before resend", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><SignupPage /></MemoryRouter>);

  await user.type(screen.getByLabelText("기업 이메일"), "finance@company.com");
  await user.click(screen.getByRole("button", { name: "인증 코드 받기" }));
  mocks.getOtpClock.mockRejectedValueOnce(new Error("clock unavailable"));
  await user.click(screen.getByRole("button", { name: /재전송/ }));

  expect(await screen.findByRole("alert")).toHaveTextContent("clock unavailable");
  expect(mocks.sendCode).toHaveBeenCalledTimes(1);
});

test("restores a failed signup and retries its stored company wallet", async () => {
  mocks.getAuthMe.mockResolvedValue({
    user: {
      email: "finance@company.com",
      name: "홍길동",
      title: "재무팀 매니저",
      phone: "010-1234-5678",
    },
    company: {
      name: "인보이스엑스 주식회사",
      type: "BUYER",
      countryCode: "US",
      registrationNumber: "12-3456789",
    },
    embeddedWallet: null,
    onboardingStatus: "PROVISIONING_EMBEDDED_WALLET",
    nextPath: "/signup",
  });
  const user = userEvent.setup();
  render(<MemoryRouter><SignupPage /></MemoryRouter>);

  await user.type(screen.getByLabelText("기업 이메일"), "finance@company.com");
  await user.click(screen.getByRole("button", { name: "인증 코드 받기" }));
  screen.getByLabelText("1번째 인증 코드").focus();
  await user.paste("123456");
  await user.click(screen.getByRole("button", { name: "인증 완료" }));

  expect(await screen.findByRole("heading", { name: "기업 가입을 이어서 완료해주세요." }))
    .toBeInTheDocument();
  expect(screen.getByLabelText("기업명")).toHaveValue("인보이스엑스 주식회사");
  expect(screen.getByLabelText("기업명")).toHaveAttribute("readonly");
  expect(screen.getByLabelText("국가 코드")).toHaveTextContent("US");
  expect(screen.getByLabelText("기업 등록번호")).toHaveValue("12-3456789");
  expect(screen.queryByRole("radiogroup", { name: "기업 유형" })).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "지갑 생성 다시 시도" }));

  expect(mocks.onboardCompany).toHaveBeenCalledWith("privy-access-token", {
    company: {
      name: "인보이스엑스 주식회사",
      type: "BUYER",
      countryCode: "US",
      registrationNumber: "12-3456789",
    },
    representative: {
      name: "홍길동",
      title: "재무팀 매니저",
      phone: "010-1234-5678",
    },
    embeddedWalletAddress: "SolanaAddress",
  });
});

test("logs out of Privy before changing to another email", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><SignupPage /></MemoryRouter>);

  await user.type(screen.getByLabelText("기업 이메일"), "finance@company.com");
  await user.click(screen.getByRole("button", { name: "인증 코드 받기" }));
  await user.click(screen.getByRole("button", { name: "다른 이메일 사용하기" }));

  expect(mocks.logout).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("heading", { name: "기업 이메일을 인증해주세요" })).toBeInTheDocument();
});
