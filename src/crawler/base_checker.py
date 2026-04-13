"""Base class for all checkers."""
from abc import ABC, abstractmethod
from typing import TypeVar, Generic


# Define a type variable for the result type
T = TypeVar('T')


class BaseChecker(ABC, Generic[T]):
    """Abstract base class for checkers."""

    def __init__(self, client):
        """Initialize with an HTTP client.

        Args:
            client: An instance of HttpClient.
        """
        self.client = client

    @abstractmethod
    async def check(self, url: str) -> T:
        """Run the check on the given URL.

        Args:
            url: The target URL.

        Returns:
            A result object of type T.
        """
        pass