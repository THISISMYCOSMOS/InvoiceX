# InvoiceX Firebase 통합 인수인계

> 작업 지침: 작업을 시작하기 전에 이 문서를 끝까지 읽고, 현재 저장소 상태와 Firebase 프로젝트 상태를 다시 확인한다. 문서에 적힌 과거 상태를 현재 상태로 가정하지 않는다.

## 1. 문서 목적

이 문서는 InvoiceX의 현재 인메모리·로컬 파일 저장 방식을 Firebase로 이전할 팀원을 위한 인수인계 문서다. 최신 `work` 브랜치의 Solana Devnet, Privy, Gemini, 투자자 예치 흐름을 보존하면서 기존 Firebase 작업물을 통합하는 것이 목표다.

## 2. 현재 상태

- 최신 제품 코드는 `work` 브랜치에 있다.
- 백엔드의 인보이스·투자자 상태는 Python 프로세스 메모리에 있어 서버를 재시작하면 초기화된다.
- 업로드 문서는 로컬 `uploads/` 디렉터리에 저장된다.
- 1차 Firebase 구현은 `feat-backend` 브랜치의 커밋 `826113c`에 보존돼 있다.
- `826113c`는 현재 `work`에 병합되지 않았다.
- Firebase Console 프로젝트는 생성돼 있다.

| 구분 | 값 |
|---|---|
| Firebase project ID | `invoicex-1d99e` |
| Firestore database | `(default)` |
| Collection prefix | `invoicex` |
| 예상 Storage bucket | `invoicex-1d99e.firebasestorage.app` |

Storage bucket 이름은 현재 Firebase 기본 규칙을 기준으로 한 예상값이다. Storage를 초기화한 뒤 Firebase Console에서 실제 bucket 이름을 반드시 확인한다.

## 3. 작업 전 중단 조건

다음 상황에서는 통합을 시작하지 말고 기존 작업자에게 상태를 공유한다.

- `work`에 merge, rebase, cherry-pick 중인 상태가 남아 있다.
- unmerged 파일이 있다.
- 다른 사용자의 미커밋 변경과 Firebase 수정 대상이 겹친다.
- Firebase 초기화 과정에서 지역 선택, 결제 업그레이드 또는 권한 변경을 요구한다.
- 실제 Firestore 문서 작성, Storage 업로드 또는 Rules 배포가 필요하지만 프로젝트 소유자의 확인을 받지 않았다.

`.data/`, `CLAUDE.md`, `.env` 및 다른 사용자의 미추적·미커밋 파일은 수정하거나 staging하지 않는다.

## 4. 재사용할 기존 Firebase 작업물

최신 브랜치를 수정하기 전에 다음 명령으로 기존 구현을 검토한다.

```powershell
git show --stat 826113c
git show 826113c -- backend/src/invoicex_backend/firebase.py
git show 826113c -- backend/src/invoicex_backend/repository.py
git show 826113c -- backend/src/invoicex_backend/storage.py
git show 826113c -- backend/tests/test_firebase_adapters.py
```

커밋 `826113c`에는 다음 내용이 이미 있다.

- Application Default Credentials를 사용하는 Firebase Admin SDK 초기화
- 인보이스, 문서 분석, 검증 상태를 위한 Firestore repository
- Firebase Storage 업로드·다운로드 adapter
- 비공개 문서를 전달하는 백엔드 streaming route
- `FIREBASE_MODE=auto|firebase|local` 설정
- 로컬 인메모리·파일 저장 fallback
- 클라이언트 직접 접근을 차단하는 Firestore·Storage Rules
- Firebase adapter 및 설정 테스트
- `firebase.json`, Firestore indexes, Rules 파일

검토 결과 구체적인 문제가 없다면 이 부분을 처음부터 다시 구현하지 않는다.

## 5. 권장 통합 순서

1. 현재 브랜치와 작업 트리를 확인한다.

```powershell
git branch --show-current
git status --short
git log -3 --oneline
```

2. 작업 트리가 안전한 경우에만 최신 `work`에서 기능 브랜치를 만든다.

```powershell
git switch work
git pull --ff-only
git switch -c feat/firebase-persistence
```

3. 보존된 Firebase 커밋을 적용한다.

```powershell
git cherry-pick 826113c
```

다음 파일은 충돌이 예상된다.

- `README.md`
- `backend/src/invoicex_backend/service.py`
- `backend/uv.lock`

