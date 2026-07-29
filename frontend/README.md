# InvoiceX 프론트엔드

InvoiceX 해커톤 MVP를 위한 역할별 화면과 Mock 데모 시나리오입니다. 최종 디자인 시스템 이전 단계이므로 시맨틱 HTML과 최소 CSS만 사용합니다.

## 실행

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 Supplier 화면은 `http://localhost:5173/supplier`로 엽니다.

## 환경 변수

`.env.example`을 복사해 `.env`를 만들고 필요에 따라 수정합니다.

```env
VITE_API_BASE_URL=http://localhost:8080
VITE_USE_MOCK_API=true
VITE_SOLANA_NETWORK=devnet
```

- `VITE_USE_MOCK_API=true`: 메모리 기반 해피 패스 데모 상태 머신을 사용합니다.
- `VITE_USE_MOCK_API=false`: `VITE_API_BASE_URL/api/v1`의 실제 백엔드 API adapter를 사용합니다.

## 제공 라우트

- `/supplier`, `/supplier/invoices/new`, `/supplier/invoices/:invoiceId`
- `/buyer`, `/buyer/invoices/:invoiceId`
- `/investor`, `/investor/setup`, `/investor/activities/:invoiceId`
- `/dev/demo` — 개발·발표 전용 상태 제어 화면

## 검증 명령

```bash
npm run lint
npm run typecheck
npm run test
npm run build
```

## 실제 API 연동

실제 API adapter는 다음 계약을 사용합니다.

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
POST /api/v1/invoices/{invoiceId}/settlement/mock-payment
```

백엔드 구현이 아직 저장소에 병합되지 않아 `POST /invoices`의 multipart 필드명과 각 응답 DTO가 미확정입니다. 이 정보는 `src/api/adapters/httpAdapter.ts`의 mapper 안에만 격리되어 있으며, 다음 항목이 확정되면 해당 파일만 수정하면 됩니다.

1. Invoice 생성·목록·상세 응답 구조
2. Verification ID와 Confirm 요청·응답 구조
3. Offer 응답 요청 JSON 필드명
4. Investor dashboard 응답 구조
5. Mock 결제·Solana 거래·정산 응답 구조

Gemini 분석, Risk 점수 계산, AP2 검증, Gasless 트랜잭션, Solana 송금은 프런트엔드가 수행하지 않습니다.
