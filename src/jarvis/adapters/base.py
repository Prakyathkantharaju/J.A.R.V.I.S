"""Base adapter interface for all data sources."""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any

import structlog

logger = structlog.get_logger()


class BaseAdapter(ABC):
    """Abstract base class for all data source adapters.

    All adapters must implement:
    - connect(): Establish connection/authentication
    - disconnect(): Clean up resources
    - health_check(): Verify adapter is operational
    - fetch(): Retrieve data within a date range
    """

    def __init__(self, name: str) -> None:
        """Initialize adapter with a name for logging."""
        self.name = name
        self._connected = False
        self.logger = logger.bind(adapter=name)

    @property
    def is_connected(self) -> bool:
        """Check if adapter is currently connected."""
        return self._connected

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the data source.

        Returns:
            True if connection successful, False otherwise.
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect and clean up resources."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify the adapter is operational.

        Returns:
            True if adapter can communicate with data source.
        """
        pass

    @abstractmethod
    async def fetch(
        self,
        start_date: date,
        end_date: date | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Fetch data within a date range.

        Args:
            start_date: Start of date range.
            end_date: End of date range (defaults to start_date for single day).
            **kwargs: Additional adapter-specific parameters.

        Returns:
            Dictionary containing fetched data.
        """
        pass

    async def fetch_today(self, **kwargs: Any) -> dict[str, Any]:
        """Convenience method to fetch today's data."""
        today = date.today()
        return await self.fetch(today, today, **kwargs)

    async def __aenter__(self) -> "BaseAdapter":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()


class AdapterError(Exception):
    """Base exception for adapter errors."""

    def __init__(self, adapter_name: str, message: str) -> None:
        self.adapter_name = adapter_name
        self.message = message
        super().__init__(f"[{adapter_name}] {message}")


class ConnectionError(AdapterError):
    """Raised when adapter fails to connect."""

    pass


class AuthenticationError(AdapterError):
    """Raised when authentication fails."""

    pass


class FetchError(AdapterError):
    """Raised when data fetch fails."""

    pass
