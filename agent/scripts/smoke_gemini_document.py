"""Run one real Document Agent call with one or more local PDFs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from invoicex_agents import (
    AgentSettings,
    DocumentAgent,
    GoogleGeminiClient,
    build_agent_error_response,
)
from invoicex_agents.clients import MediaDocument


def main(pdf_paths: list[Path]) -> None:
    """Analyze all supplied PDFs together and print the validated JSON result."""

    settings = AgentSettings()
    agent = DocumentAgent(GoogleGeminiClient(settings))
    result = agent.analyze(
        [
            MediaDocument(
                document_id=f"document-{index:02d}-{pdf_path.stem}"[:100],
                mime_type="application/pdf",
                data=pdf_path.read_bytes(),
            )
            for index, pdf_path in enumerate(pdf_paths, start=1)
        ]
    )
    print(result.model_dump_json(by_alias=True, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze one or more PDFs in a single real Gemini request."
    )
    parser.add_argument(
        "pdfs",
        nargs="*",
        type=Path,
        help="PDF files to analyze together.",
    )
    arguments = parser.parse_args(sys.argv[1:])
    sources = arguments.pdfs or [Path("tmp/pdfs/invoicex-synthetic-invoice.pdf")]
    try:
        main(sources)
    except Exception as exc:
        print(build_agent_error_response(exc).model_dump_json(by_alias=True, indent=2))
        raise SystemExit(1) from None
