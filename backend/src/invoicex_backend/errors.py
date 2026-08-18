"""Sanitized backend domain errors."""


class BackendError(RuntimeError):
    """Base class for errors safe to expose through the API."""


class NotFoundError(BackendError):
    """Requested aggregate was not found."""


class StateConflictError(BackendError):
    """Requested state transition is not currently allowed."""


class DocumentValidationError(BackendError):
    """Uploaded document set violates the public contract."""


class IntegrationError(BackendError):
    """An external integration could not complete safely."""


class MandateRejectedError(BackendError):
    """Treasury mandate rejected an attempted investment."""


class OnboardingApiError(BackendError):
    """Stable, sanitized onboarding error exposed to the frontend."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
