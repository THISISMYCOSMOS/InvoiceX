"""FastAPI routes implementing the frontend API contract."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Path,
    Request,
    UploadFile,
    status,
)

from invoicex_backend.errors import DocumentValidationError
from invoicex_backend.models import (
    DocumentType,
    ErrorResponse,
    InvestorDashboard,
    InvoiceListResponse,
    InvoiceResponse,
    OfferResponseRequest,
    UploadedDocument,
    VerificationListResponse,
    VerificationResponse,
)
from invoicex_backend.service import InvoiceService

router = APIRouter(prefix="/api/v1")


def documented_errors(*status_codes: int) -> dict[int, dict[str, object]]:
    descriptions = {
        400: "Document or domain validation failed",
        404: "Invoice or Verification was not found",
        409: "The requested state transition is not allowed",
        422: "The request does not match the API contract",
        502: "Gemini, Privy, or Solana integration failed",
    }
    return {
        code: {"model": ErrorResponse, "description": descriptions[code]}
        for code in status_codes
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
    return VerificationResponse(
        verification=service.get_verification(verification_id)
    )


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
    return InvoiceResponse(
        invoice=await service.confirm_verification(verification_id)
    )


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
    service: InvoiceServiceDependency,
) -> InvoiceResponse:
    invoice = await service.respond_to_offer(
        invoice_id,
        payload.response,
    )
    return InvoiceResponse(invoice=invoice)


@router.post(
    "/invoices/{invoiceId}/rwa-purchase",
    response_model=InvoiceResponse,
    responses=documented_errors(404, 409),
    tags=["Funding"],
    summary="Investor RWA 매수 및 조기정산 지급 시작",
)
async def purchase_rwa(
    invoice_id: InvoiceId,
    background_tasks: BackgroundTasks,
    service: InvoiceServiceDependency,
) -> InvoiceResponse:
    invoice, should_schedule = await service.purchase_rwa(invoice_id)
    if should_schedule:
        background_tasks.add_task(service.complete_funding, invoice_id)
    return InvoiceResponse(invoice=invoice)


@router.get(
    "/investor/dashboard",
    response_model=InvestorDashboard,
    tags=["Investor"],
    summary="Investor Dashboard",
)
async def investor_dashboard(
    service: InvoiceServiceDependency,
) -> InvestorDashboard:
    return service.investor_dashboard()


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
        raise DocumentValidationError(
            f"{document_type.value} 파일은 20MB를 초과할 수 없습니다."
        )
    return UploadedDocument(
        type=document_type,
        file_name=upload.filename or f"{document_type.value}.bin",
        mime_type=(upload.content_type or "application/octet-stream").lower(),
        data=data,
    )
