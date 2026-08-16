# Golden Set — Document Agent 회귀 테스트 픽스처

해외 B2B · USDC 정산 전환 이후의 문서 세트다.
기존 `agent/fixtures/documents/`(국내·KRW)는 **건드리지 않았다.** 여기는 별도 경로다.

- 기준일 **2026-08-16**
- 회사명 · VAT · 지갑 주소 · 문서번호는 전부 가상
- 5 케이스 × 4 문서 = PDF 20개, 케이스마다 `expected.json` 1개
- PDF는 전부 1페이지 · 4KB 내외 · 텍스트 레이어 포함 (`pdftotext -layout`로 추출 가능)

## 실행

```bash
python agent/scripts/eval_gemini_documents.py --fixture-root work/agent/golden-set
python agent/scripts/eval_gemini_documents.py --fixture-root work/agent/golden-set --set 04-mismatch
```

`--fixture-root`가 이미 인자로 열려 있어서 **코드 수정 없이 그대로 돌아간다.**
기존 셋을 돌리려면 `--fixture-root agent/fixtures/documents`.

## 구조

```
work/agent/golden-set/
├── 00-normal/
│   ├── 00-normal-invoice.pdf
│   ├── 00-normal-contract.pdf
│   ├── 00-normal-purchase-order.pdf
│   ├── 00-normal-delivery-note.pdf
│   └── expected.json
├── 01-duplicate/
├── 02-overdue/
├── 03-sanctions/
└── 04-mismatch/
```

파일명 = `documentId` = `expected.json`의 `documents[].documentId`.

문서 타입은 공급기업 업로드 화면(`DocumentUploadCard`)의 슬롯 4개에 대응한다.
다만 납품 증빙은 프론트가 `DELIVERY_PROOF`, 에이전트가 `DELIVERY_EVIDENCE`로 이름이 다르다.
`expected.json`은 **에이전트 쪽 이름(`DELIVERY_EVIDENCE`)** 을 쓴다.

| 파일 접미사 | expectedDocumentType | 업로드 슬롯 |
|---|---|---|
| `-invoice` | `INVOICE` | 인보이스 |
| `-contract` | `CONTRACT` | 계약서 |
| `-purchase-order` | `PURCHASE_ORDER` | 구매주문서 |
| `-delivery-note` | `DELIVERY_EVIDENCE` | 납품 증빙 |

## 설계 제약 — 문서당 품목 1줄

Document Agent의 `itemName` / `quantity` / `unitPrice`는 **스칼라**다 (`models/document.py`).
품목이 여러 줄이면 정답값을 하나로 확정할 수 없으므로, 모든 문서는 **품목 1줄**로 구성했다.

`totalAmount = quantity × unitPrice`가 문서 안에서 항상 정확히 맞아떨어진다.
단가는 전부 정수라 `"8.90"` 대 `"8.9"` 같은 정규화 모호성이 없다.

긴 값(결제조건, 계약 품목)은 표 셀에서 줄바꿈되면 문자열 매칭이 깨지므로 **전체폭 라인**으로 뺐다.

## 케이스

| 셋 | 기대 결과 | mismatches | reviewRequired | 판정 주체 |
|---|---|---|---|---|
| `00-normal` | 통과 | 0 | `false` | — |
| `01-duplicate` | KO — 중복 | 0 | `false` | **DB (세트 간)** |
| `02-overdue` | KO — 만기 도과 | 0 | `false` | **룰 엔진** |
| `03-sanctions` | KO — 제재 | 0 | `false` | **제재·지갑 스크리닝** |
| `04-mismatch` | KO — 대사 실패 | 4 | `true` | **Document Agent** |

> 중요: **01~03은 Document Agent 단독으로는 잡히지 않는다.** 문서 4종이 서로 일치하므로
> `mismatches`는 비어 있고 `reviewRequired`는 `false`가 정답이다. 이 셋들이 검증하는 것은
> "에이전트가 멀쩡한 문서를 멀쩡하다고 판정하는가"이고, 반려는 그 뒤 단계의 몫이다.
> 에이전트가 여기서 mismatch를 만들어내면 오탐이다.

