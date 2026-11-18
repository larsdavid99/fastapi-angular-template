"""UUID Source Unavailable Error."""


class UuidSourceUnavailableError(Exception):
    """Raised when no UUID could be fetched; the vendor's error is its cause."""

    def __init__(self, message: str = "UUID source unavailable"):
        self.message = message
        super().__init__(message)
