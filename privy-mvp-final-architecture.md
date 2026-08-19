# InvoiceX Privy 회원가입 MVP 최종 통합 설계

> 상태: 설계 문서만 작성. 코드 수정 및 DB migration 실행 없음.  
> 이 문서는 기존 MVP 구조 문서와 Signup API 문서를 통합한 최종 기준 문서다.

## 1. 한 줄 요약

Privy 이메일 인증을 마친 기업 대표자가 기업 정보를 제출하면, Backend가 Company와 User를 연결하고 Privy Solana Embedded Wallet을 자동 생성·연결한다. Investor Company면 논리 Vault DB 행도 함께 만들며, 이후 모든 업무 데이터의 소유와 권한은 Company를 기준으로 판단한다.

## 2. 확정 정책

| 항목 | 최종 정책 |
| --- | --- |
| User / Company | Company 1개당 대표 User 1명, User 1명당 Company 1개 |
| Membership | CompanyMembership, 직원 초대, 다중 담당자, 복잡한 RBAC 없음 |
| Company type | SUPPLIER, BUYER, INVESTOR. User role이 아니며 가입 후 변경 불가 |
| Investor | 개인 투자자 없음. Investor Company만 존재 |
| 투자 | Invoice 1개당 Investor Company 1개. 복수·분할 투자 없음 |
| Investment table | 독립 Investment 테이블은 만들지 않는다 |
| Embedded Wallet | 가입 완료 중 모든 User에게 Privy Solana Embedded Wallet 자동 생성·연결 |
| External Wallet | 가입 후 Profile Wallet에서 선택적으로 연결 |
| Vault | Investor Company마다 논리 Vault DB 행 1개를 가입 중 자동 생성 |
| 사업자등록번호 | 전역 unique, 중복 가입 불가 |
| KYB | 실제 조회 API 없음. 가입 성공 시 VERIFIED(Mock) |
| 재가입 | 동일 Privy User 재가입 불가 |

## 3. 최종 Architecture

Frontend는 이메일 OTP, 기업 유형, 기업 정보를 화면으로 제공한다. Privy는 이메일 OTP와 access token, Embedded Wallet 기능을 제공한다. Backend는 token 검증, User·Company·Wallet·Vault 저장과 권한 검사를 맡는다. DB는 업무상 소유 관계를 저장한다.

이메일 OTP용 InvoiceX Backend API는 만들지 않는다. 프론트의 code 발송, 검증, 재발송은 Privy SDK에 연결한다. 기존 Treasury, Issuer, Sponsor 서비스 지갑은 환경설정/Secret Manager로 유지하며 가입 Company wallet과 섞지 않는다.

## 4. 최종 DB 구조

기존 repository의 Invoice/RWA/Agent JSON은 유지하고, 소유·조회·투자 추적에 필요한 최소 관계 열만 추가한다.

| Entity | 최소 필드 및 제약 | 목적 |
| --- | --- | --- |
| User | id, privy_user_id UNIQUE, email, name, title, phone, company_id NULL UNIQUE, onboarding_status | Privy 로그인 주체와 대표자 profile |
| Company | id, name, type, business_registration_number UNIQUE, kyb_status, status | Invoice/Mandate/Vault의 업무상 소유자 |
| Wallet | id, company_id, wallet_type, privy_wallet_id UNIQUE nullable, chain, address UNIQUE, status | Company의 Embedded/External wallet |
| Vault | id, investor_company_id UNIQUE, available_usdc, status | Investor Company별 논리 Vault |
| Mandate | id, investor_company_id, signing_wallet_id, policy, signature, status | Investor Company의 투자 정책 |
| Invoice | 기존 document와 id, 아래의 Company/투자 추적 열 | 거래와 단일 투자 관계 |

User.company_id의 UNIQUE는 이번 MVP의 1:1 대표자 정책을 DB에서 보장한다. 나중에 다중 담당자가 필요할 때만 이 제약을 제거하고 Membership을 추가한다. 지금은 미래 확장을 위해 중간 테이블을 만들지 않는다.

