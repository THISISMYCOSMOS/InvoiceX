"""Concurrent end-to-end stress runner for the mock API workflow."""

from __future__ import annotations

import argparse
import asyncio
import statistics
import tempfile
import time
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image
from pypdf import PdfWriter

from invoicex_backend.app import create_app
from invoicex_backend.config import BackendSettings


async def run(iterations: int, concurrency: int) -> None:
    with tempfile.TemporaryDirectory(prefix="invoicex-stress-") as directory:
        settings = BackendSettings(
            _env_file=None,
            FIREBASE_MODE="local",
            AGENT_MODE="mock",
            SOLANA_MODE="mock",
            UPLOAD_DIRECTORY=Path(directory),
            PUBLIC_BASE_URL="http://stress",
        )
        app = create_app(settings=settings)
        transport = httpx.ASGITransport(app=app)
        semaphore = asyncio.Semaphore(concurrency)
        latencies: list[float] = []
        pdf_buffer = BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.write(pdf_buffer)
        pdf = pdf_buffer.getvalue()
        image_buffer = BytesIO()
        Image.new("RGB", (1, 1), color="white").save(image_buffer, format="PNG")
        png = image_buffer.getvalue()

        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://stress",
            timeout=30,
        ) as client:

            async def workflow(index: int) -> None:
                async with semaphore:
                    start = time.perf_counter()
                    files = {
                        "INVOICE": (f"invoice-{index}.pdf", pdf, "application/pdf"),
                        "CONTRACT": (f"contract-{index}.pdf", pdf, "application/pdf"),
                        "PURCHASE_ORDER": (
                            f"po-{index}.pdf",
                            pdf,
                            "application/pdf",
                        ),
                        "DELIVERY_PROOF": (
                            f"delivery-{index}.png",
                            png,
                            "image/png",
                        ),
                    }
                    created = await client.post("/api/v1/invoices", files=files)
                    _require(created, 201)
                    invoice_id = created.json()["invoice"]["id"]

                    requested = await client.post(
                        f"/api/v1/invoices/{invoice_id}/verification-request"
                    )
                    _require(requested)
                    verification_id = requested.json()["invoice"]["verificationId"]

                    confirmed = await client.post(
                        f"/api/v1/verifications/{verification_id}/confirm"
                    )
                    _require(confirmed)
                    accepted = await client.post(
                        f"/api/v1/invoices/{invoice_id}/offer-response",
                        json={"response": "ACCEPT"},
                    )
                    _require(accepted)
                    funded = await client.get(f"/api/v1/invoices/{invoice_id}")
                    _require(funded)
                    if funded.json()["invoice"]["status"] != "FUNDED":
                        raise RuntimeError("funding did not reach FUNDED")

                    settled = await client.post(
                        f"/api/v1/invoices/{invoice_id}/settlement/mock-payment"
                    )
                    _require(settled)
                    if settled.json()["invoice"]["status"] != "SETTLED":
                        raise RuntimeError("settlement did not reach SETTLED")
                    latencies.append(time.perf_counter() - start)

            started = time.perf_counter()
            await asyncio.gather(*(workflow(index) for index in range(iterations)))
            elapsed = time.perf_counter() - started

        await app.state.invoice_service.close()
        ordered = sorted(latencies)
        p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
        print(
            "stress_result "
            f"workflows={iterations} requests={iterations * 6} "
            f"concurrency={concurrency} elapsed_seconds={elapsed:.3f} "
            f"workflows_per_second={iterations / elapsed:.2f} "
            f"mean_seconds={statistics.fmean(latencies):.4f} "
            f"p95_seconds={p95:.4f}"
        )


def _require(response: httpx.Response, status_code: int = 200) -> None:
    if response.status_code != status_code:
        raise RuntimeError(
            f"{response.request.method} {response.request.url.path} "
            f"returned {response.status_code}: {response.text}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--concurrency", type=int, default=25)
    args = parser.parse_args()
    if args.iterations < 1 or args.concurrency < 1:
        parser.error("iterations and concurrency must be positive")
    asyncio.run(run(args.iterations, args.concurrency))


if __name__ == "__main__":
    main()
