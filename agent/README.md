# InvoiceX Agents

InvoiceX의 Document Agent와 Risk Agent를 위한 Python 패키지다. AI Studio의 Gemini API를 사용하며, 구조화된 Pydantic 출력과 엄격한 근거 검증을 적용한다.

## 범위

- Document Agent: 문서 유형 분류, 필드 추출, 누락·불일치 탐지, 원문 근거 연결
- Risk Agent: 백엔드가 계산한 위험 결과의 근거 기반 설명과 Risk Passport 요약
- 공통 Gemini real/mock 클라이언트

Risk Score, 조기정산 조건, 상태 전이, 자금 이동은 이 패키지의 책임이 아니다.

## 로컬 설정

```powershell
Copy-Item .env.example .env
```

`.env`에 AI Studio 키를 직접 설정한다.

```dotenv
GEMINI_API_KEY=your-local-key
```

키를 코드, 로그, 테스트 또는 Git에 넣지 않는다.

## 개발 명령

```powershell
uv sync
uv run pytest
uv run ruff check .
```

실제 Gemini 연동은 개인·거래처 정보가 없는 합성 데이터로 확인한다.

```powershell
uv run python scripts/create_synthetic_invoice_pdf.py
uv run python scripts/smoke_gemini_document.py
uv run python scripts/smoke_gemini_risk.py
```
