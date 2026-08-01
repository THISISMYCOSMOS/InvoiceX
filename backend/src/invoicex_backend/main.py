"""ASGI entrypoint for ``uv run uvicorn invoicex_backend.main:app``."""

from invoicex_backend.app import create_app

app = create_app()
