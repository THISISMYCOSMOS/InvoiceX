# InvoiceX Solana Devnet 토큰·지갑 운영 런북

> AI 작업 지침: 작업을 시작하기 전에 이 문서를 끝까지 읽고, 현재 저장소와 RPC 상태를 다시 확인한다. 문서의 과거 성공 기록을 현재 상태로 가정하거나, 검증 단계를 생략해서는 안 된다.

## 1. 문서 목적

이 문서는 팀원 또는 AI 작업자가 InvoiceX의 Solana Devnet 데모를 같은 기준으로 재현하기 위한 단일 운영 기준이다. 다음 흐름을 대상으로 한다.

1. 공급기업과 투자자 MetaMask 계정을 구분한다.
2. 투자자 지갑에 Devnet SOL과 공식 테스트 USDC를 준비한다.
3. 투자자 지갑에서 Agent Vault(Treasury)로 USDC를 실제 전송한다.
4. Solana RPC와 InvoiceX 백엔드 양쪽에서 같은 트랜잭션을 검증한다.
5. 오류가 발생하면 임의의 우회 없이 이 문서의 중단 조건을 따른다.

이 문서에서 `토큰 발행`은 별도 SPL 토큰을 새로 만드는 작업이 아니다. InvoiceX는 Circle의 공식 **Solana Devnet USDC mint**를 사용하며, Circle Faucet에서 테스트 USDC를 배포받는다.

## 2. AI 작업자가 반드시 지킬 규칙

- 현재 수정 작업은 `work` 브랜치를 기준으로 한다.
- 시작 전에 `git branch --show-current`, `git status --short`, `git log -3 --oneline`을 확인한다.
- 기존 `.data/`, `CLAUDE.md` 및 다른 사용자의 미추적·미커밋 변경을 수정하거나 스테이징하지 않는다.
- 시드 문구, 개인키, Secret Recovery Phrase, Privy secret을 요청·출력·저장하지 않는다.
- 송금에는 축약 주소를 사용하지 않는다. 항상 전체 공개 주소를 비교한다.
- 앱, MetaMask 사이트 연결, 전송 준비 응답의 주소가 하나라도 다르면 서명 요청을 열지 않는다.
- 서명창에 `Solana Mainnet`이 표시되면 즉시 취소한다. InvoiceX 데모는 Devnet 전용이다.
- 외부 전송 후에는 성공 UI만 믿지 말고 RPC 잔액, 트랜잭션 `meta.err`, 백엔드 확인 상태를 모두 검사한다.
- 모든 검증이 끝나기 전에는 완료라고 보고하지 않는다.

## 3. 고정 네트워크와 공개 주소

아래 값은 공개 데모 식별자다. 환경을 새로 구성했거나 지갑을 교체했다면 그대로 가정하지 말고 먼저 RPC와 환경 설정을 다시 확인한다.

| 구분 | 값 |
|---|---|
| Solana cluster | `devnet` |
| RPC | `https://api.devnet.solana.com` |
| CAIP-2 | `solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1` |
| Circle Devnet USDC mint | `4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU` |
| USDC decimals | `6` |
| 공급기업 MetaMask Account 1 | `HviSYZxsb3xRqQGZH6xp5Ynmq5TJbEKnBEEqJse6iV9` |
| 투자자 MetaMask Account 2 | `99HjRok4PZoX16d7Zz88S3EW4yjTDaHXJ492GaMJHD1U` |
| Privy Agent Vault / Treasury | `BDRW9KjvbJA5pxavitWJQ6o3HQiHjmtiZKw5mnJbjXYY` |
| 공급기업 USDC ATA | `Gq9iDSwbNMYQaJdCU12F2sNgC82YgT5LCfFLbtSJ6vbj` |
| 투자자 USDC ATA | `Hbu4JqCGVWQxPf5MUia5sg4fP2bK9Bmxr441cL4BEKXU` |
| Treasury USDC ATA | `6YED4SrwsRdZeM31iTndPgptvRJoQ3cjh7ep3gyhuNyK` |

