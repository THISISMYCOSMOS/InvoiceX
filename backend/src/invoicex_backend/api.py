"""FastAPI routes implementing the frontend API contract."""

from __future__ import annotations

import time
from typing import Annotated, cast

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)

from invoicex_backend.agent_activity import AgentActivityTimeline, AgentTrigger
from invoicex_backend.auth import (
    AuthenticatedIdentity,
    issue_access_token,
    require_authenticated_identity,
    require_roles,
)
from invoicex_backend.config import BackendSettings
from invoicex_backend.errors import DocumentValidationError, NotFoundError, OnboardingApiError
from invoicex_backend.models import (
    ConfirmVaultDepositRequest,
    CreateMandateRequest,
    DocumentType,
    ErrorResponse,
    InvestmentCriteriaBuyer,
    InvestorDashboard,
    InvestorMandate,
    InvoiceListResponse,
    InvoiceResponse,
    LoginRequest,
    LoginResponse,
    LoginRole,
    MandateSigningPayload,
    OfferResponseRequest,
    PrepareMandateRequest,
    PrepareVaultDepositRequest,
    SaveSupplierWalletRequest,
    SponsorVaultDepositRequest,
    UploadedDocument,
    VaultBalance,
    VaultDepositPreparation,
    VerificationListResponse,
    VerificationResponse,
)
from invoicex_backend.onboarding import OnboardingService
from invoicex_backend.onboarding_models import (
    AuthMeResponse,
    DeleteAccountResponse,
    LinkEmbeddedWalletRequest,
    OnboardCompanyRequest,
    OnboardingResponse,
    OnboardingStatus,
    SettlementWallet,
    UpdateCompanyProfileRequest,
    UpdateSettlementWalletRequest,
)
from invoicex_backend.privy_auth import PrivyPrincipalDependency, verify_privy_access_token
from invoicex_backend.seed import INVESTMENT_CRITERIA_BUYERS, authenticate_demo_account
from invoicex_backend.service import InvoiceService
from invoicex_backend.tasks import AgentTaskDispatcher, verify_cloud_tasks_oidc

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
onboarding_router = APIRouter(prefix="/api/v1/onboarding", tags=["Authentication"])
router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_authenticated_identity)],
)
internal_router = APIRouter(prefix="/internal")

supplier_only = Depends(require_roles(LoginRole.SUPPLIER))
buyer_only = Depends(require_roles(LoginRole.BUYER))
investor_only = Depends(require_roles(LoginRole.INVESTOR))
invoice_reader = Depends(require_roles(LoginRole.SUPPLIER, LoginRole.BUYER, LoginRole.INVESTOR))


def documented_errors(*status_codes: int) -> dict[int, dict[str, object]]:
    descriptions = {
        400: "Document or domain validation failed",
        403: "The authenticated demo account is not permitted to perform this action",
        404: "Invoice or Verification was not found",
        409: "The requested state transition is not allowed",
        422: "The request does not match the API contract",
        502: "Gemini, Privy, or Solana integration failed",
    }
    return {
        code: {"model": ErrorResponse, "description": descriptions[code]} for code in status_codes
    }


def get_invoice_service(request: Request) -> InvoiceService:
    return cast(InvoiceService, request.app.state.invoice_service)


InvoiceServiceDependency = Annotated[InvoiceService, Depends(get_invoice_service)]


def get_agent_task_dispatcher(request: Request) -> AgentTaskDispatcher:
    return cast(AgentTaskDispatcher, request.app.state.agent_task_dispatcher)


AgentTaskDispatcherDependency = Annotated[
    AgentTaskDispatcher, Depends(get_agent_task_dispatcher)
]


def get_settings(request: Request) -> BackendSettings:
    return cast(BackendSettings, request.app.state.settings)


SettingsDependency = Annotated[BackendSettings, Depends(get_settings)]


def get_onboarding_service(request: Request) -> OnboardingService:
    return cast(OnboardingService, request.app.state.onboarding_service)


