# InvoiceX Document Agent mock invoice test set

이 디렉터리는 실제 인보이스 양식을 참고해 만든 목업 문서로 Document Agent의 문서 분류, 필드 추출, 문서 간 불일치 탐지를 평가하기 위한 테스트 자료입니다. 실제 거래 문서가 아니며 테스트 전용입니다.

## 디렉터리 구성

```text
docs/test/
├─ pass/
│  ├─ variant-1/
│  └─ variant-2/
└─ reject/
   ├─ variant-1/
   └─ variant-2/
```

각 variant는 5개 시나리오로 구성됩니다. 각 시나리오에는 Invoice, Contract, Purchase Order, Delivery Note PDF와 정답 데이터인 `expected.json`이 들어 있습니다.

| 구분 | 시나리오 | 의도 |
|---|---|---|
| pass | `00-normal` | 정상 문서 기준군 |
| pass | `01-within-terms` | 만기 조건 이내 |
| pass | `02-clean-jurisdiction` | 제재 관련 이상이 없는 거래당사자 |
| pass | `03-reconciled` | 문서 간 값이 조정되어 일치 |
| pass | `04-fx-documented` | 환율 관련 근거가 포함된 문서 |
| reject | `00-normal` | 반려 세트의 정상 대조군 |
| reject | `01-duplicate` | 기존 인보이스와의 중복 상황 |
| reject | `02-overdue` | 만기 초과 상황 |
| reject | `03-sanctions` | 제재 대상 상황 |
| reject | `04-mismatch` | 문서 간 금액, 수량, 결제조건, 납품완료 여부 불일치 |

`pass`와 `reject`는 최종 서비스 정책 기준의 시나리오 구분입니다. Document Agent의 `reviewRequired`와 동일한 의미가 아닙니다. 중복 여부는 Backend의 기존 인보이스 이력, 만기 초과는 현재 날짜 비교, 제재 여부는 외부 제재 데이터가 추가로 필요합니다.

## 2026-08-20 Gemini 평가 결과

사용 모델: `gemini-3.6-flash`

| 평가 항목 | 결과 |
|---|---:|
| 전체 논리 시나리오 | 20건 |
| 정상 처리 | 18건 (90%) |
| 호출 실패 | 2건 (10%) |
| 완료된 문서 검토 판단 | 18/18 정확 |
| 의미 기준 필드 정확도 | 97.6% |
| 엄격한 문자열 정확도 | 93.8% |
| 문서 유형 인식 | 72/72 (100%) |
| 문서 불일치 정밀도 | 100% |
| 문서 불일치 재현율 | 50% |

호출 실패 2건은 `reject/variant-1/00-normal`과 `reject/variant-2/00-normal`에서 발생한 `GeminiInvocationError`입니다. 판정 오답이 아니라 분석 응답을 완료하지 못한 운영 실패로 집계했습니다.

두 mismatch variant 모두 문서 검토가 필요하다는 방향은 맞게 판단했습니다. 기대한 불일치 8개 중 총금액과 수량 4개를 탐지했고, 결제조건과 납품완료 여부 4개는 누락했습니다. 오탐은 없었습니다.

이 결과는 Document Agent 단독 평가입니다. Backend hard gate와 최종 서비스 PASS, REVIEW, BLOCKED 판정은 포함하지 않습니다.

## 통화 변경 시 주의사항

USD 정상 시나리오를 USDC로 바꾸는 것은 Agent 및 Backend 지원 범위입니다. 변경할 때는 한 시나리오의 모든 PDF와 `expected.json`을 함께 수정해야 합니다. 일부 문서만 수정하면 통화 불일치가 발생하는 것이 정상입니다.

EUR 기반 `03-reconciled`, `04-fx-documented`, `04-mismatch` 시나리오를 USDC로 일괄 변경하면 FX 및 통화 관련 테스트 목적이 사라질 수 있으므로 유지합니다.
