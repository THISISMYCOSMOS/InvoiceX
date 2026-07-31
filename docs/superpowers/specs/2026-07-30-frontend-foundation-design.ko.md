# InvoiceX 프론트엔드 기반 설계

## 목적과 범위

기존 `feat-frontend` 브랜치에서 InvoiceX 해커톤 MVP의 최종 디자인 이전 프런트엔드 기반을 구축합니다. 역할별 화면, 재현 가능한 전체 데모 상태 흐름, 문서 업로드·분석 검토 화면 골격, Mock과 백엔드 `/api/v1` API를 전환할 수 있는 경계를 제공합니다.

이번 작업에는 로그인·회원가입, Gemini 직접 호출, 위험 점수 계산, AP2 검증, 지갑 서명, Solana 송금, 최종 디자인 시스템을 포함하지 않습니다. 이 책임은 백엔드·Agent·후속 디자인 작업에 남깁니다.

## 저장소와 API 계약 확인 결과

- 현재 체크아웃 브랜치는 `feat-frontend`이며, 제품 코드로는 `frontend/.gitkeep`만 있습니다.
- 커밋된 프런트엔드 패키지, 백엔드 API 구현, OpenAPI 명세, DTO 정의는 아직 없습니다.
- 현재 체크아웃의 `docs/`는 미추적 상태입니다. 사용자가 제공한 원본 요청 문서는 수정하거나 커밋하지 않습니다.
- 프런트엔드 요청 문서의 이전 API 예시보다, 사용자가 공유한 `/api/v1` API 계약을 우선합니다. 프런트는 adapter를 통해 이 계약을 사용합니다.
- 응답 JSON 구조와 multipart 필드명은 아직 커밋된 코드에서 확인되지 않았습니다. 실제 API adapter 안에만 격리해, 백엔드 연동 변경이 컴포넌트나 도메인 타입에 퍼지지 않도록 합니다.

## 선택한 방식

`frontend/`에 Vite + React + TypeScript 앱을 독립적으로 구성합니다. 라우팅은 React Router, 서버 상태는 TanStack Query, 테스트는 Vitest와 Testing Library를 사용합니다.

루트에 프런트엔드 파일을 섞는 방식보다 이 방식을 선택합니다. 이후 백엔드 코드와의 경계가 명확하고 기존 `frontend/` 디렉터리의 책임과도 일치합니다.

## 도메인과 상태 모델

공통 TypeScript 도메인 타입을 Invoice, 문서, 문서 분석, Risk Passport, 블록체인 트랜잭션, A2A Agent Trace의 유일한 UI 모델로 사용합니다. 공통 상태 모듈은 전체 MVP Invoice 상태값, 한국어 상태 라벨, 허용되는 Mock 상태 전이, 단순화된 공급기업 등록 단계를 정의합니다.

```text
등록 -> 구매기업 확인 -> 검증 완료
```

모든 데모 값은 단일 시나리오 모듈에서 관리합니다. 권위 있는 MVP 상수인 `INV-2026-001`, 20,000,000 KRW, 공급기업 선지급 18,800 USDC, 투자기관 정산 19,800 USDC, 플랫폼 수수료 200 USDC를 사용합니다. 공급기업 잔여 지급은 표시하거나 계산하지 않습니다.

## API 경계

화면 컴포넌트는 Query·Mutation Hook만 호출합니다. Hook은 API 모듈을 호출하고, API 모듈은 선택된 adapter를 사용합니다.

```text
컴포넌트 -> Query/Mutation Hook -> 도메인 API 모듈 -> 선택된 adapter
                                                   -> Mock adapter
                                                   -> 실제 HTTP adapter
```

`VITE_USE_MOCK_API=true`이면 Mock adapter를, `false`이면 실제 adapter를 선택합니다. 실제 adapter는 `VITE_API_BASE_URL`에 `/api/v1`을 결합하고 다음 엔드포인트를 사용합니다.

```text
POST /invoices
GET  /invoices
GET  /invoices/{invoiceId}
POST /invoices/{invoiceId}/verification-request
GET  /verifications
GET  /verifications/{id}
POST /verifications/{verificationId}/confirm
POST /invoices/{invoiceId}/offer-response
GET  /investor/dashboard
POST /invoices/{invoiceId}/settlement/mock-payment
```

`fetch`는 실제 adapter에서만 호출합니다. 백엔드 DTO가 병합되기 전까지 mapping 함수는 필요한 응답 필드를 문서화하고, 필수 데이터가 없으면 임의의 비즈니스 규칙을 만들지 않고 명확히 실패하도록 합니다.