공급기업과 투자자 주소가 같으면 역할별 지갑 구분이 실패한 것이다. 전송을 중단하고 MetaMask 사이트 연결 권한부터 수정한다.

## 4. 현재 구현에서 실제인 것과 목업인 것

| 항목 | 현재 동작 | 판정 |
|---|---|---|
| MetaMask Solana 지갑 연결 | Wallet Standard를 통한 실제 브라우저 지갑 연결 | 실제 |
| Devnet SOL | Solana Faucet/에어드롭에서 받은 테스트 SOL | 실제 Devnet, 금전 가치 없음 |
| Devnet USDC | Circle Faucet의 공식 Devnet USDC mint | 실제 Devnet, 금전 가치 없음 |
| 투자자 → Treasury 예치 | MetaMask 서명 후 Solana Devnet 전송 | 실제 온체인 |
| 예치 확인 | 백엔드가 RPC에서 서명자, mint, 출발·도착 잔액 변화와 금액을 검증 | 실제 온체인 검증 |
| Treasury → 공급기업 조기정산 | `SOLANA_MODE=auto`가 Privy로 해석되는 경우 Privy 서버 지갑이 실제 전송 | 실제 Devnet |
| 조기정산 표시 금액 | 시나리오 제안 금액은 `18,800 USDC` | 데모 표시값 |
| 조기정산 실제 Devnet 전송액 | `SOLANA_DEMO_TRANSFER_AMOUNT_USDC=1`이면 최대 `1 USDC` | 의도적으로 제한한 실제 전송 |
| 원화 입금 | Settlement Partner 이벤트 | 목업 |
| `availableVaultUsdc` | 현재 백엔드 프로세스에서 확인한 예치·예약을 합산한 메모리 값 | 온체인 잔액 아님 |
| 인보이스·예치 상태 | 현재 `InvoiceService` 인메모리 상태 | 서버 재시작 시 초기화 |

`availableVaultUsdc`와 Treasury RPC 잔액이 다른 것은 현재 구조상 가능하다. 예를 들어 Faucet으로 Treasury에 직접 넣은 20 USDC는 백엔드 논리 잔액에 포함되지 않는다. 온체인 잔액은 반드시 RPC로 별도 확인한다.

## 5. 실행 전 점검

### 5.1 필수 커밋 확인

투자자 예치에는 최소한 다음 수정이 포함되어야 한다.

- `9811fb9 fix: Devnet 투자자 예치 체인과 계정 검증`

확인 명령:

```powershell
git merge-base --is-ancestor 9811fb9 HEAD
if ($LASTEXITCODE -ne 0) { throw "Required wallet fix 9811fb9 is missing" }
```

이 수정은 `signTransaction()` 단독 호출 대신 다음과 같이 Devnet 연결 컨텍스트가 포함된 표준 경로를 사용한다.

```ts
sendTransaction(transaction, connection, {
  preflightCommitment: "confirmed",
});
```

`signTransaction(transaction)`을 직접 우선 호출하면 Wallet Standard의 체인 정보가 빠져 MetaMask가 Mainnet으로 시뮬레이션할 수 있다.

### 5.2 환경 변수

프런트엔드 `frontend/.env.local`의 비밀이 아닌 필수 값:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
VITE_USE_MOCK_API=false
VITE_SOLANA_NETWORK=devnet
VITE_SOLANA_RPC_URL=https://api.devnet.solana.com
```

백엔드는 `backend`에서 실행할 때 루트 `.env`를 `../.env`로 읽는다. AI는 `.env` 전체를 출력하면 안 된다. 다음 키만 이름과 설정 여부를 확인한다.

- `SOLANA_CLUSTER`
- `SOLANA_RPC_URL`
- `SOLANA_CAIP2`
- `SOLANA_USDC_MINT`
- `SOLANA_USDC_DECIMALS`
- `SOLANA_DEMO_TRANSFER_AMOUNT_USDC`
- Privy 관련 키는 **값을 출력하지 말고 존재 여부만** 확인한다.

### 5.3 서버 실행

백엔드:

```powershell
Set-Location backend
uv sync --all-groups
uv run uvicorn invoicex_backend.main:app --reload --port 8000
```

프런트엔드:

```powershell
Set-Location frontend
npm install
npm run dev -- --port 5173 --strictPort
```

브라우저는 반드시 `http://localhost:5173`을 사용한다. 백엔드 CORS 기본값도 `http://localhost:5173`이다. `http://127.0.0.1:5173`을 섞으면 CORS 때문에 화면이 `불러오는 중`에 머물 수 있다. `127.0.0.1`을 사용해야 한다면 `FRONTEND_ORIGIN`도 같은 origin으로 변경하고 백엔드를 재시작한다.