---

### 00-normal

Nordwind Components GmbH (DE) → Halcyon Robotics Ltd (UK) · **USD 96,000**

| | 값 |
|---|---|
| 인보이스 | IX-2026-0817 · 발행 2026-07-20 · 만기 2026-09-18 |
| 계약 | CTR-2026-0311 · Net 60 |
| 발주 | PO-2026-4471 · 발주일 2026-06-02 |
| 납품 | POD-2026-4471-A · 2026-07-14 · 완료 |
| 품목 | Harmonic drive gear unit HDU-120 · 150 pcs @ 640 |

잔존 33일, 잔존만기율 0.55. 계약 4조에 채권 양도 허용·양도통지 조항 명시. 무역신용보험 ACTIVE(Coface).

기준선 셋이다. 여기서 mismatch가 나오면 프롬프트나 모델 회귀를 의심해야 한다.

### 01-duplicate

**계약서·발주서·납품증빙이 `00-normal`과 동일**하고 인보이스 번호만 `IX-2026-0817-A`.

```
판매자 VAT  DE811234567    ← 동일
구매자 VAT  GB432198765    ← 동일
PO 번호     PO-2026-4471   ← 동일
통화/금액   USD 96000      ← 동일
발행일      2026-07-20     ← 동일
Invoice No. IX-2026-0817-A ← 다름
```

하나의 납품 건에 인보이스가 두 장 걸린, 이중금융의 전형적인 형태다.

- **파일 해시는 `00-normal`과 다르다.** 해시 단독으로는 안 걸린다
- 세트 내부 4개 문서는 서로 일치한다. **에이전트는 이걸 정상으로 봐야 맞다**
- 판정은 세트 간 비교 — 자체 DB 복합키(판매자 VAT + 구매자 VAT + 통화 + 금액 + 발행일)와 PO 번호 단위 검사
- 인보이스 각주의 "Reissued copy. Supersedes an earlier document"는 보조 신호

### 02-overdue

Meridian Textiles S.p.A. (IT) → Vantage Retail Group Inc. (US) · **USD 37,800**

발행 2026-04-02 / Net 90 / 만기 **2026-07-01** → 기준일 대비 **46일 도과**.

문서 대사는 전부 통과한다. 계약·발주·인보이스 Net 90 일치, 납품 완료, B/L 첨부, 분쟁 없음, 보험 ACTIVE.
다른 축이 전부 양호해도 만기 하나로 점수와 무관하게 반려되는지 보는 셋이다.

### 03-sanctions

Aurora Marine Supplies Pte Ltd (SG) → **Pars Offshore Engineering Co. (Tehran, Iran)** · **USD 59,200**

**문서 품질을 의도적으로 완벽하게** 만들었다. 4종 대사 통과, 납품 완료, 서명 완비, 계약 5조에 수출통제·제재 준수 조항까지 있다. 만기도 2026-09-19로 여유가 있다.

걸리는 건 두 가지뿐이고 **둘 다 문서 밖에 있다.**

- 구매기업 소재 Tehran, Iran / 배송지 Bandar Abbas
- 정산 지갑이 Tron TRC-20 → 지갑 스크리닝 대상

룰 엔진이 문서 완성도와 제재를 분리해서 판정하는지 확인하는 셋이다.

### 04-mismatch

Kestrel Packaging Solutions B.V. (NL) → Brightline Foods SAS (FR) · EUR

문서 4종이 서로 어긋난다. 대사 로직을 정면으로 검증한다.

| 필드 | 계약 | 발주 | 납품 | 인보이스 |
|---|---|---|---|---|
| paymentTerms | **Net 30** | — | — | **Net 45** |
| quantity | — | **11,000** | **11,000** | **12,000** |
| totalAmount | — | **22,000** | — | **24,000** |
| deliveryCompleted | — | — | **false** | **true** |
| purchaseOrderNumber | — | PO-BLF-33027 | PO-BLF-33027 | **없음** |
| contractNumber | CTR-2026-0120 | CTR-2026-0120 | — | **없음** |
| dueDate | — | — | — | **없음** |

