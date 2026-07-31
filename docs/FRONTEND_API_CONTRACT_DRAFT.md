# InvoiceX 프런트엔드 API 계약 초안

> 대상: 백엔드 구현 담당자
>
> 상태: **초안 — 현재 `feat-frontend` 프런트엔드가 사용하는 구조를 기준으로 작성**
>
> 목적: 백엔드 초기 구현이 이 문서를 기준으로 API와 DTO를 고정할 수 있도록 한다.

## 1. 범위와 원칙

- Base URL: `{VITE_API_BASE_URL}/api/v1`
- 인증·회원가입은 MVP 범위 밖이다. Demo 계정만 사용한다.
- Gemini 문서 분석, Risk 점수·조건 산정, AP2 검증, Solana 송금은 **백엔드 책임**이다. 프런트는 결과와 상태만 표시한다.
- 금액 계산과 Invoice 상태 전이는 서버가 결정한다. 프런트의 Mock 데이터는 화면·데모용이며 서버의 비즈니스 로직을 대체하지 않는다.
- 모든 성공 응답은 `application/json`을 반환한다.
- 실패 응답 본문은 현재 프런트가 그대로 오류 문구로 표시하므로, 우선 사람이 읽을 수 있는 텍스트 또는 `message`가 명확한 JSON을 반환한다.
- `GET /invoices` 및 `GET /verifications` 목록 응답은 반드시 `{ "items": [...] }` 형태를 사용한다.

## 2. 공통 enum

### InvoiceStatus

```ts
type InvoiceStatus =
  | "DRAFT"
  | "DOCUMENT_UPLOADING"
  | "DOCUMENT_ANALYZING"
  | "DOCUMENT_REVIEW_REQUIRED"
  | "BUYER_REVIEW"
  | "BUYER_VERIFIED"
  | "RISK_ASSESSING"
  | "OFFER_READY"
  | "FUNDING"
  | "FUNDED"
  | "REPAYMENT_PENDING"
  | "SETTLING"
  | "SETTLED"
  | "REVISION_REQUESTED"
  | "DISPUTED"
  | "BLOCKED"
  | "ERROR";
```

### DocumentType / 파일 상태

```ts
type DocumentType =
  | "INVOICE"
  | "CONTRACT"
  | "PURCHASE_ORDER"
  | "DELIVERY_PROOF";

type UploadStatus = "IDLE" | "UPLOADING" | "COMPLETED" | "FAILED";
```

### 기타 enum

```ts
type ExtractedFieldStatus = "MATCHED" | "MISMATCH" | "MISSING" | "REVIEW_REQUIRED";
type AnalysisStatus = "PENDING" | "ANALYZING" | "COMPLETED" | "FAILED";
type RiskEligibility = "ELIGIBLE" | "REVIEW_REQUIRED" | "BLOCKED";
type TransactionStatus = "PENDING" | "CONFIRMED" | "FAILED";
type VerificationStatus = "PENDING" | "CONFIRMED" | "REVISION_REQUESTED" | "DISPUTED";
```

## 3. 공통 응답 DTO

### Invoice

아래 필드는 Invoice 목록·상세·상태 변경 응답에 사용한다. 목록에서는 문서·분석·Risk Passport·거래·Trace를 생략할 수 있으나, 상세 API에서는 제공한다.

```json
{
  "id": "INV-2026-001",
  "supplier": {
    "id": "SUPPLIER_ALPHA",
    "name": "Alpha Components",
    "walletAddress": "DEMO_SUPPLIER_WALLET"
  },
  "buyer": {
    "id": "BUYER_PRIME",
    "name": "Prime Mobility"
  },
  "investor": {
    "id": "INVESTOR_NOVA",
    "name": "Nova Capital",
    "vaultAddress": "DEMO_AGENT_VAULT"
  },
  "invoiceAmountKrw": 20000000,
  "issueDate": "2026-07-29",
  "dueDate": "2026-10-30",
  "deliveryDate": "2026-07-24",
  "contractNumber": "PM-SUPPLY-2026-04",
  "purchaseOrderNumber": "PO-89341",
  "status": "DOCUMENT_REVIEW_REQUIRED",
  "verificationId": "VER-2026-001",
  "documents": [],
  "analysis": null,
  "riskPassport": null,
  "fundingTransaction": null,
  "settlementTransaction": null,
  "settlement": null,
  "agentTraces": []
}
```

