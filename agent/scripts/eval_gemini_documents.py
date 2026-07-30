"""Evaluate the real Document Agent against committed PDF golden sets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from invoicex_agents import AgentSettings, DocumentAgent, GoogleGeminiClient
from invoicex_agents.clients import MediaDocument
from invoicex_agents.models.document import (
    DocumentExtractedData,
    DocumentField,
    normalize_comparison_value,
)

DEFAULT_FIXTURE_ROOT = Path("agent/fixtures/documents")


def _expected_extracted_data(payload: dict[str, object]) -> dict[str, object]:
    return DocumentExtractedData.model_validate(payload).model_dump(by_alias=True)


def _mismatch_map(
    mismatches: list[dict[str, object]],
) -> dict[str, dict[str, str]]:
    mapped: dict[str, dict[str, str]] = {}
    for mismatch in mismatches:
        field = DocumentField(str(mismatch["field"]))
        mapped[field.value] = {
            str(value["documentId"]): normalize_comparison_value(
                field,
                value["value"],
            )
            for value in mismatch["values"]  # type: ignore[index]
        }
    return mapped


def _evaluate_set(
    fixture_dir: Path,
    agent: DocumentAgent,
) -> dict[str, object]:
    expected_path = fixture_dir / "expected.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    documents = [
        MediaDocument(
            document_id=document["documentId"],
            mime_type="application/pdf",
            data=(fixture_dir / document["pdf"]).read_bytes(),
        )
        for document in expected["documents"]
    ]
    result = agent.analyze(documents)
    actual_documents = {document.document_id: document for document in result.documents}
    failures: list[str] = []

    if set(actual_documents) != {document["documentId"] for document in expected["documents"]}:
        failures.append("documentId set differs from the golden set")

    for expected_document in expected["documents"]:
        document_id = expected_document["documentId"]
        actual = actual_documents.get(document_id)
        if actual is None:
            continue
        if actual.document_type.value != expected_document["expectedDocumentType"]:
            failures.append(
                f"{document_id}: documentType={actual.document_type.value!r}, "
                f"expected={expected_document['expectedDocumentType']!r}"
            )

        expected_data = _expected_extracted_data(expected_document["expectedExtractedData"])
        actual_data = actual.extracted_data.model_dump(by_alias=True)
        for field, expected_value in expected_data.items():
            if actual_data[field] != expected_value:
                failures.append(
                    f"{document_id}.{field}={actual_data[field]!r}, expected={expected_value!r}"
                )

        actual_missing = {field.value for field in actual.missing_fields}
        expected_missing = set(expected_document["expectedMissingFields"])
        if actual_missing != expected_missing:
            failures.append(
                f"{document_id}.missingFields={sorted(actual_missing)!r}, "
                f"expected={sorted(expected_missing)!r}"
            )

    actual_mismatches = _mismatch_map(
        [mismatch.model_dump(by_alias=True) for mismatch in result.mismatches]
    )
    expected_mismatches = _mismatch_map(expected["expectedMismatches"])
    if actual_mismatches != expected_mismatches:
        failures.append(f"mismatches={actual_mismatches!r}, expected={expected_mismatches!r}")

    if result.review_required is not expected["expectedReviewRequired"]:
        failures.append(
            f"reviewRequired={result.review_required!r}, "
            f"expected={expected['expectedReviewRequired']!r}"
        )

    return {
        "setId": expected["setId"],
        "passed": not failures,
        "documentCount": len(result.documents),
        "mismatchFields": [mismatch.field.value for mismatch in result.mismatches],
        "reviewRequired": result.review_required,
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=DEFAULT_FIXTURE_ROOT,
    )
    parser.add_argument(
        "--set",
        action="append",
        dest="sets",
        help="Fixture directory name to evaluate; repeat to select multiple sets.",
    )
    args = parser.parse_args()

    fixture_root: Path = args.fixture_root
    selected_sets = args.sets or sorted(
        path.name
        for path in fixture_root.iterdir()
        if path.is_dir() and (path / "expected.json").is_file()
    )
    agent = DocumentAgent(GoogleGeminiClient(AgentSettings()))
    results = [_evaluate_set(fixture_root / set_name, agent) for set_name in selected_sets]
    summary = {
        "model": AgentSettings().gemini_model,
        "passed": all(result["passed"] for result in results),
        "sets": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not summary["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