확인 URL:

- 프런트엔드: `http://localhost:5173/login`
- 백엔드 OpenAPI: `http://localhost:8000/api/docs`
- 백엔드에는 현재 `/health` 경로가 없으므로 `/health`의 404를 서버 장애로 오판하지 않는다.

## 6. MetaMask 역할별 계정 연결

MetaMask 멀티체인 계정은 Account마다 별도의 Solana 주소를 가진다. 그러나 MetaMask 상단에서 Account를 바꾸는 것만으로 이미 허용된 `localhost:5173` 사이트 계정이 자동으로 바뀌지 않을 수 있다.

### 6.1 공급기업

1. MetaMask에서 Account 1을 선택한다.
2. 주소 선택 메뉴에서 Solana 공개 주소가 `HviSY...6iV9`인지 확인한다.
3. InvoiceX 공급기업 설정에서 연결한다.
4. 앱의 전체 주소가 Account 1 주소와 일치하는지 확인한다.

### 6.2 투자자

1. 열려 있는 서명 요청이 있으면 취소한다.
2. InvoiceX에서 기존 지갑 연결을 해제한다.
3. MetaMask에서 Account 2를 선택한다.
4. MetaMask 하단의 `localhost:5173` 연결 관리에서 Account 1 권한을 제거하고 Account 2를 허용한다.
5. InvoiceX에서 MetaMask를 다시 연결한다.
6. 다음 세 값이 모두 `99Hj...HD1U`인지 확인한다.
   - MetaMask Account 2의 Solana 주소
   - MetaMask 하단 `localhost:5173`의 연결 Account
   - InvoiceX 투자자 화면의 전체 지갑 주소

역할 전환 시 WalletProvider를 유지하는 현재 구현은 **한 개의 활성 연결을 유지**할 뿐, 공급기업 Account 1과 투자자 Account 2를 동시에 활성화하지 않는다. 서로 다른 계정을 쓸 때는 MetaMask 사이트 권한을 전환해야 한다. 역할별 자동 계정 전환이 필요하면 별도의 지갑 세션 설계가 추가로 필요하다.

MetaMask의 `Unable to connect to Hardhat` 배너와 `Network: Hardhat` 표시는 EVM 네트워크 상태다. InvoiceX의 Solana Wallet Standard 연결과는 별개이므로 이 배너만으로 Solana 예치를 실패로 판정하지 않는다.

## 7. 테스트 토큰 준비

### 7.1 Devnet SOL

SOL은 ATA 생성과 전송 수수료에 필요하다. 데모에는 0.05~0.5 SOL이면 충분하다.

Solana CLI가 설치되어 있을 때는 우선 프로그램 방식으로 요청할 수 있다.

```powershell
solana airdrop 1 99HjRok4PZoX16d7Zz88S3EW4yjTDaHXJ492GaMJHD1U --url devnet
```

공용 RPC는 429 또는 Faucet 고갈 오류를 반환할 수 있다. 반복 재시도로 제한을 소모하지 않는다.

공식 웹 Faucet은 `https://faucet.solana.com/`이다. 이 사이트는 AI 에이전트가 웹 폼을 직접 사용하지 말라고 명시한다. AI는 페이지와 주소를 사용자에게 안내하고, 사용자가 직접 요청하도록 한다. 현재 공식 화면 기준 최대 8시간당 2회이며 GitHub 연결 여부에 따라 선택 금액이 달라질 수 있다.

### 7.2 Devnet USDC

