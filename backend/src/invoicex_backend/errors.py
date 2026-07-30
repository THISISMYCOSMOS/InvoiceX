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
