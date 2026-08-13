# Document Agent 실제 공개 양식 평가 자료

2026-08-13 기준 `origin/main` (`9298e1feb3d1894a9e86808277b86c64c2d2e01f`)의 Document Agent를 `gemini-3.6-flash`로 평가한 보존 자료입니다.

## 구성

- `fixtures/`: Adobe·GSA 공개 원본 양식에 합성 평가값을 기입한 PDF 8개, 사전 정답 JSON, 출처 URL·SHA-256 manifest, fixture 검증 결과
- `results/initial/`: 최초 8회 호출 결과
- `results/remeasurement/`: 최초에 결과가 없었던 OF348·GSA3025 각 1회 재측정 결과
- `reports/`: 최종 Word/PDF 보고서와 기계 판독용 요약 JSON

## 최종 고유 양식 기준 결과

- 유효 구조화 결과: 7/8 (87.5%)
- 유효 결과의 전체 필드 값: 98/98 (100.0%)
- 문서 유형을 포함한 완전 일치: 6/7 (85.7%)
- OF348: 최초 HTTP 503 이후 재측정에서 정확 일치
- GSA3025: 최초·재측정 모두 `AI_RESPONSE_INVALID`; 추출값이 없어 정확도 분모에서 제외
- 총 API 호출: 최초 8회 + 재측정 2회 = 10회

이 시험은 공개 원본 레이아웃에 적힌 값의 추출과 단일 문서 유형 분류를 측정합니다. 문서 내용의 진위·조작 판정과 문서 간 값 불일치 검출 정확도는 이번 시험 범위가 아닙니다.

API 키와 로컬 `.env`, 임시 렌더 이미지 및 캐시는 포함하지 않았습니다.
