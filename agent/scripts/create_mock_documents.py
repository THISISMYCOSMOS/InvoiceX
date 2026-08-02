"""Generate the mock InvoiceX transaction document sets and their answer keys.

The sets follow the transaction described in the product documents: a 3,000 KRW
invoice issued by a supplier against a purchase order and a supply contract. Every
company, number and date here is synthetic.

Set A is the happy path where all four documents agree.
Set B repeats the same transaction with a purchase order that was issued at a lower
unit price, so the Document Agent must report a totalAmount and a unitPrice mismatch.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

KOREAN_FONT = "HYSMyeongJo-Medium"

CANONICAL_FIELDS = (
    "invoiceNumber",
    "supplierName",
    "buyerName",
    "purchaseOrderNumber",
    "contractNumber",
    "currency",
    "totalAmount",
    "issueDate",
    "dueDate",
    "itemName",
    "quantity",
    "unitPrice",
    "paymentTerms",
    "deliveryCompleted",
)

# issueDate는 거래 단위 속성이 아니라 문서 자신의 발행일이다. 청구서·발주서·납품확인서는
# 각자 다른 날 발행되므로 값이 달라도 불일치가 아니다. 나머지 필드는 거래 단위 속성이다.
PER_DOCUMENT_FIELDS = ("issueDate",)

SUPPLIER = "(주)알파컴포넌츠"
BUYER = "(주)프라임모빌리티"
ITEM = "정밀 가공 부품"
PAYMENT_TERMS = "청구서 발행일로부터 93일 이내 지급"


@dataclass(frozen=True)
class MockDocument:
    """One synthetic PDF and the human-confirmed values it is expected to yield."""

    document_id: str
    file_name: str
    heading: str
    document_type: str
    lines: tuple[tuple[str, str], ...]
    extracted: dict[str, object]
    note: str = ""

    def expected_extracted_data(self) -> dict[str, object]:
        return {name: self.extracted.get(name) for name in CANONICAL_FIELDS}

    def expected_missing_fields(self) -> list[str]:
        return [name for name in CANONICAL_FIELDS if self.extracted.get(name) is None]


@dataclass(frozen=True)
class MockDocumentSet:
    """A group of documents that belong to the same transaction."""

    set_id: str
    title: str
    documents: tuple[MockDocument, ...]
    expected_mismatches: tuple[dict[str, object], ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)


def _invoice(
    document_id: str,
    invoice_number: str,
    purchase_order_number: str,
    unit_price: int,
    total_amount: int,
) -> MockDocument:
    return MockDocument(
        document_id=document_id,
        file_name=f"{document_id}.pdf",
        heading="청구서 (INVOICE)",
        document_type="INVOICE",
        lines=(
            ("인보이스 번호", invoice_number),
            ("공급기업", SUPPLIER),
            ("구매기업", BUYER),
            ("계약번호", "CT-2026-0007"),
            ("발주번호", purchase_order_number),
            ("발행일", "2026-07-29"),
            ("지급 만기일", "2026-10-30"),
            ("통화", "KRW"),
            ("품목", ITEM),
            ("수량", "100"),
            ("단가", f"{unit_price:,} KRW"),
            ("공급가액 합계", f"{total_amount:,} KRW"),
            ("지급 조건", PAYMENT_TERMS),
            ("납품 완료 여부", "완료"),
        ),
        extracted={
            "invoiceNumber": invoice_number,
            "supplierName": SUPPLIER,
            "buyerName": BUYER,
            "purchaseOrderNumber": purchase_order_number,
            "contractNumber": "CT-2026-0007",
            "currency": "KRW",
            "totalAmount": str(total_amount),
            "issueDate": "2026-07-29",
            "dueDate": "2026-10-30",
            "itemName": ITEM,
            "quantity": "100",
            "unitPrice": str(unit_price),
            "paymentTerms": PAYMENT_TERMS,
            "deliveryCompleted": True,
        },
    )


def _contract(document_id: str) -> MockDocument:
    return MockDocument(
        document_id=document_id,
        file_name=f"{document_id}.pdf",
        heading="물품공급계약서 (CONTRACT)",
        document_type="CONTRACT",
        lines=(
            ("계약번호", "CT-2026-0007"),
            ("공급기업", SUPPLIER),
            ("구매기업", BUYER),
            ("계약 기간", "2026-01-01 ~ 2026-12-31"),
            ("통화", "KRW"),
            ("계약 품목", ITEM),
            ("계약 단가", "30 KRW"),
            ("대금 지급 조건", PAYMENT_TERMS),
        ),
        extracted={
            "supplierName": SUPPLIER,
            "buyerName": BUYER,
            "contractNumber": "CT-2026-0007",
            "currency": "KRW",
            "itemName": ITEM,
            "unitPrice": "30",
            "paymentTerms": PAYMENT_TERMS,
        },
        note=(
            "계약서에는 개별 청구 건의 번호·금액·만기일이 없다. "
            "해당 필드는 누락으로 선언되어야 한다."
        ),
    )


def _purchase_order(
    document_id: str,
    purchase_order_number: str,
    unit_price: int,
    total_amount: int,
) -> MockDocument:
    return MockDocument(
        document_id=document_id,
        file_name=f"{document_id}.pdf",
        heading="발주서 (PURCHASE ORDER)",
        document_type="PURCHASE_ORDER",
        lines=(
            ("발주번호", purchase_order_number),
            ("계약번호", "CT-2026-0007"),
            ("공급기업", SUPPLIER),
            ("구매기업", BUYER),
            ("발주일", "2026-07-01"),
            ("납품 요청일", "2026-07-24"),
            ("통화", "KRW"),
            ("품목", ITEM),
            ("수량", "100"),
            ("단가", f"{unit_price:,} KRW"),
            ("발주 금액", f"{total_amount:,} KRW"),
        ),
        extracted={
            "supplierName": SUPPLIER,
            "buyerName": BUYER,
            "purchaseOrderNumber": purchase_order_number,
            "contractNumber": "CT-2026-0007",
            "currency": "KRW",
            "totalAmount": str(total_amount),
            "issueDate": "2026-07-01",
            "itemName": ITEM,
            "quantity": "100",
            "unitPrice": str(unit_price),
        },
        note="발주일은 발주서 자체의 발행일이며 청구서 발행일과 다르다. 불일치가 아니다.",
    )


def _delivery_note(document_id: str, purchase_order_number: str) -> MockDocument:
    return MockDocument(
        document_id=document_id,
        file_name=f"{document_id}.pdf",
        heading="거래명세서 및 납품확인서 (DELIVERY EVIDENCE)",
        document_type="DELIVERY_EVIDENCE",
        lines=(
            ("발주번호", purchase_order_number),
            ("공급기업", SUPPLIER),
            ("구매기업", BUYER),
            ("발행일", "2026-07-24"),
            ("납품일", "2026-07-24"),
            ("통화", "KRW"),
            ("품목", ITEM),
            ("수량", "100"),
            ("단가", "30 KRW"),
            ("공급가액 합계", "3,000 KRW"),
            ("인수 확인", "발주 수량 전량 납품 완료"),
            ("인수 부서", "구매기업 물류팀"),
        ),
        extracted={
            "supplierName": SUPPLIER,
            "buyerName": BUYER,
            "purchaseOrderNumber": purchase_order_number,
            "currency": "KRW",
            "totalAmount": "3000",
            "issueDate": "2026-07-24",
            "itemName": ITEM,
            "quantity": "100",
            "unitPrice": "30",
            "deliveryCompleted": True,
        },
        note="납품 완료 사실을 확인하는 증빙이다. 지급 만기일과 계약번호는 담지 않는다.",
    )


SET_A = MockDocumentSet(
    set_id="set-a-happy-path",
    title="해피패스 — 4개 문서의 공통 항목이 모두 일치",
    documents=(
        _invoice("a-invoice", "INV-2026-0001", "PO-2026-1001", 30, 3_000),
        _contract("a-contract"),
        _purchase_order("a-purchase-order", "PO-2026-1001", 30, 3_000),
        _delivery_note("a-delivery-note", "PO-2026-1001"),
    ),
    expected_mismatches=(),
    notes=(
        "발행일은 청구서 2026-07-29, 발주서 2026-07-01, 납품확인서 2026-07-24로 서로 다르다.",
        "이를 불일치로 보고하면 오탐이며 해피패스가 Buyer Verification 단계에서 막힌다.",
        "reviewRequired는 false가 기대값이다. 누락 필드는 있으나 거래 단위 값은 충돌하지 않는다.",
    ),
)

SET_B = MockDocumentSet(
    set_id="set-b-amount-mismatch",
    title="불일치 — 발주서 단가가 계약·청구서보다 낮게 발행됨",
    documents=(
        _invoice("b-invoice", "INV-2026-0002", "PO-2026-1002", 30, 3_000),
        _contract("b-contract"),
        _purchase_order("b-purchase-order", "PO-2026-1002", 28, 2_800),
        _delivery_note("b-delivery-note", "PO-2026-1002"),
    ),
    expected_mismatches=(
        {
            "field": "totalAmount",
            "values": [
                {"documentId": "b-invoice", "value": "3000"},
                {"documentId": "b-purchase-order", "value": "2800"},
                {"documentId": "b-delivery-note", "value": "3000"},
            ],
            "description": "청구서와 거래명세서는 3,000원, 발주서는 2,800원이다.",
        },
        {
            "field": "unitPrice",
            "values": [
                {"documentId": "b-invoice", "value": "30"},
                {"documentId": "b-contract", "value": "30"},
                {"documentId": "b-purchase-order", "value": "28"},
                {"documentId": "b-delivery-note", "value": "30"},
            ],
            "description": "계약 단가는 30원이나 발주서만 28원으로 발행되었다.",
        },
    ),
    notes=(
        "reviewRequired는 true가 기대값이다.",
        "이 상태는 Dispute가 아니라 Request Revision으로 처리되는 정보 오기재 유형이다.",
        "수량·품목·거래 당사자·통화는 네 문서 모두 일치한다.",
    ),
)

DOCUMENT_SETS = (SET_A, SET_B)


def render_pdf(document: MockDocument, output_path: Path) -> None:
    """Write one synthetic document as a single-page, text-based PDF."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    _, height = A4

    pdf.setTitle(f"InvoiceX mock document {document.document_id}")
    pdf.setFont(KOREAN_FONT, 18)
    pdf.drawString(54, height - 64, document.heading)

    pdf.setFont(KOREAN_FONT, 11)
    y = height - 104
    for label, value in document.lines:
        pdf.drawString(54, y, f"{label}: {value}")
        y -= 26

    pdf.setFont(KOREAN_FONT, 9)
    disclaimer = "합성 테스트 문서입니다. 실제 기업 정보나 거래 정보를 포함하지 않습니다."
    pdf.drawString(54, 48, disclaimer)
    pdf.save()


