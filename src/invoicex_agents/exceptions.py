"""Sanitized exceptions exposed by the InvoiceX agent package."""


class AgentError(RuntimeError):
    """Base class for agent failures."""


class AgentConfigurationError(AgentError):
    """Raised when required local configuration is missing or invalid."""


class AgentInputError(AgentError):
    """Raised when an agent request violates an invariant."""


class GeminiInvocationError(AgentError):
    """Raised when Gemini cannot complete a request."""


class GeminiResponseValidationError(AgentError):
    """Raised when Gemini returns an invalid structured response."""
