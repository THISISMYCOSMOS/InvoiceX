"""FastAPI routes implementing the frontend API contract."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Path,
    Query,
    Request,
    UploadFile,
    status,
)

from invoicex_backend.auth import PrivyPrincipalDependency, require_wallet_owner
from invoicex_backend.errors import DocumentValidationError, NotFoundError
from invoicex_backend.models import (
    ConfirmVaultDepositRequest,
    CreateMandateRequest,
    DocumentType,
    ErrorResponse,
    InvestorDashboard,
    InvestorMandate,
    InvoiceListResponse,
    InvoiceResponse,
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
from invoicex_backend.service import InvoiceService

router = APIRouter(prefix="/api/v1")


def documented_errors(*status_codes: int) -> dict[int, dict[str, object]]:
    descriptions = {
        400: "Document or domain validation failed",
        401: "Privy authentication is missing, invalid, or expired",
        403: "The authenticated Privy user does not own the requested wallet",
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


@router.post(
    "/invoices",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    responses=documented_errors(400, 422, 502),
    tags=["Invoices"],
    summary="문서 등록 및 Gemini 분석",
)
async def create_invoice(
    invoice_file: InvoiceFile,
    contract_file: ContractFile,
    purchase_order_file: PurchaseOrderFile,
    delivery_proof_file: DeliveryProofFile,
    service: InvoiceServiceDependency,
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
    return InvoiceResponse(invoice=await service.create_invoice(uploads))


@router.get(
    "/invoices",
    response_model=InvoiceListResponse,
    tags=["Invoices"],
    summary="Supplier Invoice 목록",
)
async def list_invoices(service: InvoiceServiceDependency) -> InvoiceListResponse:
    return InvoiceListResponse(items=service.list_invoices())


@router.get(
    "/invoices/{invoiceId}",
    response_model=InvoiceResponse,
    responses=documented_errors(404),
    tags=["Invoices"],
    summary="Invoice 통합 상세",
)
async def get_invoice(
    invoice_id: InvoiceId,
    service: InvoiceServiceDependency,
) -> InvoiceResponse:
    return InvoiceResponse(invoice=service.get_invoice(invoice_id))


@router.post(
    "/invoices/{invoiceId}/verification-request",
    response_model=InvoiceResponse,
    responses=documented_errors(404, 409),
    tags=["Verifications"],
    summary="Buyer 검증 요청 생성",
)
async def request_verification(
    invoice_id: InvoiceId,
    service: InvoiceServiceDependency,
) -> InvoiceResponse:
    return InvoiceResponse(invoice=await service.request_verification(invoice_id))


@router.get(
    "/verifications",
    response_model=VerificationListResponse,
    tags=["Verifications"],
    summary="Buyer 검증 목록",
)
async def list_verifications(
    service: InvoiceServiceDependency,
) -> VerificationListResponse:
    return VerificationListResponse(items=service.list_verifications())


@router.get(
    "/verifications/{verificationId}",
    response_model=VerificationResponse,
    responses=documented_errors(404),
    tags=["Verifications"],
    summary="Buyer 검증 상세",
)
async def get_verification(
    verification_id: VerificationId,
    service: InvoiceServiceDependency,
) -> VerificationResponse:
    return VerificationResponse(verification=service.get_verification(verification_id))


@router.post(
    "/verifications/{verificationId}/confirm",
    response_model=InvoiceResponse,
    responses=documented_errors(404, 409, 502),
    tags=["Verifications"],
    summary="Buyer 검증 확정 및 Risk Passport 생성",
)
async def confirm_verification(
    verification_id: VerificationId,
    service: InvoiceServiceDependency,
) -> InvoiceResponse:
    return InvoiceResponse(invoice=await service.confirm_verification(verification_id))


@router.post(
    "/invoices/{invoiceId}/offer-response",
    response_model=InvoiceResponse,
    responses=documented_errors(404, 409, 422),
    tags=["Funding"],
    summary="Supplier 조기정산 조건 응답",
)
async def respond_to_offer(
    invoice_id: InvoiceId,
    payload: OfferResponseRequest,
    background_tasks: BackgroundTasks,
    service: InvoiceServiceDependency,
) -> InvoiceResponse:
    invoice, should_schedule = await service.respond_to_offer(
        invoice_id,
        payload.response,
    )
    if should_schedule:
        background_tasks.add_task(service.execute_mandated_investment, invoice_id)
    return InvoiceResponse(invoice=invoice)


@router.post(
    "/supplier/wallet",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=documented_errors(409, 422),
    tags=["Funding"],
    summary="공급기업 정산 지갑 저장",
)
async def save_supplier_wallet(
    payload: SaveSupplierWalletRequest,
    service: InvoiceServiceDependency,
) -> None:
    service.save_supplier_wallet(payload.wallet_address)


@router.post(
    "/investor/mandates/prepare",
    response_model=MandateSigningPayload,
    responses=documented_errors(409, 422),
    tags=["Investor"],
    summary="Mandate 지갑 서명 메시지 준비",
)
async def prepare_mandate(
    payload: PrepareMandateRequest,
    service: InvoiceServiceDependency,
    principal: PrivyPrincipalDependency,
) -> MandateSigningPayload:
    require_wallet_owner(principal, payload.owner_wallet_address)
    return MandateSigningPayload(
        canonical_message=service.prepare_mandate_message(
            owner_wallet_address=payload.owner_wallet_address,
            policy=payload.policy,
        )
    )


@router.post(
    "/investor/mandates",
    response_model=InvestorMandate,
    responses=documented_errors(409, 422),
    tags=["Investor"],
    summary="지갑 서명 Mandate 활성화",
)
async def create_mandate(
    payload: CreateMandateRequest,
    background_tasks: BackgroundTasks,
    service: InvoiceServiceDependency,
    principal: PrivyPrincipalDependency,
) -> InvestorMandate:
    require_wallet_owner(principal, payload.owner_wallet_address)
    mandate = service.create_mandate(payload)
    background_tasks.add_task(service.execute_pending_investments)
    return mandate


@router.get(
    "/investor/mandates/active",
    response_model=InvestorMandate,
    responses=documented_errors(404, 409, 422),
    tags=["Investor"],
    summary="지갑의 활성 Mandate 조회",
)
async def get_active_mandate(
    service: InvoiceServiceDependency,
    principal: PrivyPrincipalDependency,
    owner_wallet_address: str = Query(alias="ownerWalletAddress"),
) -> InvestorMandate:
    require_wallet_owner(principal, owner_wallet_address)
    mandate = service.active_mandate_for_wallet(owner_wallet_address)
    if mandate is None:
        raise NotFoundError(f"{owner_wallet_address}의 활성 Mandate를 찾을 수 없습니다.")
    return mandate


@router.get(
    "/investor/vault",
    response_model=VaultBalance,
    responses=documented_errors(409, 422),
    tags=["Investor"],
    summary="Agent Vault 잔액 조회",
)
async def get_vault(
    service: InvoiceServiceDependency,
    principal: PrivyPrincipalDependency,
    owner_wallet_address: str = Query(alias="ownerWalletAddress"),
) -> VaultBalance:
    require_wallet_owner(principal, owner_wallet_address)
    return service.get_vault(owner_wallet_address)


@router.post(
    "/investor/vault/deposits/prepare",
    response_model=VaultDepositPreparation,
    responses=documented_errors(409, 422, 502),
    tags=["Investor"],
    summary="Agent Vault 예치 트랜잭션 준비",
)
async def prepare_vault_deposit(
    payload: PrepareVaultDepositRequest,
    service: InvoiceServiceDependency,
    principal: PrivyPrincipalDependency,
) -> VaultDepositPreparation:
    require_wallet_owner(principal, payload.owner_wallet_address)
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
    responses=documented_errors(409, 422, 502),
    tags=["Investor"],
    summary="가스리스 Agent Vault 예치 서명 완결",
)
async def sponsor_vault_deposit(
    payload: SponsorVaultDepositRequest,
    background_tasks: BackgroundTasks,
    service: InvoiceServiceDependency,
    principal: PrivyPrincipalDependency,
) -> VaultBalance:
    require_wallet_owner(principal, payload.owner_wallet_address)
    vault = await service.sponsor_vault_deposit(payload)
    background_tasks.add_task(service.execute_pending_investments)
    return vault


@router.post(
    "/investor/vault/deposits/confirm",
    response_model=VaultBalance,
    responses=documented_errors(409, 422, 502),
    tags=["Investor"],
    summary="Agent Vault 예치 확인",
)
async def confirm_vault_deposit(
    payload: ConfirmVaultDepositRequest,
    background_tasks: BackgroundTasks,
    service: InvoiceServiceDependency,
    principal: PrivyPrincipalDependency,
) -> VaultBalance:
    require_wallet_owner(principal, payload.owner_wallet_address)
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
    principal: PrivyPrincipalDependency,
) -> InvestorDashboard:
    owner_wallet_address = principal.primary_embedded_wallet() if principal is not None else None
    return service.investor_dashboard(owner_wallet_address=owner_wallet_address)


@router.post(
    "/invoices/{invoiceId}/settlement/mock-payment",
    response_model=InvoiceResponse,
    responses=documented_errors(404, 409, 502),
    tags=["Settlement"],
    summary="KRW Mock 입금 및 Solana 정산",
)
async def settle_mock_payment(
    invoice_id: InvoiceId,
    service: InvoiceServiceDependency,
) -> InvoiceResponse:
    return InvoiceResponse(invoice=await service.settle_mock_payment(invoice_id))


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