## Mock 데모 흐름

Mock adapter는 하나의 해피 패스 Invoice를 위한 메모리 내 상태 머신입니다. 개발자 화면은 다음 순서로 상태를 진행시킬 수 있습니다.

```text
초기화 -> 문서 분석 -> 구매기업 확인 -> Risk Passport 생성
-> 공급기업 조건 동의 -> Treasury 펀딩 -> KRW Mock 입금 -> 정산
```

MVP 책임 경계를 지킵니다. Gemini 분석 결과는 백엔드 경계에서 이미 반환된 데이터로 취급하고, 위험·정책 결과는 표시 데이터로만 다룹니다. KRW 이벤트는 Sandbox임을 명확히 표기하고, 트랜잭션 영수증은 실제 지갑 동작이 아닌 데모 기록입니다.

Buyer의 보완 요청과 이의 제기 버튼은 해당 상태로만 전환합니다. 전체 분쟁·보완 처리 흐름은 추가하지 않습니다.

## 라우트와 화면

- `/supplier`: 공급기업 요약, Invoice 목록, 신규 등록 링크
- `/supplier/invoices/new`: 4종 문서 슬롯, 파일 검증, 업로드·교체·제거, 분석 요청
- `/supplier/invoices/:invoiceId`: 상태별 섹션을 전환하는 단일 상세 화면. 조건 제안, 펀딩, 정산 영수증을 포함
- `/buyer`: 검증 요청 목록과 지급 예정 목록
- `/buyer/invoices/:invoiceId`: 상태에 따른 검증 폼 또는 Mock 만기 지급 화면
- `/investor/setup`: API 호출과 화면 상태만 제공하는 Mandate·정책 설정 골격. 브라우저에서 AP2·Gasless 로직은 실행하지 않음
- `/investor`: 투자기관 대시보드
- `/investor/activities/:invoiceId`: Risk Passport, 정책·AP2 결과, Agent Trace, 트랜잭션·정산 기록
- `/dev/demo`: 일반 사용자 내비게이션에 노출하지 않는 데모 제어 화면. 제품 화면과 같은 Hook 사용

공통 접근성 컴포넌트는 레이아웃, 개발 환경 전용 역할 전환, 로딩·오류·빈 상태, 상태 배지, 업로드 카드, PDF 미리보기 골격, 추출 필드 행, 공급기업 진행 표시, Risk Passport 요약, Agent Trace, 트랜잭션 영수증, Explorer 링크로 구성합니다. 스타일은 시맨틱 HTML과 최소 CSS만 사용합니다.

## 검증과 오류 처리

업로드는 문서 유형별 파일 1개, PDF/JPG/JPEG/PNG, 파일당 최대 20MB만 허용합니다. 유효하게 완료된 네 문서 슬롯이 모두 채워져야 분석 버튼이 활성화됩니다. Mutation이 끝나면 관련 Invoice·목록·검증 목록·대시보드 Query를 무효화합니다. 로딩, API 오류, 파일 검증 오류, PDF 미리보기 불가 상태를 명시적으로 표시합니다.

## 테스트 전략

생산 코드를 작성하기 전에 테스트를 작성합니다. 구현 세부사항이 아니라 관찰 가능한 동작을 검증합니다.

- 상태 라벨, 공급기업 단계 매핑, 허용되는 Mock 상태 전이
- 허용·거부 파일 형식과 20MB 경계값
- Mock adapter의 전체 상태 전이 효과
- Explorer 링크 생성
- 유효한 네 문서가 등록되기 전 분석 제어 비활성화
- Buyer 검증, Offer 준비, 펀딩 완료, 정산 완료의 대표 화면 상태

완료 보고 전 설정된 `lint`, `typecheck`, `test`, `build` 명령을 실행합니다. 누락된 백엔드 DTO나 API 오류는 임의 계약으로 숨기지 않고 연동 이슈로 보고합니다.

## 백엔드 연동 시 후속 작업

백엔드 브랜치가 병합되면 실제 adapter의 임시 응답 mapping을 실제 DTO로 교체합니다. 백엔드 팀은 다음을 제공하거나 커밋해야 합니다.

1. `POST /invoices`의 multipart 필드명 및 Invoice·분석 응답
2. Invoice 목록·상세 응답 스키마
3. 검증 ID와 Confirm 요청·응답 스키마
4. Offer 응답 요청 형태
5. 투자기관 대시보드 스키마
6. Mock 결제 응답 및 트랜잭션·정산 기록 스키마