OnboardingServiceDependency = Annotated[OnboardingService, Depends(get_onboarding_service)]
InvoiceFile = Annotated[
    UploadFile,
    File(
        alias="INVOICE",
        description="Invoice PDF/JPG/JPEG/PNG (maximum 20MB)",
    ),
]
ContractFile = Annotated[
    UploadFile,
    File(
        alias="CONTRACT",
        description="Supply contract PDF/JPG/JPEG/PNG (maximum 20MB)",
    ),
]
PurchaseOrderFile = Annotated[
    UploadFile,
    File(
        alias="PURCHASE_ORDER",
        description="Purchase order PDF/JPG/JPEG/PNG (maximum 20MB)",
    ),
]
DeliveryProofFile = Annotated[
    UploadFile,
    File(
        alias="DELIVERY_PROOF",
        description="Delivery evidence PDF/JPG/JPEG/PNG (maximum 20MB)",
    ),
]
InvoiceId = Annotated[
    str,
    Path(alias="invoiceId", description="Invoice aggregate ID", examples=["INV-2026-001"]),
]
VerificationId = Annotated[
    str,
    Path(
        alias="verificationId",
        description="Buyer verification ID",
        examples=["VER-2026-001"],
    ),
]


@auth_router.post(
    "/login",
    response_model=LoginResponse,
    responses={401: {"model": ErrorResponse, "description": "Invalid account credentials"}},
    summary="이메일과 비밀번호 로그인",
)
async def login(
    payload: LoginRequest,
    settings: SettingsDependency,
    service: OnboardingServiceDependency,
) -> LoginResponse:
    member = service.authenticate_password_login(payload.email, payload.password, payload.role)
    if member is not None:
        identity = AuthenticatedIdentity(
            role=payload.role,
            email=member.email,
            source="MEMBER",
        )
        access_token, expires_at = issue_access_token(identity, settings)
        return LoginResponse(
            access_token=access_token,
            auth_mode="MEMBER",
            role=payload.role,
            email=member.email,
            expires_at=expires_at,
        )

    account = authenticate_demo_account(payload.role, payload.email, payload.password)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid demo credentials.",
        )
    identity = AuthenticatedIdentity(role=account.role, email=account.email)
    access_token, expires_at = issue_access_token(identity, settings)
    return LoginResponse(
        access_token=access_token,
        auth_mode="DEMO",
        role=account.role,
        email=account.email,
        expires_at=expires_at,
    )


@auth_router.get("/otp-clock", include_in_schema=False)
async def otp_clock(response: Response, settings: SettingsDependency) -> dict[str, int]:
    """Return the server clock and configured OTP countdown window without caching."""

    response.headers["Cache-Control"] = "no-store"
    return {
        "serverTimeMs": int(time.time() * 1000),
        "expiresInSeconds": settings.privy_otp_display_ttl_seconds,
    }


@auth_router.get(
    "/me",
    response_model=AuthMeResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Privy token is invalid"},
        502: {"model": ErrorResponse, "description": "Privy user lookup failed"},
    },
    summary="Privy 사용자 가입 상태 조회",
)
async def auth_me(
    request: Request,
    settings: SettingsDependency,
    service: OnboardingServiceDependency,
) -> AuthMeResponse:
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise OnboardingApiError(
            status.HTTP_401_UNAUTHORIZED,
            "PRIVY_TOKEN_INVALID",
            "인증 토큰이 필요합니다.",
        )
    if token.count(".") == 2:
        return await service.auth_me(verify_privy_access_token(token, settings))
    identity = await require_authenticated_identity(request)
    if identity is None:
        raise OnboardingApiError(
            status.HTTP_401_UNAUTHORIZED,
            "AUTHENTICATION_REQUIRED",
            "인증 토큰을 확인할 수 없습니다.",
        )
    return service.auth_me_for_email(identity.email)


async def _completed_member_email(
    request: Request,
    settings: BackendSettings,
    service: OnboardingService,
) -> str:
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise OnboardingApiError(
            status.HTTP_401_UNAUTHORIZED,
            "AUTHENTICATION_REQUIRED",
            "인증 토큰이 필요합니다.",
        )
    if token.count(".") == 2:
        profile = await service.auth_me(verify_privy_access_token(token, settings))
        if profile.onboarding_status is not OnboardingStatus.COMPLETED:
            raise OnboardingApiError(
                status.HTTP_403_FORBIDDEN,
                "ONBOARDING_INCOMPLETE",
                "회원가입을 완료한 후 이용할 수 있습니다.",
            )
        return profile.user.email
    identity = await require_authenticated_identity(request)
    if identity is None:
        raise OnboardingApiError(
            status.HTTP_401_UNAUTHORIZED,
            "AUTHENTICATION_REQUIRED",
            "인증 토큰을 확인할 수 없습니다.",
        )
    return identity.email


