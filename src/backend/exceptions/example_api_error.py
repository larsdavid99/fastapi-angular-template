"""Example API Exception."""


class ExampleApiError(Exception):
    """Raised when the external example API call fails."""

    def __init__(self, message: str = "Example API error", source: str = "httpbin"):
        self.message = message
        self.source = source
        super().__init__(f"[{source}] {message}")