기대 `expectedMismatches` 4건: `paymentTerms` · `quantity` · `totalAmount` · `deliveryCompleted`.
`expectedReviewRequired`는 `true`.

발주번호·계약번호·만기일은 **불일치가 아니라 누락**으로 선언되어야 한다. 인보이스에 아예 없기 때문이다.

계약서에 판정 근거가 명문화되어 있다.

- 2조 — "Net 30이 아닌 결제조건을 기재한 인보이스는 본 계약상 무효"
- 3조 — "모든 인보이스는 발주번호와 계약번호를 기재해야 하며, 누락 시 미지급 반송"
- 4조 — "부분 출하는 구매기업의 사전 서면 동의 필요"

납품 증빙에는 수령자 서명이 없고("Signature not obtained"), 운송서류도 없으며, 분쟁이 2026-06-12에 제기되어 미해결이다.

만기일을 역산하면 인보이스 기준(Net 45) 2026-07-26, 계약 기준(Net 30) 2026-07-11 — **어느 쪽이든 이미 도과**다.

인보이스는 EUR 표기인데 정산은 USDC로 요청되어 있고 환율 근거가 없다. 이건 문서 대사가 아니라 룰 엔진에서 볼 항목이다.

**검증 포인트:** 누락 필드를 환각으로 채우지 않는지. 역산 근거를 명시하는지. 금액·수량 불일치를 산술로 잡는지. 계약 조항과 인보이스 조건의 충돌을 인식하는지.

## expected.json 스키마

기존 `agent/fixtures/documents/*/expected.json`과 동일하다.

```jsonc
{
  "setId": "04-mismatch",
  "title": "...",
  "documents": [
    {
      "documentId": "04-mismatch-invoice",
      "pdf": "04-mismatch-invoice.pdf",
      "expectedDocumentType": "INVOICE",
      "expectedExtractedData": { /* 14개 필드 전부, 없으면 null */ },
      "expectedMissingFields": [ /* null인 필드와 정확히 같은 집합 */ ],
      "note": ""
    }
  ],
  "expectedMismatches": [
    { "field": "quantity",
      "values": [ { "documentId": "...", "value": "12000" } ],
      "description": "..." }
  ],
  "expectedReviewRequired": true,
  "notes": [],
  "perDocumentFields": ["issueDate"],
  "comparisonRules": []
}
```

불변 조건 두 가지를 자체 검증했다.

1. `expectedExtractedData`에서 `null`인 필드 집합 == `expectedMissingFields` (프롬프트가 요구하는 조건)
2. `null`이 아닌 모든 기대값이 해당 PDF 텍스트에 문자열로 실제 존재

금액·수량은 자릿수 구분 기호를 제거한 숫자 문자열, 날짜는 `YYYY-MM-DD`로 비교한다.
`issueDate`는 `perDocumentFields`라 문서 간 값이 달라도 불일치가 아니다.

## 재생성

생성 스크립트는 이 저장소 밖에 있다. 케이스 데이터는 스크립트 하단 `case(...)` 블록에 있고,
`--fixture-root`로 출력 경로를 받는다.

```bash
python gen_work_golden_set.py work/agent/golden-set
```

## 남은 확인 사항

- `agent/scripts/create_mock_documents.py`는 기존 `set-a-happy-path` / `set-b-amount-mismatch`를 생성한다. 이 골든세트와는 무관하며 서로 덮어쓰지 않는다.
- `agent/tests/test_document_agent.py`는 `set-a-happy-path/a-invoice.pdf`를 하드코딩한다. 기존 픽스처를 그대로 두었으므로 **테스트는 영향받지 않는다.**
- 통화 관련: 프론트 `DocumentAnalysis` 타입이 `amountKrw`로 고정되어 있어 해외 통화를 담지 못한다. 에이전트는 `currency` + `totalAmount`를 분리해 갖고 있다. 계약 불일치로 보이나 이 문서의 범위 밖이라 기록만 한다.
