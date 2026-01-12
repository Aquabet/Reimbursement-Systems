class BaseError(Exception):
    """Base exception for the application."""

    pass


class ConfigurationError(BaseError):
    """Raised when there's an issue with configuration."""

    pass


class DatabaseError(BaseError):
    """Raised when a database operation fails."""

    pass