def build_answer_key(document_set: MockDocumentSet) -> dict[str, object]:
    """Return the human-confirmed expectations for one document set."""

    return {
        "setId": document_set.set_id,
        "title": document_set.title,
        "documents": [
            {
                "documentId": document.document_id,
                "pdf": document.file_name,
                "expectedDocumentType": document.document_type,
                "expectedExtractedData": document.expected_extracted_data(),
                "expectedMissingFields": document.expected_missing_fields(),
                "note": document.note,
            }
            for document in document_set.documents
        ],
        "expectedMismatches": [dict(item) for item in document_set.expected_mismatches],
        "expectedReviewRequired": bool(document_set.expected_mismatches),
        "notes": list(document_set.notes),
        "perDocumentFields": list(PER_DOCUMENT_FIELDS),
        "comparisonRules": [
            "금액과 수량은 자릿수 구분 기호를 제거한 숫자 문자열로 비교한다.",
            "날짜는 YYYY-MM-DD로 비교한다.",
            "perDocumentFields는 문서 자신의 속성이므로 문서 간 값이 달라도 불일치가 아니다.",
            "evidenceId는 모델이 생성하므로 정답지에 없다. 근거의 존재와 documentId만 확인한다.",
        ],
    }


def create_document_sets(output_root: Path) -> list[Path]:
    """Generate every mock set under output_root and return the written paths."""

    pdfmetrics.registerFont(UnicodeCIDFont(KOREAN_FONT))
    written: list[Path] = []
    for document_set in DOCUMENT_SETS:
        set_dir = output_root / document_set.set_id
        for document in document_set.documents:
            pdf_path = set_dir / document.file_name
            render_pdf(document, pdf_path)
            written.append(pdf_path)

        answer_key_path = set_dir / "expected.json"
        answer_key_path.write_text(
            json.dumps(build_answer_key(document_set), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written.append(answer_key_path)
    return written


if __name__ == "__main__":
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("fixtures/documents")
    for path in create_document_sets(destination):
        print(path.resolve())