Company.type은 SUPPLIER, BUYER, INVESTOR 중 하나다. 가입 성공 시 kyb_status는 VERIFIED(Mock), status는 ACTIVE다.

Wallet의 업무상 소유자는 Company다. 가입 중 자동 생성되는 Embedded Wallet은 Company에 연결한다. Privy User와 wallet의 실제 소유 관계는 Backend가 Privy server integration으로 확인한다.

Vault는 논리 DB 행이다. Solana Token Account, custody account, Solana Program 기반 Vault는 이번 설계에서 만들지 않는다. Investor 가입 시 available_usdc는 0으로 시작한다.

### Invoice의 최소 추가 열

| 열 | 용도 |
| --- | --- |
| supplier_company_id | 공급 Company |
| buyer_company_id | 구매 Company. 새 Invoice에서는 반드시 존재, legacy 데이터만 임시 nullable |
| investor_company_id nullable | 단일 투자 Company |
| mandate_id nullable | 사용 Mandate |
| vault_id nullable | 사용 논리 Vault |
| investment_amount_usdc nullable | 투자 금액 |
| investment_status nullable | 투자 상태 |
| invested_at nullable | 투자 시점 |
| investment_transaction_signature nullable | Solana 실행 signature |

독립 Investment 테이블 없이도 기존 AgentDecision, RwaAsset, BlockchainTransaction과 이 열을 합쳐 투자자, Invoice, 금액, Mandate, Vault, 시점, 상태, signature를 모두 추적할 수 있다.

Invoice에는 selected_investor_wallet_id를 추가하지 않는다. 실제 RWA가 전송된 wallet/address는 RwaAsset 또는 transaction 기록에 남기고, Invoice의 투자 소유는 investor_company_id로 표현한다.

buyer_company_id는 Supplier가 제출한 Buyer 사업자등록번호로 Company를 조회해 설정한다. 업로드 문서에서 번호를 추출할 수 있더라도, 실제 연결에는 Supplier가 확인한 번호를 사용한다.

## 5. Entity 관계도

~~~mermaid
erDiagram
  USER ||--|| COMPANY : "represents in MVP"
  COMPANY ||--o{ WALLET : owns
  COMPANY ||--o{ INVOICE : supplier_or_buyer_or_investor
  COMPANY ||--o{ MANDATE : owns
  COMPANY ||--o| VAULT : investor_only
  INVOICE }o--|| MANDATE : uses
  INVOICE }o--|| VAULT : uses
  INVOICE ||--o| RWA_ASSET : tokenized_as
  MANDATE }o--|| WALLET : signed_with
~~~

## 6. 최종 회원가입 Flow

1. Privy 이메일 OTP 완료 후 access token을 발급한다.
2. Frontend가 GET /api/v1/auth/me을 호출한다.
3. Backend는 privy_user_id 기준 Pending User를 생성 또는 조회한다.
4. COMPLETED면 응답의 nextPath dashboard로 이동하고, NEEDS_COMPANY_PROFILE이면 가입 UI를 계속 보여준다.
5. 사용자는 기업 유형, 기업명, 사업자등록번호, 담당자명·직책·연락처를 입력한다.
6. Frontend가 POST /api/v1/onboarding/company를 호출한다.
7. Backend는 Company 생성, User profile 업데이트, User.company_id 연결, KYB VERIFIED(Mock)를 처리한다.
8. Backend는 onboarding_status를 PROVISIONING_EMBEDDED_WALLET로 바꾸고 Privy Solana Embedded Wallet을 생성 또는 조회한다.
9. Backend는 Wallet DB 행을 Company에 연결한다. Investor면 logical Vault 행을 balance 0으로 생성한다.
10. 모든 단계가 성공하면 onboarding_status를 COMPLETED로 변경하고 embeddedWallet, nextPath를 반환한다.
11. Frontend는 응답 성공 후에만 가입 완료 화면과 dashboard를 보여준다.

## 7. 회원가입 API

현재 회원가입 Frontend에 필요한 Backend API는 두 개뿐이다.

### GET /api/v1/auth/me

