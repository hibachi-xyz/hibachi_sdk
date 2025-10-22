"""Abstract interfaces for HTTP and WebSocket executors.

This module defines the abstract base classes that all HTTP and WebSocket
executor implementations must follow, enabling pluggable transport layers.
"""

from abc import ABC, abstractmethod
from typing import Any

from hibachi_xyz.types import JsonObject


class HttpResponse:
    """Container for HTTP response data.

    Encapsulates the status code, body, and headers from an HTTP response.
    """

    status: int
    body: JsonObject
    headers: dict[str, str] | None

    __slots__ = ("status", "body", "headers")

    def __init__(
        self,
        *,
        status: int,
        body: JsonObject | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize an HTTP response object.

        Args:
            status: The HTTP status code of the response.
            body: The JSON response body. Defaults to an empty dict if None.
            headers: Optional HTTP response headers as key-value pairs.

        """
        self.status = status
        self.body = body if body is not None else {}
        self.headers = headers


class HttpExecutor(ABC):
    """Abstract base class for HTTP request executors.

    Defines the interface for sending both authenticated and unauthenticated HTTP requests.
    """

    api_key: str | None = None

    @abstractmethod
    def __init__(
        self,
        api_url: str,
        data_api_url: str,
        api_key: str | None,
    ):
        """Initialize the HTTP executor.

        Args:
            api_url: The base API URL for making requests.
            data_api_url: The data API URL for data-specific requests.
            api_key: Optional API key for authentication.

        """
        ...

    @abstractmethod
    def send_authorized_request(
        self,
        method: str,
        path: str,
        json: Any | None = None,
    ) -> HttpResponse:
        """Send an authorized HTTP request with API key authentication.

        Args:
            method: The HTTP method (e.g., 'GET', 'POST', 'PUT', 'DELETE').
            path: The URL path for the request.
            json: Optional JSON payload to send with the request.

        Returns:
            An HttpResponse object containing the status, body, and headers.

        """
        ...

    @abstractmethod
    def send_simple_request(
        self,
        path: str,
    ) -> HttpResponse:
        """Send a simple HTTP GET request without authentication.

        Args:
            path: The URL path for the request.

        Returns:
            An HttpResponse object containing the status, body, and headers.

        """
        ...


class WsConnection(ABC):
    """Abstract base class for WebSocket connection wrappers.

    Defines the interface for WebSocket communication operations.
    """

    @abstractmethod
    async def send(
        self,
        serialized_body: str,
    ) -> None:
        """Send a message through the WebSocket connection.

        Args:
            serialized_body: The serialized message body to send.

        """
        ...

    @abstractmethod
    async def recv(self) -> str:
        """Receive a message from the WebSocket connection.

        Returns:
            The received message as a string.

        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the WebSocket connection."""
        ...


class WsExecutor(ABC):
    """Abstract base class for WebSocket connection executors.

    Defines the interface for establishing WebSocket connections.
    """

    @abstractmethod
    async def connect(
        self,
        web_url: str,
        headers: dict[str, str] | None = None,
    ) -> WsConnection:
        """Establish a WebSocket connection.

        Args:
            web_url: The WebSocket URL to connect to.
            headers: Optional headers to include in the connection handshake.

        Returns:
            A WsConnection object representing the established connection.

        """
        ...
