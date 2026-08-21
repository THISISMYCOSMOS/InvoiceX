# InvoiceX 프론트엔드

InvoiceX 해커톤 MVP의 공급기업·구매기업·투자자 화면입니다. Privy 인증, Solana Devnet 지갑 연결, 실제 API와 브라우저 내 Mock 데모를 모두 지원합니다.

## 실행

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5173/login`으로 접속해 역할을 선택하거나, `http://localhost:5173/signup`에서 가입을 시작합니다.

## 환경 변수

`.env.example`을 복사해 `.env.local`을 만들고 필요에 따라 수정합니다.

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_USE_MOCK_API=false
VITE_PRIVY_APP_ID=cms678zqw007k0cjkq4jhxn9q
VITE_SOLANA_NETWORK=devnet
```

- `VITE_USE_MOCK_API=true`: 메모리 기반 해피 패스 데모 상태 머신을 사용합니다.
- `VITE_USE_MOCK_API=false`: `VITE_API_BASE_URL/api/v1`의 실제 백엔드 API adapter를 사용합니다. 실제 Gemini·Privy·Solana Devnet 테스트는 이 값이어야 합니다.
- 회원가입은 `http://localhost:5173/signup`으로 접속합니다. Privy에 등록된 로컬 Origin은 `localhost`이므로 `127.0.0.1`은 사용하지 않습니다.
- `VITE_PRIVY_APP_ID`는 공개 식별자입니다. Privy App Secret은 프론트엔드 환경 변수에 넣지 않습니다.

## 제공 라우트

- 공급기업: `/supplier`, `/supplier/invoices/new`, `/supplier/invoices/:invoiceId`, `/supplier/company-wallet`, `/supplier/funds-conversion`
- 구매기업: `/buyer`, `/buyer/verification`, `/buyer/payment`, `/buyer/invoices/:invoiceId`, `/buyer/profile`
- 투자자: `/investor`, `/investor/activities`, `/investor/activities/:invoiceId`, `/investor/investment-policy`, `/investor/vault`, `/investor/profile`, `/investor/funds-conversion`
- `/dev/demo` — 개발·발표 전용 상태 제어 화면

## 검증 명령

```bash
npm run lint
npm run typecheck
npm run test
npm run build
```

## 실제 API 연동

실제 API는 Privy Bearer 토큰을 사용하며 기본 URL `VITE_API_BASE_URL/api/v1` 아래에 제공됩니다. 전체 요청·응답 계약은 백엔드를 실행한 뒤 Swagger UI(`http://localhost:8000/api/docs`)에서 확인합니다.

주요 플로우는 다음 엔드포인트를 사용합니다.

```text
POST /api/v1/invoices
GET  /api/v1/invoices
GET  /api/v1/invoices/{invoiceId}
POST /api/v1/invoices/{invoiceId}/verification-request
GET  /api/v1/verifications
GET  /api/v1/verifications/{id}
POST /api/v1/verifications/{verificationId}/confirm
POST /api/v1/invoices/{invoiceId}/offer-response
GET  /api/v1/investor/dashboard
POST /api/v1/investor/mandates/prepare
POST /api/v1/investor/mandates
POST /api/v1/investor/vault/deposits/prepare
POST /api/v1/investor/vault/deposits/sponsor
GET  /api/v1/invoices/{invoiceId}/buyer-payment/prepare
POST /api/v1/invoices/{invoiceId}/buyer-payment/sponsor
POST /api/v1/invoices/{invoiceId}/buyer-payment/confirm
```

`POST /api/v1/invoices`와 문서 교체 API는 다음 네 개의 multipart 필드를 사용합니다.

- `INVOICE`
- `CONTRACT`
- `PURCHASE_ORDER`
- `DELIVERY_PROOF`

Gemini 분석, Risk 점수 계산, Mandate 정책 평가와 서비스 지갑을 통한 Treasury·Settlement 실행은 백엔드가 수행합니다. 프런트엔드는 사용자의 Privy 지갑 서명과 상태·거래 증적 표시를 담당합니다.
