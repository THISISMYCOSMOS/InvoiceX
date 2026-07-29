# InvoiceX Wallet Backend

InvoiceX의 지갑 API와 Solana 네트워크 연결을 담당할 백엔드 경계다.

현재 단계에서는 폴더와 환경변수 계약만 정의한다. Privy API 클라이언트, 잔액 조회,
트랜잭션 서명·전송 코드는 와이어프레임과 코어 정책이 확정된 뒤 구현한다.

## 범위

- Privy 서버 지갑 조회
- Solana Testnet 주소·잔액 조회
- 코어 승인 결과에 따른 트랜잭션 서명 요청
- 멱등성 키를 적용한 트랜잭션 전송
- 외부 API 오류와 타임아웃 처리

## 책임 경계

- Core는 금액, 수취인, 한도, 상태 전이를 검증하고 승인한다.
- Backend는 승인된 요청만 Privy와 Solana RPC에 전달한다.
- Agent는 직접 지갑을 제어하거나 자금을 이동하지 않는다.

## 보안

- App Secret, Wallet ID, 개인키, 시드 문구를 Git에 저장하지 않는다.
- 로컬에서는 `.env`, 배포 환경에서는 Secret Manager를 사용한다.
- 운영 전 지갑 Owner, Authorization Key, 전송 한도, 수취인 허용 목록을 설정한다.

필요한 설정 키는 [`.env.example`](.env.example)에 정의되어 있다.
