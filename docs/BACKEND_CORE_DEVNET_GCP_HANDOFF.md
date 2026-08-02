# InvoiceX — Devnet 자동 매수 데모 작업 기준

> 백엔드·코어 담당자 또는 구현 보조 AI에게 전달하는 데모용 작업 기준입니다.
> Solana **Devnet만** 사용합니다. Mainnet, 실제 고객 자금, 운영 수준의 인프라는 이번 범위가 아닙니다.

## 1. 현재 상태

- Gemini 문서 분석은 실제 API 호출 구조가 있습니다.
- Solana RWA 발행·Vault·자동 매수 코드도 준비돼 있습니다.
- 다만 실행 키, 테스트 USDC mint, Privy 설정이 없어 현재 Solana는 Mock으로 동작합니다.
- Firebase, Cloud Run, Cloud Storage, Secret Manager는 아직 연결돼 있지 않습니다.

즉, 이번 목표는 모든 운영 인프라를 만드는 것이 아니라, **Devnet에서 RWA 발행 → Agent 자동 매수 → 공급기업 USDC 수령을 실제로 한 번 성공시키는 것**입니다.

## 2. 데모에서 보여줄 흐름

1. 공급기업이 인보이스를 등록하고 구매기업 확인을 받습니다.
2. 공급기업이 RWA 발행을 요청합니다.
3. 인보이스별 RWA 토큰 1개를 Devnet에 발행하고 서비스 에스크로에 보관합니다.
4. 투자자가 외부 지갑으로 Mandate에 서명하고, 테스트 USDC를 Agent Vault에 예치합니다.
5. Treasury Agent가 투자 조건을 확인합니다.
6. 조건을 통과하면 자동으로 다음을 처리합니다.
   - Agent Vault 테스트 USDC → 공급기업 지갑
   - RWA 에스크로 토큰 → Agent Vault
7. Explorer 링크와 전후 잔액으로 결과를 확인합니다.

```text
OFFER_READY → RWA_ISSUED → FUNDING → FUNDED
```

`FUNDED`는 실제 Devnet 거래가 confirmed된 뒤에만 설정합니다.

## 3. 지갑 구성

### 사용자 지갑 2개

- **공급기업 지갑**: 조기정산 테스트 USDC를 받는 지갑
- **투자자 지갑**: Mandate에 서명하고 Vault에 테스트 USDC를 예치하는 지갑

### 서비스 지갑 3개

- **Agent Vault**: 투자자가 예치한 테스트 USDC를 보관하고 자동 매수에 사용하는 지갑
- **RWA Issuer/Escrow**: RWA를 발행하고 매수 전까지 보관하는 지갑
- **Gas Sponsor**: Devnet SOL을 보유하고 가스비를 대신 내는 지갑

서비스 지갑을 하나의 팀이 관리할 수는 있지만, 데모에서 실제 RWA 이동과 USDC 지급을 확인하려면 Agent Vault와 RWA Escrow 주소는 분리합니다. 개인키, Privy Secret, Gemini Key는 프론트엔드·Git·Firestore에 넣지 않습니다.

## 4. Solana / Privy 작업

### 필요한 설정값

```env
SOLANA_MODE=privy
SOLANA_CLUSTER=devnet
SOLANA_RPC_URL=<Devnet RPC URL>
SOLANA_USDC_MINT=<팀이 확정한 테스트 USDC mint>
SOLANA_USDC_DECIMALS=6

PRIVY_APP_ID=
PRIVY_APP_SECRET=
PRIVY_TREASURY_WALLET_ID=
PRIVY_RWA_ISSUER_WALLET_ID=
PRIVY_SPONSOR_WALLET_ID=
PRIVY_SPONSOR_WALLET_ADDRESS=

GASLESS_ENABLED=true
GASLESS_DEPOSIT_MAX_USDC=<데모 한도>
```

### 할 일

- Devnet Privy App과 서비스 지갑 3개를 생성합니다.
- 투자자 지갑에 테스트 USDC를 지급합니다.
- Gas Sponsor 지갑에 Devnet SOL을 넣습니다.
- 투자자는 외부 지갑으로 Mandate와 Vault 예치 트랜잭션에 서명합니다.
- Sponsor 지갑은 fee payer로 서명해 가스비를 냅니다.
- RWA는 인보이스별 1개만 발행하고, 발행 직후 Escrow 지갑에 둡니다.
- Agent가 투자 조건을 통과시킨 경우에만 USDC 지급과 RWA 이동을 실행합니다.