`id`, `status`, `supplier`, `buyer`, `investor`, 금액·일자·계약/PO 번호, `documents`, `agentTraces`는 프런트 화면에서 사용하는 필드이므로 상세 API에서는 누락하지 않는다. 값이 아직 없으면 해당 optional 객체는 `null`, 배열은 `[]`로 반환한다.

### InvoiceDocument

```json
{
  "id": "DOC-001",
  "invoiceId": "INV-2026-001",
  "type": "INVOICE",
  "fileName": "01_Invoice_INV-2026-001.pdf",
  "mimeType": "application/pdf",
  "fileSize": 1024,
  "storageUrl": "https://signed-or-public-preview-url",
  "uploadStatus": "COMPLETED"
}
```

`storageUrl`은 프런트의 PDF 미리보기용이다. 권한 모델이 도입되기 전 Demo 단계에서는 제한된 signed URL 또는 공개 Demo URL을 사용한다.

### DocumentAnalysis

```json
{
  "invoiceId": "INV-2026-001",
  "status": "COMPLETED",
  "invoiceNumber": { "value": "INV-2026-001", "status": "MATCHED" },
  "supplierName": { "value": "Alpha Components", "status": "MATCHED" },
  "buyerName": { "value": "Prime Mobility", "status": "MATCHED" },
  "amountKrw": { "value": 20000000, "status": "MATCHED" },
  "dueDate": { "value": "2026-10-30", "status": "MATCHED" },
  "contractNumber": { "value": "PM-SUPPLY-2026-04", "status": "MATCHED" },
  "purchaseOrderNumber": { "value": "PO-89341", "status": "MATCHED" },
  "deliveryCompleted": { "value": true, "status": "MATCHED" },
  "modelName": "gemini-...",
  "promptVersion": "v1",
  "analyzedAt": "2026-07-30T00:00:00.000Z"
}
```

각 추출 필드는 필요하면 다음 evidence를 포함한다.

```json
{
  "evidence": {
    "documentType": "INVOICE",
    "page": 1,
    "text": "INV-2026-001"
  }
}
```

### RiskPassport

```json
{
  "invoiceId": "INV-2026-001",
  "eligibility": "ELIGIBLE",
  "riskScore": 86,
  "scoreDirection": "HIGHER_IS_SAFER",
  "positiveFactors": [
    { "title": "구매기업 검증 완료", "description": "거래, 금액, 납품 완료가 확인되었습니다." }
  ],
  "riskFactors": [
    { "severity": "LOW", "title": "단일 Demo 거래", "description": "Demo 시나리오입니다." }
  ],
  "suggestedAdvanceRateBps": 9400,
  "suggestedAdvanceAmountUsdc": 18800,
  "modelName": "gemini-...",
  "policyVersion": "v1",
  "generatedAt": "2026-07-30T00:00:00.000Z"
}
```

Risk Score, 적격성, 선지급 조건은 서버의 결정적 코드가 계산한다. Gemini는 설명문 생성에만 사용하며 수치 값을 변경하지 않는다.

### BlockchainTransaction / Settlement / AgentTrace

```json
{
  "signature": "SolanaTransactionSignature",
  "network": "SOLANA_DEVNET",
  "status": "CONFIRMED",
  "amountUsdc": 18800,
  "fromAddress": "DEMO_AGENT_VAULT",
  "toAddress": "DEMO_SUPPLIER_WALLET",
  "explorerUrl": "https://explorer.solana.com/tx/...?...",
  "createdAt": "2026-07-30T00:00:00.000Z"
}
```

```json
{
  "invoiceFaceValueUsdc": 20000,
  "investorSettlementUsdc": 19800,
  "platformFeeUsdc": 200,
  "supplierResidualUsdc": 0
}
```