충돌 해결 기준:

1. `work`의 최신 Solana Devnet, Privy, 투자자 예치 동작을 보존한다.
2. 기존 지갑 런북을 제거하지 말고 Firebase 안내를 추가한다.
3. `InvoiceService`의 최신 필드와 `826113c`의 repository 초기화·저장 호출을 함께 유지한다.
4. `backend/uv.lock`은 dependency block을 손으로 합치지 말고 `uv lock`으로 재생성한다.
5. 충돌 표시만 제거하고 끝내지 말고 전체 diff를 다시 검토한다.

## 6. 커밋 826113c 이후에 반드시 보완할 부분

보존된 커밋은 최신 투자자 예치·Vault 흐름이 추가되기 전에 작성됐다. 현재 repository가 저장하는 대상은 다음 세 가지뿐이다.

- invoices
- document analyses
- verifications

최종 구현은 다음 투자자 상태도 저장·복원해야 한다.

- 투자자 지갑 주소
- Treasury/Vault 주소
- 예치 준비 내역
- 확정된 예치 내역
- 이미 반영한 트랜잭션 서명
- 최신 확정 예치
- 사용 가능한 Vault USDC 잔액
- 펀딩 예약 상태
- 투자자 예치 ID sequence

완료 기준:

- API를 재시작해도 투자자 대시보드가 초기화되지 않는다.
- 서버 재시작 후에도 같은 Solana 서명을 두 번 입금 처리하지 않는다.
- 예치 준비 후 서버를 재시작해도 해당 예치를 확정할 수 있다.
- 펀딩 예약·해제 후 Vault 잔액이 재시작 전후에 달라지지 않는다.
- 복원한 invoice, document, verification, trace, deposit ID와 새 ID가 충돌하지 않는다.

투자자 runtime state를 하나의 Firestore 문서로 저장하거나 전용 collection으로 분리해도 된다. 잔액, 예약, 예치, 사용한 서명이 함께 변경되는 경로는 transaction 또는 batch로 원자성을 보장하고 테스트로 입증한다.

현재 설계는 Firestore snapshot을 메모리에 복원한 뒤 사용한다. 다중 worker 간 상태 동기화를 추가로 구현하지 않는다면 백엔드를 single-process로 운영한다는 제약을 문서화한다.

## 7. Storage 및 보안 기준

Firebase Storage object는 다음 private 경로를 사용한다.

```text
invoices/{invoice_id}/{document_id}.{extension}
```

문서는 다음 백엔드 API를 통해 전달한다.

```text
GET /uploads/{invoice_id}/{document_id}
```

보안 기준:

- 공개 URL 또는 장기 signed URL을 노출하지 않는다.
- `Content-Disposition`에 사용할 원본 파일명을 정규화한다.
- path traversal과 허용하지 않은 MIME/확장자 조합을 차단한다.
- 민감한 증빙 문서에 `Cache-Control: private, no-store`를 유지한다.
- Firestore와 Storage에 대한 클라이언트 직접 접근을 기본 차단한다.
- Firebase Admin 권한을 가진 FastAPI 백엔드를 현재 MVP의 trust boundary로 사용한다.

사용자용 Firebase Authentication은 이 인수인계 범위가 아니다. 임시 헤더를 신원 인증 대체수단으로 추가하지 않는다.

## 8. 프로젝트 소유자가 직접 진행할 인증

구현과 fake/local 테스트는 Firebase 인증 없이 진행한다. 실제 Firebase 확인이 필요해지면 작업을 중단하고 프로젝트 소유자에게 다음 로그인을 요청한다.

Firebase Admin SDK 런타임 인증:

```powershell
gcloud auth application-default login
gcloud auth application-default set-quota-project invoicex-1d99e
```

Rules·Indexes 배포 인증:

```powershell
firebase login
firebase use --add
```

`firebase use --add`에서 `invoicex-1d99e` 프로젝트를 선택하고 alias는 `default`를 사용한다. alias 없이 1회 배포할 때는 다음과 같이 프로젝트를 명시한다.

```powershell
firebase deploy --project invoicex-1d99e --only firestore:rules,firestore:indexes,storage
```

프로젝트 소유자에게 token, password, OTP, 서비스 계정 JSON을 채팅에 붙여 넣으라고 요청하지 않는다. 로컬 개발은 ADC를 사용하고 인증 파일을 저장소에 커밋하지 않는다.

