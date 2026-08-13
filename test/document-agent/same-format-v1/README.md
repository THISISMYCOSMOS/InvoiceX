# Same-format scenarios v1

기존 4문서 양식을 유지한 채 정상, 표기 변형, 단일·복합 불일치 시나리오를 평가했습니다.

- 설계 19세트, 측정 11세트, 미측정 8세트(HTTP 429)
- 측정 문서 44개, 필드 셀 616개
- 완전 일치 11/11, 필드 616/616
- 불일치 TP/FP/FN = 11/0/0, reviewRequired 11/11

`fixtures/baseline`은 기존 2세트, `fixtures/scenarios`는 생성한 17세트입니다. `results/merged-summary.json`과 개별 원시 결과가 판정 근거입니다. 각 측정 사례의 성공 실행은 1회이므로 반복성은 아직 측정되지 않았습니다.