@auth_router.get(
    "/settlement-wallet",
    response_model=SettlementWallet,
    summary="현재 조기정산 지갑 조회",
)
async def get_settlement_wallet(
    request: Request,
    settings: SettingsDependency,
    service: OnboardingServiceDependency,
) -> SettlementWallet:
    email = await _completed_member_email(request, settings, service)
    return service.settlement_wallet_for_email(email)


@auth_router.put(
    "/settlement-wallet",
    response_model=SettlementWallet,
    summary="조기정산에 사용할 지갑 변경",
)
async def update_settlement_wallet(
    payload: UpdateSettlementWalletRequest,
    request: Request,
    settings: SettingsDependency,
    service: OnboardingServiceDependency,
) -> SettlementWallet:
    email = await _completed_member_email(request, settings, service)
    return service.update_settlement_wallet(email, payload)


@auth_router.put(
    "/company-profile",
    response_model=AuthMeResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication is required"},
        409: {"model": ErrorResponse, "description": "Company profile conflict"},
        422: {"model": ErrorResponse, "description": "Invalid company profile"},
    },
    summary="데모용 기업 프로필 수정",
)
async def update_company_profile(
    payload: UpdateCompanyProfileRequest,
    request: Request,
    settings: SettingsDependency,
    service: OnboardingServiceDependency,
) -> AuthMeResponse:
    email = await _completed_member_email(request, settings, service)
    return service.update_company_profile(email, payload)


@auth_router.put(
    "/embedded-wallet",
    response_model=AuthMeResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Privy token is invalid"},
        409: {"model": ErrorResponse, "description": "Wallet ownership conflict"},
        422: {"model": ErrorResponse, "description": "Invalid Solana wallet"},
        502: {"model": ErrorResponse, "description": "Privy wallet lookup failed"},
    },
    summary="브라우저에서 생성한 Embedded Wallet 연결",
)
async def link_embedded_wallet(
    payload: LinkEmbeddedWalletRequest,
    principal: PrivyPrincipalDependency,
    service: OnboardingServiceDependency,
) -> AuthMeResponse:
    return await service.link_embedded_wallet(principal, payload)


@auth_router.delete(
    "/account",
    response_model=DeleteAccountResponse,
    summary="InvoiceX 계정 탈퇴",
)
async def withdraw_account(
    request: Request,
    settings: SettingsDependency,
    service: OnboardingServiceDependency,
) -> DeleteAccountResponse:
    email = await _completed_member_email(request, settings, service)
    return await service.withdraw_account_for_email(email)


@onboarding_router.post(
    "/company",
    response_model=OnboardingResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Privy token is invalid"},
        409: {"model": ErrorResponse, "description": "Onboarding uniqueness conflict"},
        422: {"model": ErrorResponse, "description": "Invalid company profile"},
        502: {"model": ErrorResponse, "description": "Wallet provisioning failed"},
    },
    summary="기업 등록과 사용자 소유 Embedded Wallet 생성",
)
async def onboard_company(
    payload: OnboardCompanyRequest,
    principal: PrivyPrincipalDependency,
    service: OnboardingServiceDependency,
) -> OnboardingResponse:
    return await service.onboard_company(principal, payload)


@router.get(
    "/reference/investment-criteria/buyers",
    response_model=list[InvestmentCriteriaBuyer],
    tags=["Investor"],
    summary="투자 조건용 목업 구매기업 목록",
    dependencies=[investor_only],
)
async def list_investment_criteria_buyers() -> list[InvestmentCriteriaBuyer]:
    return list(INVESTMENT_CRITERIA_BUYERS)


@router.post(
    "/invoices",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    responses=documented_errors(403, 400, 422, 502),
    tags=["Invoices"],
    summary="문서 등록 및 Gemini 분석",
)
async def create_invoice(
    invoice_file: InvoiceFile,
    contract_file: ContractFile,
    purchase_order_file: PurchaseOrderFile,
    delivery_proof_file: DeliveryProofFile,
    service: InvoiceServiceDependency,
    dispatcher: AgentTaskDispatcherDependency,
    identity: AuthenticatedIdentity | None = supplier_only,
) -> InvoiceResponse:
    """Accept the four exact multipart fields defined by the frontend contract."""

    max_bytes = service.settings.max_document_size_bytes
    uploads = [
        await _read_upload(invoice_file, DocumentType.INVOICE, max_bytes),
        await _read_upload(contract_file, DocumentType.CONTRACT, max_bytes),
        await _read_upload(
            purchase_order_file,
            DocumentType.PURCHASE_ORDER,
            max_bytes,
        ),
        await _read_upload(
            delivery_proof_file,
            DocumentType.DELIVERY_PROOF,
            max_bytes,
        ),
    ]
    invoice = await service.create_invoice(uploads, identity)
    await dispatcher.enqueue(invoice.id, AgentTrigger.INVOICE_CREATED)
    return InvoiceResponse(invoice=service.get_invoice(invoice.id, identity))