Circle Faucet: `https://faucet.circle.com/?allow=true`

1. 자산으로 `USDC`를 선택한다.
2. 네트워크로 `Solana Devnet`을 선택한다.
3. 투자자 **전체 주소**를 입력한다.
4. `Send 20 USDC`를 요청한다.
5. reCAPTCHA가 표시되면 사용자가 직접 완료한다.
6. 반환된 Explorer 서명을 저장한다.

Circle 공개 Faucet의 일반 제한은 주소·자산·네트워크 조합당 2시간에 한 번, 20 USDC다. 발급 후 mint가 반드시 `4zMMC...ncDU`인지 RPC 또는 Explorer에서 확인한다.

### 7.3 금지 사항

- 공식 Circle USDC 대신 같은 심볼의 임의 SPL 토큰을 만들지 않는다.
- 토큰을 받기 위해 시드 문구나 개인키를 다른 지갑·스크립트에 복사하지 않는다.
- 잘못된 Account 1에 토큰을 넣어 놓고 투자자 지갑으로 간주하지 않는다.

## 8. 투자자 예치 실행

예치 전 조건:

- 앱 연결 주소가 투자자 Account 2 전체 주소와 일치한다.
- 투자자 USDC ATA에 예치 금액 이상의 Devnet USDC가 있다.
- 투자자 주소에 수수료용 Devnet SOL이 있다.
- Treasury 주소가 준비 API 응답과 이 문서의 현재 주소와 일치한다.
- 현재 코드가 `9811fb9` 또는 그 이후다.

실행 순서:

1. `http://localhost:5173/investor/setup`으로 이동한다.
2. 투자자 지갑 칸이 `99HjRok4PZoX16d7Zz88S3EW4yjTDaHXJ492GaMJHD1U`인지 확인한다.
3. 예치 금액을 입력한다. 현재 표준 데모는 20 USDC다.
4. `Devnet USDC 예치`를 누른다.
5. MetaMask 요청의 네트워크와 계정을 확인한다.
6. Mainnet 또는 Account 1이면 취소한다.
7. 승인 후 InvoiceX의 성공 링크에서 서명을 수집한다.
8. 아래 9장의 검증을 수행한다.

프런트엔드는 먼저 `POST /api/v1/investor/deposits/prepare`를 호출한다. 전송 후 `POST /api/v1/investor/deposits/confirm`을 호출하며, 백엔드는 다음을 검증한다.

- 준비된 투자자 주소가 실제 signer다.
- mint가 공식 Devnet USDC다.
- 투자자 잔액 감소량과 Treasury 잔액 증가량이 정확히 같다.
- 금액이 준비 요청과 같다.
- 트랜잭션이 confirmed/finalized 상태이며 `meta.err`가 없다.
- 동일 서명을 같은 서버 세션에서 중복 반영하지 않는다.

## 9. 온체인·백엔드 검증

### 9.1 PowerShell RPC 도우미