Firestore와 Storage가 Firebase Console에서 아직 초기화되지 않았을 수 있다. 지역 선택은 되돌리기 어려우므로 팀원이 임의로 선택하지 말고 프로젝트 소유자에게 확인한다. 결제 업그레이드가 표시되면 승인 전에 중단한다.

## 9. 환경 설정

`backend/.env.example`에는 비밀값이 아닌 다음 Firebase 설정을 추가한다.

```dotenv
FIREBASE_MODE=auto
FIREBASE_PROJECT_ID=
FIREBASE_STORAGE_BUCKET=
FIREBASE_FIRESTORE_DATABASE=(default)
FIREBASE_COLLECTION_PREFIX=invoicex
FIREBASE_APP_NAME=invoicex-backend
```

개발자가 실제 Firebase를 사용할 때는 기존 Gemini, Privy, Solana 설정을 보존하고 git에서 ignore된 로컬 환경 파일에 다음을 추가한다.

```dotenv
FIREBASE_MODE=firebase
FIREBASE_PROJECT_ID=invoicex-1d99e
FIREBASE_STORAGE_BUCKET=invoicex-1d99e.firebasestorage.app
FIREBASE_FIRESTORE_DATABASE=(default)
FIREBASE_COLLECTION_PREFIX=invoicex
```

디버깅 과정에서 `.env` 전체 내용을 출력하지 않는다.

## 10. 필수 검증

실제 인증을 요청하기 전에 로컬·결정적 테스트를 먼저 완료한다.

```powershell
cd backend
uv lock
uv sync --all-groups
uv run ruff check src tests scripts
uv run pytest
uv run python scripts/stress_api.py --iterations 500 --concurrency 25
```

최소 테스트 범위:

- Firebase project ID가 없으면 local mode가 선택된다.
- project ID 없이 Firebase mode를 명시하면 startup이 즉시 실패한다.
- Firestore에 저장한 모든 상태가 동일하게 복원된다.
- API 재시작 후 invoice와 투자자 상태가 유지된다.
- 재시작 후에도 중복 예치 서명이 차단된다.
- Firebase Storage가 private object 경로를 사용한다.
- Storage를 직접 노출하지 않고 백엔드가 문서를 전달한다.
- 기존 API contract, Solana, 투자자 예치 테스트가 모두 통과한다.

프로젝트 소유자가 ADC 인증을 완료하면 읽기 전용 startup 확인을 먼저 수행한다. Rules 배포, 테스트 문서 작성, Storage 업로드, Firebase 프로젝트 설정 변경은 프로젝트 소유자의 확인 후 진행한다.

## 11. 최종 리뷰 체크리스트

커밋 전에 다음을 모두 확인한다.

- 충돌 해결 파일만이 아니라 전체 diff를 검토했다.
- conflict marker가 남아 있지 않다.
- `git diff --check`가 통과한다.
- `.env`, JSON credential, token, private key가 staging되지 않았다.
- Firestore 실패를 메모리 mode로 묵시하고 fallback하지 않는다.
- persistence 실패 전에 API가 성공을 응답하지 않는다.
- Firebase client가 app shutdown에서 정상적으로 정리된다.
- 문서가 UTF-8이며 개인 로컬 경로·계정 정보가 없다.
- single-process 제약 및 아직 배포하지 않은 범위를 정확히 문서화했다.

권장 커밋 메시지:

```text
feat(backend): Firebase 영속 저장소를 최신 결제 흐름에 통합
```

## 12. 완료 조건

다음이 모두 충족돼야 Firebase 통합 완료로 보고한다.

1. Firebase persistence가 최신 `work` 동작과 통합됐다.
2. 모든 invoice·투자자 상태가 API 재시작 후에도 유지된다.
3. 업로드 증빙이 Firebase Storage에 private으로 저장되고 백엔드를 통해 제공된다.
4. local mode와 기존 테스트가 깨지지 않았다.
5. `backend/README.md`와 `backend/.env.example`에 팀원을 위한 설정·인증·문제 해결 안내가 반영됐다.
6. lint, 전체 테스트, stress 검증이 통과했다.
7. 인증 없이 통과한 검증과 실제 Firebase에서 통과한 검증을 구분해 보고했다.
8. credential과 관계없는 workspace 파일이 커밋에 포함되지 않았다.
