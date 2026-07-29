# InvoiceX

InvoiceX는 역할별 코드를 다음 네 영역으로 분리합니다.

- `agent/`: 문서 추출, 위험 분석, 목업 및 Agent 테스트
- `backend/`: API, 인증, 데이터 저장 및 외부 연동
- `core/`: 결정론적 도메인 규칙과 검증
- `frontend/`: 사용자 인터페이스와 UX

현재 개발 단계는 `feat`이며, 영역별 작업은 대응하는 `feat-*` 브랜치에서 진행합니다.
