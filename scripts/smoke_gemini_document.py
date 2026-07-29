"""Run one real Document Agent call with a non-sensitive local PDF."""

from __future__ import annotations

import sys
from pathlib import Path

from invoicex_agents import AgentSettings, DocumentAgent, GoogleGeminiClient
from invoicex_agents.clients import MediaDocument


def main(pdf_path: Path) -> None:
    """Analyze the supplied synthetic PDF and print the validated JSON result."""

    settings = AgentSettings()
    agent = DocumentAgent(GoogleGeminiClient(settings))
    result = agent.analyze(
        [
            MediaDocument(
                document_id="synthetic-invoice-1",
                mime_type="application/pdf",
                data=pdf_path.read_bytes(),
            )
        ]
    )
    print(result.model_dump_json(by_alias=True, indent=2))


if __name__ == "__main__":
    source = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tmp/pdfs/invoicex-synthetic-invoice.pdf")
    )
    main(source)
