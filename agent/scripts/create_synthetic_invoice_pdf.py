"""Create a non-sensitive PDF fixture for manual Gemini smoke tests."""

from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def create_invoice(output_path: Path) -> None:
    """Write one simple, text-based invoice PDF."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    pdf.setTitle("InvoiceX Synthetic Invoice")
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(54, height - 60, "INVOICE")

    pdf.setFont("Helvetica", 11)
    lines = [
        "Invoice Number: INV-TEST-001",
        "Supplier: Alpha Components Ltd.",
        "Buyer: Prime Mobility Corp.",
        "Purchase Order Number: PO-TEST-1001",
        "Contract Number: CT-TEST-2026",
        "Currency: KRW",
        "Issue Date: 2026-07-29",
        "Due Date: 2026-10-30",
        "Item: Precision Components",
        "Quantity: 100",
        "Unit Price: 200,000 KRW",
        "Total Amount: 20,000,000 KRW",
        "Payment Terms: Net 93 days",
        "Delivery Completed: Yes",
    ]
    y = height - 105
    for line in lines:
        pdf.drawString(54, y, line)
        y -= 24

    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(
        54,
        48,
        "Synthetic test document. It contains no real company or transaction data.",
    )
    pdf.save()


if __name__ == "__main__":
    destination = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tmp/pdfs/invoicex-synthetic-invoice.pdf")
    )
    create_invoice(destination)
    print(destination.resolve())
