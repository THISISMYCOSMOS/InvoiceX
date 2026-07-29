"""Check AI Studio model access without sending InvoiceX documents."""

from __future__ import annotations

from google import genai

from invoicex_agents import AgentSettings


def main() -> None:
    """Run one minimal prompt and print only non-sensitive status data."""

    settings = AgentSettings()
    if settings.gemini_api_key is None:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents="Reply with the single word OK.",
        )
    except Exception as exc:
        status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
        print(
            {
                "model": settings.gemini_model,
                "status": "FAILED",
                "httpStatus": status_code,
                "errorType": type(exc).__name__,
            }
        )
        raise SystemExit(1) from None

    print(
        {
            "model": settings.gemini_model,
            "status": "PASS",
            "hasTextResponse": bool(response.text),
        }
    )


if __name__ == "__main__":
    main()