```powershell
function Invoke-SolanaRpc {
  param([string]$Method, [object[]]$Params)
  $body = @{
    jsonrpc = "2.0"
    id = 1
    method = $Method
    params = $Params
  } | ConvertTo-Json -Depth 12
  Invoke-RestMethod `
    -Method Post `
    -Uri "https://api.devnet.solana.com" `
    -ContentType "application/json" `
    -ErrorAction Stop `
    -Body $body
}
```

SOL 잔액:

```powershell
$address = "99HjRok4PZoX16d7Zz88S3EW4yjTDaHXJ492GaMJHD1U"
$result = Invoke-SolanaRpc "getBalance" @($address, @{ commitment = "finalized" })
$result.result.value / 1000000000
```

USDC 잔액:

```powershell
$mint = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"
$result = Invoke-SolanaRpc "getTokenAccountsByOwner" @(
  $address,
  @{ mint = $mint },
  @{ encoding = "jsonParsed"; commitment = "finalized" }
)
$balances = @(
  $result.result.value | ForEach-Object {
    [decimal]$_.account.data.parsed.info.tokenAmount.uiAmountString
  }
)
($balances | Measure-Object -Sum).Sum
```

트랜잭션 검증:

```powershell
$signature = "REPLACE_WITH_FULL_SIGNATURE"
$result = Invoke-SolanaRpc "getTransaction" @(
  $signature,
  @{
    encoding = "jsonParsed"
    commitment = "finalized"
    maxSupportedTransactionVersion = 0
  }
)
$result.result.meta.err
```

성공 조건은 결과가 `$null`이고, 투자자와 Treasury의 토큰 잔액 변화가 요청 금액과 정확히 일치하는 것이다.

백엔드 확인:

```powershell
$dashboard = Invoke-RestMethod "http://localhost:8000/api/v1/investor/dashboard"
$dashboard.latestDeposit | ConvertTo-Json -Depth 8
```

다음 값이 Explorer/RPC와 일치해야 한다.

- `investorWalletAddress`
- `treasuryWalletAddress`
- `amountUsdc`
- `signature`
- `status = CONFIRMED`
- `network = SOLANA_DEVNET`

## 10. 확인된 성공 기준점

2026-08-02 KST에 다음 실제 Devnet 예치가 검증됐다.

| 항목 | 값 |
|---|---|
| 서명 | `hBFvP1ehUq5qBowQdGnZDWk2QU8JFrycEk8jWyfdiWcT19epRFrcXxJogKnzZhV46wyXKiy6rsT6uDNk8GVB3ya` |
| Explorer | `https://explorer.solana.com/tx/hBFvP1ehUq5qBowQdGnZDWk2QU8JFrycEk8jWyfdiWcT19epRFrcXxJogKnzZhV46wyXKiy6rsT6uDNk8GVB3ya?cluster=devnet` |
| 상태 | `finalized`, `meta.err = null` |
| 수수료 | `5,049 lamports` |
| 투자자 전 | `10 SOL`, `20 USDC` |
| 투자자 후 | `9.999994951 SOL`, `0 USDC` |
| Treasury 전 | `20 USDC` |
| Treasury 후 | `40 USDC` |
| 백엔드 reference | `DEP-2026-006` |
| 백엔드 상태 | `CONFIRMED` |
| 백엔드 논리 가용액 | `20 USDC` |

이 표는 성공 사례이지 현재 잔액을 보장하는 설정값이 아니다. 새 작업에서는 항상 RPC로 다시 조회한다.

## 11. 오류 대응표

| 증상 | 원인 | 조치 |
|---|---|---|
| 투자자 화면 주소가 `HviSY...6iV9` | 사이트 연결이 Account 1에 고정 | MetaMask `localhost:5173` 권한에서 Account 1을 제거하고 Account 2 허용 후 재연결 |
| MetaMask 상단은 Account 2인데 앱은 Account 1 | 전역 선택과 사이트 허용 계정이 다름 | 상단 계정만 바꾸지 말고 사이트 연결 관리까지 변경 |
| 서명창에 `Solana Mainnet` 및 simulation reverted | `signTransaction` 직접 호출 또는 오래된 프런트엔드, 잘못된 계정 | 취소 후 `9811fb9` 포함 여부와 HMR/새로고침 확인, Account 2 재연결 |
| 앱에서 `Devnet USDC가 없습니다` | 연결 주소의 공식 USDC ATA가 없거나 잘못된 계정 | 전체 주소와 mint 확인 후 Circle Faucet 사용 |
| `insufficient Devnet USDC` | 예치 금액보다 잔액이 적음 | 잔액 이하로 조정하거나 Faucet 제한 해제 후 보충 |
| Solana RPC 429 | 공용 에어드롭 제한 또는 Faucet 고갈 | 반복 요청 중단, 공식 안내의 다른 방법 또는 사용자 웹 Faucet 사용 |
| Faucet `2 airdrops limit` | 최근 8시간 요청 횟수 소진 | 온체인 잔액부터 확인하고 이미 입금됐으면 재요청하지 않음 |
| MetaMask `Unable to connect to Hardhat` | EVM 로컬 RPC가 꺼짐 | Solana 거래에는 무관. EVM 기능을 쓰지 않으면 무시 |
| `불러오는 중`에서 멈춤 | API 미실행, CORS origin 불일치, `localhost`/`127.0.0.1` 혼용 | 5173·8000 확인, 브라우저와 `FRONTEND_ORIGIN`을 `localhost`로 통일 |
| `/health`가 404 | 해당 라우트가 없음 | `/api/docs` 또는 실제 `/api/v1` 경로로 확인 |
| Treasury RPC 40인데 대시보드 20 | 대시보드는 세션 논리 예치만 집계 | 실제 잔액은 RPC를 기준으로 하고 차이를 문서화 |
| 서버 재시작 후 최신 예치가 사라짐 | 예치·인보이스 상태가 인메모리 | 온체인 자산은 남는다. DB/체인 재동기화 전에는 서버를 데모 중 재시작하지 않음 |
| 성공 화면은 떴지만 RPC `meta.err`가 존재 | 체인 실패 또는 잘못된 서명 조회 | 완료 처리 금지, 전체 서명과 cluster를 다시 확인 |
| Privy 지급 502 | 설정 누락, 공급자/RPC 실패, 잘못된 주소 | 비밀값은 노출하지 말고 `missing_privy_*_configuration`과 서버 로그 확인 |

