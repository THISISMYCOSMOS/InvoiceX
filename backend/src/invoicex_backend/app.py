"""InvoiceX FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from invoicex_backend.agents import create_agent_gateway
from invoicex_backend.api import auth_router, router
from invoicex_backend.config import BackendSettings
from invoicex_backend.errors import (
    BackendError,
    DocumentValidationError,
    IntegrationError,
    NotFoundError,
    StateConflictError,
)
from invoicex_backend.repository import CloudSqlRwaRepository, SQLiteRwaRepository
from invoicex_backend.secrets import load_settings
from invoicex_backend.service import InvoiceService
from invoicex_backend.solana import create_solana_gateway
from invoicex_backend.storage import GcsDocumentStorage, LocalDocumentStorage


def create_repository(settings: BackendSettings):
    if settings.persistence_backend == "cloud_sql":
        return CloudSqlRwaRepository.from_settings(settings)
    return SQLiteRwaRepository(settings.rwa_database_path)


def create_document_storage(settings: BackendSettings):
    if settings.document_storage_backend == "gcs":
        return GcsDocumentStorage(settings)
    return LocalDocumentStorage(settings)


def create_app(
    settings: BackendSettings | None = None,
    service: InvoiceService | None = None,
) -> FastAPI:
    """Create the API and allow dependency injection for contract tests."""

    resolved_settings = settings or load_settings()
    storage = create_document_storage(resolved_settings)
    if service is None:
        service = InvoiceService(
            settings=resolved_settings,
            agent_gateway=create_agent_gateway(resolved_settings),
            solana_gateway=create_solana_gateway(resolved_settings),
            storage=storage,
            repository=create_repository(resolved_settings),
        )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await service.close()

    app = FastAPI(
        title="InvoiceX Backend API",
        version="1.0.0",
        description=(
            "Frontend API contract implementation with Gemini Document/Risk Agents "
            "and direct Solana Devnet RWA automation."
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
    app.state.settings = resolved_settings

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        """Unauthenticated liveness endpoint for Cloud Run and deployment checks."""

        return {"status": "ok"}

    @app.get("/api/v1/healthz", include_in_schema=False)
    async def api_healthz() -> dict[str, str]:
        """API-namespaced liveness endpoint for clients and reverse proxies."""

        return {"status": "ok"}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[resolved_settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router)
    app.include_router(router)
    if isinstance(storage, LocalDocumentStorage):
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
