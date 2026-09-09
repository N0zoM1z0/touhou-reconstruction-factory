"""Factory-specific errors."""


class FactoryError(Exception):
    """Base error for deterministic factory failures."""


class ValidationError(FactoryError, ValueError):
    """Raised when data cannot satisfy the truth-kernel contract."""


class CompatibilityError(FactoryError):
    """Raised when providers cannot form a coherent reconstruction kit."""


class AdapterError(FactoryError):
    """Raised when an existing repository cannot be imported safely."""


class RegressionFixtureError(ValidationError):
    """Raised when a historical regression fixture is malformed or tampered."""


class ReplayError(FactoryError):
    """Raised when a controlled replay cannot satisfy its execution contract."""


class AcceptanceError(FactoryError):
    """Raised when receipts cannot satisfy an acceptance registry contract."""