## 12. 재시작과 반복 데모 주의사항

- 백엔드 재시작 시 `_available_vault_usdc`, 예치 준비, 사용 서명, 최신 예치와 인보이스 상태가 초기화된다.
- Solana 온체인 Treasury 잔액은 초기화되지 않는다.
- 현재는 온체인 Treasury 잔액을 백엔드 논리 잔액으로 재동기화하는 엔드포인트가 없다.
- Account 2의 20 USDC를 모두 예치한 후에는 투자자 잔액이 0이다. 같은 예치를 반복하려면 Circle Faucet 제한을 기다리거나 별도의 적법한 Devnet 자금 공급 절차가 필요하다.
- 현재 실제 조기정산 전송은 Devnet에서 1 USDC로 제한된다. UI의 18,800 USDC를 실제로 전송한다고 오해하지 않는다.
- DB 영속화 작업은 별도 과제다. 이 문서만으로 인메모리 저장 문제를 해결했다고 보고하지 않는다.

## 13. AI 완료 보고 체크리스트

AI는 아래 항목을 모두 충족한 경우에만 완료라고 보고한다.

- [ ] `work` 기준과 기존 변경 보존 여부를 확인했다.
- [ ] 공급기업과 투자자 전체 Solana 주소가 서로 다르다.
- [ ] 앱 투자자 주소가 MetaMask 사이트 연결 Account 2와 일치한다.
- [ ] RPC에서 투자자의 SOL과 공식 Devnet USDC 잔액을 확인했다.
- [ ] 서명창이 Devnet 컨텍스트이며 Mainnet 경고가 없다.
- [ ] 전송 서명을 수집했다.
- [ ] RPC `getTransaction`에서 거래를 찾았고 `meta.err = null`이다.
- [ ] 투자자 감소량과 Treasury 증가량이 예치 금액과 같다.
- [ ] 백엔드 `latestDeposit`의 주소·금액·서명·상태가 RPC와 같다.
- [ ] 실제/목업 경계를 결과에 명시했다.
- [ ] 테스트·린트·타입 검사·빌드 결과를 확인했다.
- [ ] 필요한 파일만 커밋·푸시했다.

## 14. 공식 참고 자료

- Circle USDC contract addresses: <https://developers.circle.com/stablecoins/usdc-contract-addresses>
- Circle Testnet Faucet: <https://faucet.circle.com/?allow=true>
- Circle Solana Devnet USDC transfer quickstart: <https://developers.circle.com/stablecoins/quickstart-transfer-10-usdc-on-solana>
- Solana Devnet Faucet: <https://faucet.solana.com/>
- Solana Faucet guide: <https://solana.com/developers/guides/getstarted/solana-token-airdrop-and-faucets>
- MetaMask Solana navigation: <https://support.metamask.io/configure/networks/navigating-solana>