```json
{
  "id": "TRACE-RISK-TREASURY",
  "invoiceId": "INV-2026-001",
  "sourceAgent": "RISK_AGENT",
  "targetAgent": "TREASURY_AGENT",
  "status": "COMPLETED",
  "summary": "Risk Passport 전달 완료",
  "createdAt": "2026-07-30T00:00:00.000Z",
  "completedAt": "2026-07-30T00:00:01.000Z"
}
```

## 4. Endpoint 계약

### 4.1 문서 등록 및 분석 시작

```text
POST /api/v1/invoices
Content-Type: multipart/form-data
```

프런트가 현재 전송하는 form-data part 이름은 아래와 같다.

| Part 이름 | 필수 | 파일 |
|---|---:|---|
| `INVOICE` | 예 | Invoice PDF/JPG/JPEG/PNG |
| `CONTRACT` | 예 | 공급 계약서 |
| `PURCHASE_ORDER` | 예 | PO |
| `DELIVERY_PROOF` | 예 | 납품·용역 완료 증빙 |

파일은 문서별 1개이며 PDF/JPG/JPEG/PNG, 파일당 최대 20MB다.

성공 응답:

```json
{ "invoice": { "id": "INV-2026-001", "status": "DOCUMENT_ANALYZING" } }
```

백엔드가 동기적으로 분석을 끝낼 경우 `DOCUMENT_REVIEW_REQUIRED`를 반환해도 된다. 비동기 처리라면 생성 직후 `DOCUMENT_ANALYZING`을 반환하고, 아래 상세 API polling 결과에서 `DOCUMENT_REVIEW_REQUIRED`와 `analysis`를 반환한다.

### 4.2 Supplier Invoice 목록

```text
GET /api/v1/invoices
```

성공 응답:

```json
{ "items": [/* Invoice 배열 */] }
```

### 4.3 Invoice 통합 상세

```text
GET /api/v1/invoices/{invoiceId}
```

성공 응답:

```json
{ "invoice": /* Invoice 객체 */ }
```

문서 분석, Buyer 검증, Risk Passport, Agent Trace, 펀딩 거래, 정산 거래·결과는 이 단일 상세 응답으로 통합 제공한다.

### 4.4 Buyer 검증 요청 생성

```text
POST /api/v1/invoices/{invoiceId}/verification-request
```

요청 body 없음.

성공 응답:

```json
{
  "invoice": {
    "id": "INV-2026-001",
    "status": "BUYER_REVIEW",
    "verificationId": "VER-2026-001"
  }
}
```

### 4.5 Buyer 검증 목록 및 상세

```text
GET /api/v1/verifications
GET /api/v1/verifications/{verificationId}
```

목록 응답:

```json
{
  "items": [
    { "id": "VER-2026-001", "invoiceId": "INV-2026-001", "status": "PENDING" }
  ]
}
```

상세 응답:

```json
{
  "verification": {
    "id": "VER-2026-001",
    "invoiceId": "INV-2026-001",
    "status": "PENDING"
  }
}
```

상세 검증 화면을 고도화할 때는 `invoice` 또는 `documents`, `analysis`를 같은 응답에 확장할 수 있다. 현재 프런트는 Invoice 상세 API도 함께 조회한다.

### 4.6 Buyer Confirm

```text
POST /api/v1/verifications/{verificationId}/confirm
```

요청 body 없음.

백엔드 처리:

1. Buyer 검증을 확정한다.
2. Risk Passport 및 조기정산 조건을 결정적으로 생성한다.
3. Invoice를 `OFFER_READY`로 전이한다.

성공 응답:

```json
{ "invoice": /* riskPassport를 포함한 OFFER_READY Invoice */ }
```

### 4.7 Supplier 조건 응답

```text
POST /api/v1/invoices/{invoiceId}/offer-response
Content-Type: application/json
```

요청 body:

```json
{ "response": "ACCEPT" }
```

`response`는 `ACCEPT` 또는 `DECLINE`이다.

성공 응답:

```json
{ "invoice": { "id": "INV-2026-001", "status": "FUNDING" } }
```

