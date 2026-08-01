"""InvoiceX FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from invoicex_backend.agents import create_agent_gateway
from invoicex_backend.api import router
from invoicex_backend.config import BackendSettings
from invoicex_backend.errors import (
    BackendError,
    DocumentValidationError,
    IntegrationError,
    NotFoundError,
    StateConflictError,
)
from invoicex_backend.firebase import create_firebase_resources
from invoicex_backend.repository import (
    FirestoreStateRepository,
    MemoryStateRepository,
)
from invoicex_backend.service import InvoiceService
from invoicex_backend.solana import create_solana_gateway
from invoicex_backend.storage import (
    DocumentStorage,
    FirebaseDocumentStorage,
    LocalDocumentStorage,
)


def create_app(
    settings: BackendSettings | None = None,
    service: InvoiceService | None = None,
) -> FastAPI:
    """Create the API and allow dependency injection for contract tests."""

    resolved_settings = settings or BackendSettings()
    storage: DocumentStorage | None = None
    if service is None:
        if resolved_settings.resolved_firebase_mode() == "firebase":
            firebase = create_firebase_resources(resolved_settings)
            storage = FirebaseDocumentStorage(
                resolved_settings,
                firebase.storage_bucket,
            )
            repository = FirestoreStateRepository(
                resolved_settings,
                firebase.firestore_client,
            )
        else:
            storage = LocalDocumentStorage(resolved_settings)
            repository = MemoryStateRepository()
        service = InvoiceService(
            settings=resolved_settings,
            agent_gateway=create_agent_gateway(resolved_settings),
            solana_gateway=create_solana_gateway(resolved_settings),
            storage=storage,
            repository=repository,
        )
    elif resolved_settings.resolved_firebase_mode() == "local":
        storage = LocalDocumentStorage(resolved_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await service.initialize()
        yield
        await service.close()

    app = FastAPI(
        title="InvoiceX Backend API",
        version="1.0.0",
        description=(
            "Firebase-backed frontend API contract implementation with Gemini "
            "Document/Risk Agents and Privy-managed Solana Devnet settlement."
        ),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/docs-json",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "Invoices", "description": "Invoice documents and aggregate state"},
            {"name": "Verifications", "description": "Buyer verification workflow"},
            {"name": "Funding", "description": "Treasury mandate and funding"},
            {"name": "Investor", "description": "Investor dashboard"},
            {"name": "Settlement", "description": "Mock KRW payment and USDC settlement"},
        ],
    )
    app.state.invoice_service = service
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[resolved_settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.get(
        "/uploads/{invoice_id}/{document_id}",
        include_in_schema=False,
    )
    async def read_uploaded_document(
        invoice_id: str,
        document_id: str,
    ) -> Response:
        document, content = await service.read_document(invoice_id, document_id)
        safe_name = document.file_name.replace("\\", "/").rsplit("/", 1)[-1]
        encoded_name = quote(safe_name or "document", safe="")
        return Response(
            content=content,
            media_type=document.mime_type,
            headers={
                "Content-Disposition": f"inline; filename*=UTF-8''{encoded_name}",
                "Cache-Control": "private, no-store",
            },
        )

    if storage is not None and storage.directory is not None:
        app.mount(
            "/uploads",
            StaticFiles(directory=storage.directory),
            name="uploads",
        )

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
        return _error_response(404, str(exc))

    @app.exception_handler(StateConflictError)
    async def conflict_handler(_: Request, exc: StateConflictError) -> JSONResponse:
        return _error_response(409, str(exc))

    @app.exception_handler(DocumentValidationError)
    async def document_handler(
        _: Request,
        exc: DocumentValidationError,
    ) -> JSONResponse:
        return _error_response(400, str(exc))

    @app.exception_handler(IntegrationError)
    async def integration_handler(_: Request, exc: IntegrationError) -> JSONResponse:
        return _error_response(502, str(exc))

    @app.exception_handler(BackendError)
    async def backend_handler(_: Request, exc: BackendError) -> JSONResponse:
        return _error_response(400, str(exc))

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        _: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        details = [
            {
                "location": ".".join(str(part) for part in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={"message": "요청 형식이 API 계약과 일치하지 않습니다.", "details": details},
        )

    @app.exception_handler(HTTPException)
    async def http_handler(_: Request, exc: HTTPException) -> JSONResponse:
        return _error_response(exc.status_code, str(exc.detail))

    return app


def _error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"message": message})