인증은 Privy access token bearer header다.

- User와 가입 상태를 반환한다.
- User가 없으면 Pending User를 생성/조회한다.
- 가입 전에는 company와 embeddedWallet이 null이고 onboardingStatus는 NEEDS_COMPANY_PROFILE, nextPath는 /signup이다.
- 가입 완료 후에는 User profile, Company(type, kybStatus), Embedded Wallet, onboardingStatus COMPLETED, type별 nextPath를 반환한다.

### POST /api/v1/onboarding/company

인증은 Privy access token bearer header다.

요청 body:

~~~json
{
  "company": {
    "name": "에이씨미 주식회사",
    "type": "SUPPLIER",
    "businessRegistrationNumber": "123-45-67890"
  },
  "representative": {
    "name": "홍길동",
    "title": "재무팀 매니저",
    "phone": "010-0000-0000"
  }
}
~~~

email과 privyUserId는 body에서 받지 않고 검증된 Privy token에서 결정한다.

성공 응답은 Company, Embedded Wallet, Investor일 경우 logicalVault, onboardingStatus COMPLETED, nextPath를 포함한다.

| HTTP | code | 의미 |
| --- | --- | --- |
| 401 | PRIVY_TOKEN_INVALID | token 없음 또는 검증 실패 |
| 409 | ONBOARDING_ALREADY_COMPLETED | 동일 Privy User 재가입 |
| 409 | BUSINESS_REGISTRATION_ALREADY_USED | 사업자등록번호 중복 |
| 422 | VALIDATION_ERROR | 필수값/형식 오류 |
| 502 | EMBEDDED_WALLET_PROVISIONING_FAILED | Company는 유지, wallet 생성 재시도 필요 |

SignupPage는 businessRegistrationNumber와 contactPhone을 state 또는 FormData에 반드시 보관해 POST body에 포함한다. 완료 화면은 API의 nextPath를 사용한다.

## 8. Wallet 구조

### Embedded Wallet

Embedded Wallet은 사용자 선택 UI나 사용자 액션 API가 아니다. POST onboarding/company 내부에서 Backend가 Privy server integration을 호출해 생성 또는 조회하고 DB에 연결한다. 따라서 사용자 버튼용 POST /api/v1/wallets/embedded는 만들지 않는다.

Company/User 생성 뒤 wallet provisioning이 실패하면 status는 PROVISIONING_EMBEDDED_WALLET로 남긴다. 같은 POST 재시도는 기존 Company/User를 재사용하고 wallet 생성 또는 조회만 다시 수행한다. Company, Wallet, Vault가 중복 생성되면 안 된다.

### External Wallet

External Wallet은 가입 이후 Profile Wallet 화면에서 추가한다. 후속 API는 GET /api/v1/wallets, POST /api/v1/wallets/external/challenge, POST /api/v1/wallets/external/confirm, PATCH /api/v1/wallets/{walletId}/primary다.

주소만 받아 등록하지 않는다. nonce/message와 Solana signature를 검증한 뒤 Company에 연결한다.

## 9. Authorization

Backend는 Privy token에서 User를 확인하고 User.company_id, Company.type, onboarding_status로 principal을 만든다.

- COMPLETED가 아니면 업무 API를 허용하지 않는다.
- Invoice 조회는 supplier_company_id, buyer_company_id, investor_company_id 중 현재 company_id와 일치하는 것만 반환한다.
- Supplier는 Invoice 생성·offer·정산, Buyer는 자기 Invoice verification, Investor는 자기 Mandate/Vault만 처리한다.
- request의 ownerWalletAddress, viewerRole, companyId는 권한 근거가 아니다.

## 10. 기존 Demo Backend에서 변경해야 할 부분

| 현재 | 변경 방향 |
| --- | --- |
| 고정 데모 email/password와 HMAC token | Privy token 검증과 auth/me |
| LoginRole, require_roles | Company.type과 resource Company FK 검사 |
| profile_wallets의 역할별 전역 주소 | Company별 wallets |
| Mandate/Vault의 owner_wallet_address | investor_company_id |
| JSON party만으로 접근 판단 | Invoice Company FK |
| Vault API의 ownerWalletAddress | principal Company의 logical Vault를 서버에서 조회 |