`ACCEPT` 후 Treasury Agent가 투자 정책과 AP2 Mandate를 검증하고 송금을 처리한다. 실제 송금이 완료되면 상세 API는 `FUNDED`와 `fundingTransaction`을 반환해야 한다. 프런트는 별도 실제 fund endpoint를 호출하지 않고 상세 상태를 조회한다.

### 4.8 Investor Dashboard

```text
GET /api/v1/investor/dashboard
```

성공 응답은 wrapper 없이 아래 객체를 반환한다.

```json
{
  "investorName": "Nova Capital",
  "automatedInvestmentActive": true,
  "mandateStatus": "ACTIVE",
  "availableVaultUsdc": 50000,
  "outstandingPrincipalUsdc": 18800,
  "recentAgentTraces": []
}
```

### 4.9 KRW Mock 입금 및 정산

```text
POST /api/v1/invoices/{invoiceId}/settlement/mock-payment
```

요청 body 없음.

이 endpoint는 다음 Demo 흐름을 서버에서 처리한다.

```text
KRW_PAYMENT_CONFIRMED sandbox event
→ Settlement Partner Devnet USDC 입금
→ Settlement Agent 분배
→ SETTLED
```

성공 응답:

```json
{
  "invoice": {
    "id": "INV-2026-001",
    "status": "SETTLED",
    "settlementTransaction": {},
    "settlement": {
      "invoiceFaceValueUsdc": 20000,
      "investorSettlementUsdc": 19800,
      "platformFeeUsdc": 200,
      "supplierResidualUsdc": 0
    }
  }
}
```

현재 실제 API 명세에는 별도 `POST /settle`이 없다. 따라서 실제 모드에서는 이 endpoint가 정산 완료까지 처리해야 한다. 개발자 화면의 별도 `Settlement 실행`은 Mock 시나리오 단계용이며, 실제 백엔드에 별도 정산 endpoint가 추가되기 전에는 사용하지 않는다.

## 5. 상태 흐름

```text
DRAFT
→ DOCUMENT_ANALYZING
→ DOCUMENT_REVIEW_REQUIRED
→ BUYER_REVIEW
→ OFFER_READY
→ FUNDING
→ FUNDED
→ REPAYMENT_PENDING (선택적 표시 상태)
→ SETTLING
→ SETTLED
```

보완 요청은 `REVISION_REQUESTED`, 이의 제기는 `DISPUTED`, 정책 또는 검증 실패는 `BLOCKED`, 처리 실패는 `ERROR`로 전이한다. MVP에서는 보완·이의의 전체 후속 워크플로를 구현하지 않는다.

## 6. 백엔드 구현 체크리스트

- [ ] 위 enum 값을 그대로 사용한다.
- [ ] 목록 endpoint는 반드시 `{ items: [...] }`로 반환한다.
- [ ] Invoice 상세와 상태 변경 응답은 `{ invoice: {...} }`로 반환한다.
- [ ] Verification 상세는 `{ verification: {...} }`로 반환한다.
- [ ] `POST /invoices` multipart part 이름을 위 4개 enum으로 수용한다.
- [ ] Confirm 처리에서 서버가 Risk Passport와 Offer를 생성한다.
- [ ] Offer 수락 이후 펀딩 결과와 Solana signature를 Invoice 상세에 저장한다.
- [ ] Mock payment 처리에서 sandbox 여부를 로그와 응답 데이터에 명확히 남긴다.
- [ ] 정산 완료 후 investor 19,800 USDC, platform fee 200 USDC, supplier residual 0 USDC를 반환한다.
- [ ] 펀딩·정산 요청은 invoice ID 기준으로 중복 실행되지 않도록 서버에서 idempotent하게 처리한다.

## 7. 프런트 전환 방법

백엔드가 위 계약을 구현한 뒤 프런트 환경변수를 아래처럼 변경한다.

```env
VITE_API_BASE_URL=https://<backend-host>
VITE_USE_MOCK_API=false
VITE_SOLANA_NETWORK=devnet
```

현재 front adapter 위치는 `frontend/src/api/adapters/httpAdapter.ts`다. DTO가 이 초안대로 구현되면 추가 화면 변경 없이 API 모드로 전환할 수 있다.