가스리스는 단순히 서비스 지갑에 SOL을 넣는 것만으로 끝나지 않습니다. 투자자가 USDC 전송에 서명하고, Sponsor가 fee payer로 서명한 뒤 서버가 거래를 전송해야 합니다.

## 5. Mandate와 Agent 판단

데모용 Mandate에는 아래 정보만 명확히 포함하면 됩니다.

- 투자자 지갑 주소
- Agent Vault 주소
- 총 투자 한도와 인보이스당 한도
- 허용 구매기업 목록
- 최소 Risk Score
- 만료일

투자자가 이 내용을 외부 지갑으로 서명하면 백엔드는 서명과 지갑 주소를 확인해 활성 Mandate로 저장합니다. 투자 조건을 바꾸면 다시 서명하게 합니다.

자동 매수 직전에는 프론트 값이 아니라 서버에 저장된 Mandate와 정책을 기준으로 아래만 확인합니다.

- Risk Score 충족 여부
- 허용한 구매기업인지
- 투자 한도를 넘지 않는지
- Mandate가 만료되지 않았는지
- Vault USDC 잔액이 충분한지

같은 인보이스가 두 번 지급되지 않도록 `invoice_id` 기준 중복 실행 방지는 반드시 넣습니다.

## 6. Firebase / GCP — 데모에 필요한 최소 범위

GCP 활용을 보여주되, 데모에서는 아래 네 가지만 연결하면 충분합니다.

| 서비스 | 데모에서 맡을 일 |
| --- | --- |
| Cloud Run | FastAPI backend 실행 |
| Secret Manager | Gemini·Privy·RPC·서비스 지갑 비밀값 보관 |
| Cloud Storage | 업로드한 PDF 문서 저장 |
| Firestore | 인보이스, Mandate, Vault 예치, RWA, 거래 상태 저장 |

Cloud Run 기본 로그로 Gemini·Solana 오류를 확인할 수 있게 `invoice_id`를 로그에 남깁니다.

Firestore에는 데모에 필요한 상태만 저장합니다.

```text
invoices
mandates
vaultDeposits
rwaAssets
transactions
```

Firebase는 지갑 키를 저장하거나 거래를 서명하는 곳이 아닙니다. 지갑 관련 비밀값은 Secret Manager 또는 Privy에만 둡니다.

Cloud Build, Artifact Registry, Cloud Tasks, Cloud Scheduler, Pub/Sub, Vertex AI 전환은 데모 이후 확장 항목으로 둡니다. 현재 Gemini API 호출을 Vertex AI라고 표현하지 않습니다.

## 7. 실제로 확인할 테스트

아래 여섯 가지가 되면 데모 기준으로 충분합니다.

1. 투자자 지갑의 테스트 USDC가 Agent Vault로 실제 이동하는지
2. Sponsor 지갑의 Devnet SOL이 예치 거래 수수료로 차감되는지
3. 인보이스별 RWA mint가 실제로 발행되고 Escrow 지갑에 보이는지
4. 조건을 통과하면 Agent가 자동으로 공급기업 지갑에 USDC를 보내는지
5. 같은 거래에서 Agent Vault가 RWA를 받는지
6. 같은 인보이스를 다시 실행해도 USDC가 중복 지급되지 않는지

각 테스트는 Explorer 링크와 전후 잔액 캡처를 남깁니다.

## 8. 담당자에게 필요한 결과물

- 공급기업·투자자·Vault·Escrow·Sponsor 공개 주소
- 실제 사용할 테스트 USDC mint 주소와 지급 방법
- RWA 발행 / Vault 예치 / 자동 매수 Explorer 링크
- 공급기업 USDC 증가, Vault RWA 보유, Sponsor SOL 차감 캡처
- Cloud Run URL
- Firestore와 Cloud Storage 연결 여부

## 9. 이번 데모에서 하지 않는 것

- Mainnet과 실제 고객 자금 사용
- 실제 법정통화 결제
- 분할 매수, 복수 투자자 매칭, 복잡한 정산 분배
- Vertex AI 전환
- 운영용 CI/CD, 비동기 작업 큐, 고급 모니터링
- 프론트에 키나 Secret 노출