@internal_router.post("/agent-tasks", include_in_schema=False)
async def run_agent_task(
    payload: dict[str, str],
    request: Request,
    settings: SettingsDependency,
    service: InvoiceServiceDependency,
) -> dict[str, str]:
    if (
        settings.agent_task_dispatcher != "cloud_tasks"
        or not settings.cloud_run_task_audience
        or not settings.cloud_tasks_service_account_email
        or not verify_cloud_tasks_oidc(
            request.headers.get("Authorization"),
            audience=settings.cloud_run_task_audience,
            expected_email=settings.cloud_tasks_service_account_email,
        )
    ):
        raise HTTPException(status_code=403, detail="Cloud Tasks caller is not authorized.")
    try:
        invoice_id = payload["invoiceId"]
        trigger = AgentTrigger(payload["trigger"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid Agent task payload.") from exc
    await service.run_agent_task(invoice_id, trigger)
    return {"status": "completed"}


@router.get(
    "/invoices",
    response_model=InvoiceListResponse,
    tags=["Invoices"],
    summary="역할별 Invoice 목록",
)
async def list_invoices(
    service: InvoiceServiceDependency,
    identity: AuthenticatedIdentity | None = invoice_reader,
) -> InvoiceListResponse:
    return InvoiceListResponse(items=service.list_invoices(identity))


@router.get(
    "/invoices/{invoiceId}",
    response_model=InvoiceResponse,
    responses=documented_errors(403, 404),
    tags=["Invoices"],
    summary="Invoice 통합 상세",
)
async def get_invoice(
    invoice_id: InvoiceId,
    service: InvoiceServiceDependency,
    identity: AuthenticatedIdentity | None = invoice_reader,
) -> InvoiceResponse:
    return InvoiceResponse(invoice=service.get_invoice(invoice_id, identity))


@router.get(
    "/invoices/{invoiceId}/agent-activity",
    response_model=AgentActivityTimeline,
    responses=documented_errors(403, 404),
    tags=["Invoices"],
    summary="역할별 Agent Activity 타임라인",
)
async def get_agent_activity(
    invoice_id: InvoiceId,
    service: InvoiceServiceDependency,
    viewer_role: LoginRole = Query(default=LoginRole.SUPPLIER, alias="viewerRole"),
    identity: AuthenticatedIdentity | None = invoice_reader,
) -> AgentActivityTimeline:
    # The request parameter is only a local-demo fallback. Authenticated users
    # are always rendered from their signed role, preventing Investor detail
    # from being selected by a Supplier query parameter.
    role = identity.role if identity is not None else viewer_role
    if role not in {LoginRole.SUPPLIER, LoginRole.INVESTOR}:
        raise HTTPException(status_code=403, detail="Buyer does not have an Agent Activity view.")
    service.get_invoice(invoice_id, identity)
    return service.get_agent_activity(invoice_id, role=role.value)  # type: ignore[arg-type]


@router.post(
    "/invoices/{invoiceId}/verification-request",
    response_model=InvoiceResponse,
    responses=documented_errors(403, 404, 409),
    tags=["Verifications"],
    summary="Buyer 검증 요청 생성",
)
async def request_verification(
    invoice_id: InvoiceId,
    service: InvoiceServiceDependency,
    identity: AuthenticatedIdentity | None = supplier_only,
) -> InvoiceResponse:
    return InvoiceResponse(invoice=await service.request_verification(invoice_id, identity))


@router.get(
    "/verifications",
    response_model=VerificationListResponse,
    tags=["Verifications"],
    summary="Buyer 검증 목록",
)
async def list_verifications(
    service: InvoiceServiceDependency,
    identity: AuthenticatedIdentity | None = buyer_only,
) -> VerificationListResponse:
    return VerificationListResponse(items=service.list_verifications(identity))


@router.get(
    "/verifications/{verificationId}",
    response_model=VerificationResponse,
    responses=documented_errors(403, 404),
    tags=["Verifications"],
    summary="Buyer 검증 상세",
)
async def get_verification(
    verification_id: VerificationId,
    service: InvoiceServiceDependency,
    identity: AuthenticatedIdentity | None = buyer_only,
) -> VerificationResponse:
    return VerificationResponse(verification=service.get_verification(verification_id, identity))


@router.post(
    "/verifications/{verificationId}/confirm",
    response_model=InvoiceResponse,
    responses=documented_errors(403, 404, 409, 502),
    tags=["Verifications"],
    summary="Buyer 검증 확정 및 Risk Passport 생성",
)
async def confirm_verification(
    verification_id: VerificationId,
    service: InvoiceServiceDependency,
    identity: AuthenticatedIdentity | None = buyer_only,
) -> InvoiceResponse:
    return InvoiceResponse(invoice=await service.confirm_verification(verification_id, identity))


@router.post(
    "/invoices/{invoiceId}/risk-review-request",
    response_model=InvoiceResponse,
    responses=documented_errors(403, 404, 409),
    tags=["Risk"],
    summary="Supplier Risk Score 이의 신청",
)
async def request_risk_review(
    invoice_id: InvoiceId,
    service: InvoiceServiceDependency,
    identity: AuthenticatedIdentity | None = supplier_only,
) -> InvoiceResponse:
    return InvoiceResponse(invoice=await service.request_risk_review(invoice_id, identity))


@router.post(
    "/invoices/{invoiceId}/offer-response",
    response_model=InvoiceResponse,
    responses=documented_errors(403, 404, 409, 422),
    tags=["Funding"],
    summary="Supplier 조기정산 조건 응답",
)
async def respond_to_offer(
    invoice_id: InvoiceId,
    payload: OfferResponseRequest,
    background_tasks: BackgroundTasks,
    service: InvoiceServiceDependency,
    identity: AuthenticatedIdentity | None = supplier_only,
) -> InvoiceResponse:
    invoice, should_schedule = await service.respond_to_offer(
        invoice_id,
        payload.response,
        identity,
    )
    if should_schedule:
        background_tasks.add_task(service.execute_mandated_investment, invoice_id)
    return InvoiceResponse(invoice=invoice)


@router.post(
    "/supplier/wallet",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=documented_errors(403, 409, 422),
    tags=["Funding"],
    summary="공급기업 정산 지갑 저장",
)
async def save_supplier_wallet(
    payload: SaveSupplierWalletRequest,
    service: InvoiceServiceDependency,
    identity: AuthenticatedIdentity | None = supplier_only,
) -> None:
    service.save_supplier_wallet(payload.wallet_address, identity)


@router.post(
    "/investor/mandates/prepare",
    response_model=MandateSigningPayload,
    responses=documented_errors(403, 409, 422),
    tags=["Investor"],
    summary="Mandate 지갑 서명 메시지 준비",
)
async def prepare_mandate(
    payload: PrepareMandateRequest,
    service: InvoiceServiceDependency,
    identity: AuthenticatedIdentity | None = investor_only,
) -> MandateSigningPayload:
    service.assert_wallet_ownership(payload.owner_wallet_address, identity)
    return MandateSigningPayload(
        canonical_message=service.prepare_mandate_message(
            owner_wallet_address=payload.owner_wallet_address,
            policy=payload.policy,
        )
    )


@router.post(
    "/investor/mandates",
    response_model=InvestorMandate,
    responses=documented_errors(403, 409, 422),
    tags=["Investor"],
    summary="지갑 서명 Mandate 활성화",
)
async def create_mandate(
    payload: CreateMandateRequest,
    background_tasks: BackgroundTasks,
    service: InvoiceServiceDependency,
    identity: AuthenticatedIdentity | None = investor_only,
) -> InvestorMandate:
    service.assert_wallet_ownership(payload.owner_wallet_address, identity)
    mandate = service.create_mandate(payload)
    background_tasks.add_task(service.execute_pending_investments)
    return mandate


@router.get(
    "/investor/mandates/active",
    response_model=InvestorMandate,
    responses=documented_errors(403, 404, 409, 422),
    tags=["Investor"],
    summary="지갑의 활성 Mandate 조회",
)
async def get_active_mandate(
    service: InvoiceServiceDependency,
    owner_wallet_address: str = Query(alias="ownerWalletAddress"),
    identity: AuthenticatedIdentity | None = investor_only,
) -> InvestorMandate:
    service.assert_wallet_ownership(owner_wallet_address, identity)
    mandate = service.active_mandate_for_wallet(owner_wallet_address)
    if mandate is None:
        raise NotFoundError(f"{owner_wallet_address}의 활성 Mandate를 찾을 수 없습니다.")
    return mandate


@router.get(
    "/investor/vault",
    response_model=VaultBalance,
    responses=documented_errors(403, 409, 422),
    tags=["Investor"],
    summary="Agent Vault 잔액 조회",
)
async def get_vault(
    service: InvoiceServiceDependency,
    owner_wallet_address: str = Query(alias="ownerWalletAddress"),
    identity: AuthenticatedIdentity | None = investor_only,
) -> VaultBalance:
    service.assert_wallet_ownership(owner_wallet_address, identity)
    return service.get_vault(owner_wallet_address)


@router.post(
    "/investor/vault/deposits/prepare",
    response_model=VaultDepositPreparation,
    responses=documented_errors(403, 409, 422, 502),
    tags=["Investor"],
    summary="Agent Vault 예치 트랜잭션 준비",
)
async def prepare_vault_deposit(
    payload: PrepareVaultDepositRequest,
    service: InvoiceServiceDependency,
    identity: AuthenticatedIdentity | None = investor_only,
) -> VaultDepositPreparation:
    service.assert_wallet_ownership(payload.owner_wallet_address, identity)
    prepared = await service.prepare_vault_deposit(
        owner_wallet_address=payload.owner_wallet_address,
        amount_usdc=payload.amount_usdc,
    )
    return VaultDepositPreparation(
        transaction_base64=prepared.transaction_base64,
        vault_address=prepared.vault_address,
        stablecoin_mint_address=prepared.stablecoin_mint_address,
        sponsored=prepared.sponsored,
        sponsor_deposit_id=prepared.sponsor_deposit_id,
        sponsor_wallet_address=prepared.sponsor_wallet_address,
    )


@router.post(
    "/investor/vault/deposits/sponsor",
    response_model=VaultBalance,
    responses=documented_errors(403, 409, 422, 502),
    tags=["Investor"],
    summary="가스리스 Agent Vault 예치 서명 완결",
)
async def sponsor_vault_deposit(
    payload: SponsorVaultDepositRequest,
    background_tasks: BackgroundTasks,
    service: InvoiceServiceDependency,
    identity: AuthenticatedIdentity | None = investor_only,
) -> VaultBalance:
    service.assert_wallet_ownership(payload.owner_wallet_address, identity)
    vault = await service.sponsor_vault_deposit(payload)
    background_tasks.add_task(service.execute_pending_investments)
    return vault


@router.post(
    "/investor/vault/deposits/confirm",
    response_model=VaultBalance,
    responses=documented_errors(403, 409, 422, 502),
    tags=["Investor"],
    summary="Agent Vault 예치 확인",
)
async def confirm_vault_deposit(
    payload: ConfirmVaultDepositRequest,
    background_tasks: BackgroundTasks,
    service: InvoiceServiceDependency,
    identity: AuthenticatedIdentity | None = investor_only,
) -> VaultBalance:
    service.assert_wallet_ownership(payload.owner_wallet_address, identity)
    vault = await service.confirm_vault_deposit(payload)
    background_tasks.add_task(service.execute_pending_investments)
    return vault


@router.get(
    "/investor/dashboard",
    response_model=InvestorDashboard,
    tags=["Investor"],
    summary="Investor Dashboard",
)
async def investor_dashboard(
    service: InvoiceServiceDependency,
    identity: AuthenticatedIdentity | None = investor_only,
) -> InvestorDashboard:
    return service.investor_dashboard(identity)


@router.post(
    "/invoices/{invoiceId}/settlement/mock-payment",
    response_model=InvoiceResponse,
    responses=documented_errors(403, 404, 409, 502),
    tags=["Settlement"],
    summary="USDC Mock 입금 및 Solana 정산",
)
async def settle_mock_payment(
    invoice_id: InvoiceId,
    service: InvoiceServiceDependency,
    identity: AuthenticatedIdentity | None = supplier_only,
) -> InvoiceResponse:
    return InvoiceResponse(invoice=await service.settle_mock_payment(invoice_id, identity))


async def _read_upload(
    upload: UploadFile,
    document_type: DocumentType,
    max_bytes: int,
) -> UploadedDocument:
    try:
        data = await upload.read(max_bytes + 1)
    finally:
        await upload.close()
    if len(data) > max_bytes:
        raise DocumentValidationError(f"{document_type.value} 파일은 20MB를 초과할 수 없습니다.")
    return UploadedDocument(
        type=document_type,
        file_name=upload.filename or f"{document_type.value}.bin",
        mime_type=(upload.content_type or "application/octet-stream").lower(),
        data=data,
    )
