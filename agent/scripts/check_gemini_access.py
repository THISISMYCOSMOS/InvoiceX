"""Check Vertex AI model access without sending InvoiceX documents."""

from __future__ import annotations

from google import genai

from invoicex_agents import AgentSettings


def main() -> None:
    """Run one minimal prompt and print only non-sensitive status data."""

    settings = AgentSettings()
    if not settings.vertex_ai_project_id:
        raise RuntimeError("VERTEX_AI_PROJECT_ID is not configured")

    client = genai.Client(
        vertexai=True,
        project=settings.vertex_ai_project_id,
        location=settings.vertex_ai_location,
    )
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
                "provider": "vertex_ai",
                "project": settings.vertex_ai_project_id,
                "location": settings.vertex_ai_location,
                "status": "FAILED",
                "httpStatus": status_code,
                "errorType": type(exc).__name__,
            }
        )
        raise SystemExit(1) from None

    print(
        {
            "model": settings.gemini_model,
            "provider": "vertex_ai",
            "project": settings.vertex_ai_project_id,
            "location": settings.vertex_ai_location,
            "status": "PASS",
            "hasTextResponse": bool(response.text),
        }
    )


if __name__ == "__main__":
    main()