## 11. 최소 Migration 방향

이번 요청에서 실제 migration은 실행하지 않는다.

1. DB를 백업한다.
2. users, companies, wallets를 추가한다.
3. Invoice/Mandate/Vault에 Company 관계와 최소 투자 추적 열을 추가한다.
4. 데모 Supplier/Buyer/Investor를 Company 3개와 대표 User 3개로 명시 mapping한다.
5. 기존 demo invoice party를 Company FK에 연결한다.
6. Privy 인증과 onboarding을 연결한 뒤 Company 기반 권한으로 전환한다.
7. 검증 후 HMAC demo login과 profile_wallets를 제거한다.

## 12. 구현 시 권장 순서

1. Schema와 repository interface
2. Privy token 검증
3. GET auth/me
4. POST onboarding/company와 Embedded Wallet provisioning
5. SignupPage state와 API 연결
6. Company 기반 Invoice/Mandate/Vault authorization
7. Investor logical Vault 생성 검증
8. External Wallet Profile 기능

## 13. Buyer Review 연결 설계

현재 서비스의 업무 순서는 Supplier Invoice 생성 → Buyer 검토 → Buyer 승인 → Supplier 발행 요청 → RWA 발행 완료다. Buyer 등록 여부는 Buyer Review 요청 단계가 아니라 **Invoice 생성 과정**에서 검증한다.

1. Supplier가 문서를 업로드하면 Document Agent가 Buyer 사업자등록번호를 추출한다. 추출 실패 또는 값 불일치는 Invoice 생성 오류로 처리한다.
2. Backend는 추출한 business_registration_number로 ACTIVE Buyer Company를 조회하고, Company.type이 BUYER인지 확인한다.
3. 등록 Buyer가 없거나 type이 BUYER가 아니면 422 BUYER_NOT_REGISTERED를 반환하고 요청을 중단한다. UI는 “구매기업이 InvoiceX에 등록되어 있지 않아 인보이스를 생성할 수 없습니다.”라고 경고한다.
4. 이 실패 경로에서는 정식 Invoice, Verification, Agent 실행 이력을 생성하지 않는다. 업로드 문서는 임시 분석용으로만 처리하고 실패 후 정리한다.
5. 등록 Buyer가 확인된 경우에만 buyer_company_id를 연결하여 Invoice를 생성한다. 같은 성공 흐름에서 Verification을 PENDING으로 만들고 Invoice를 BUYER_REVIEW로 전환해 Buyer Review 대기열에 넣는다.
6. Buyer dashboard와 verification 목록은 Invoice.buyer_company_id가 principal.company_id인 건만 보여준다. 따라서 다른 Buyer Company는 검토 대기열이나 상세에 접근할 수 없다.
7. 해당 Buyer Company가 승인하면 Verification은 CONFIRMED가 되고, Invoice는 현재 workflow의 OFFER_READY 단계로 진행한다.
8. Supplier는 자기 supplier_company_id가 일치하고 Buyer 검토가 CONFIRMED인 Invoice에만 발행 요청을 할 수 있다. 기존 offer 수락/발행 흐름은 RWA_ISSUED로 이어진다.

미등록 Buyer를 위한 Draft, 대기, 초대, placeholder Company, Company 검색 API는 MVP 범위에서 제외한다.

또한 External Wallet Profile UI, 실제 온체인 Vault/token account provisioning, RWA custody 세부 모델, Company 대표 User 변경은 후속 항목이다.

## 14. MVP 이후로 미룬 항목

- CompanyMembership, 다중 담당자, 직원 초대
- 개인 투자자와 여러 InvestmentAccount
- 복수/분할 투자와 독립 Investment/Position 테이블
- 실제 KYB/KYC, MFA, 관리자 승인
- vault ledger와 회계 reconciliation
- wallet rotation/revocation, 다중 서명자·권한 위임
- production-grade on-chain custody/escrow
