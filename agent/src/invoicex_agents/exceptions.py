"""Sanitized exceptions exposed by the InvoiceX agent package."""


class AgentError(RuntimeError):
    """Base class for agent failures."""


class AgentConfigurationError(AgentError):
    """Raised when required local configuration is missing or invalid."""


class AgentInputError(AgentError):
    """Raised when an agent request violates an invariant."""


class GeminiInvocationError(AgentError):
    """Raised when Gemini cannot complete a request."""

    def __init__(
        self,
        message: str,
        *,
        status_code: object | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class GeminiResponseValidationError(AgentError):
    """Raised when Gemini returns an invalid structured response."""
