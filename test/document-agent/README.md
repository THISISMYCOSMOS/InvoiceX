# Document Agent evaluation artifacts

이 폴더는 2026-08-12~13에 수행한 Document Agent 시험을 세 그룹으로 보존합니다. API를 다시 호출하지 않고 당시 저장된 fixture와 원시 결과를 기준으로 집계했습니다.

- `same-format-v1/`: 기존 고정 양식을 유지하고 값·표기·불일치 조건을 바꾼 시험
- `different-format-v1/`: 회사별 신규 레이아웃 8종의 블라인드 시험
- `real-public-v1/`: 공개 배포 양식 8종에 알려진 합성 값을 채운 시험
- `reports/`: 세 시험을 합친 성능평가 DOCX, PDF, 기계 판독용 JSON

정확도 분모에는 구조화된 모델 결과가 반환된 고유 사례만 포함합니다. HTTP 429/503 및 구조화 응답 검증 실패는 가용성·커버리지로 별도 기록합니다.
