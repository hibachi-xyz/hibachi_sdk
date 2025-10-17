"""WebSocket executor implementation using websockets.

This module provides WebSocket connection handling using the websockets library,
serving as the default WebSocket executor for the Hibachi SDK.
"""

from typing import override

import websockets
from websockets.asyncio.client import ClientConnection

from hibachi_xyz.errors import (
    DeserializationError,
    TransportError,
    WebSocketConnectionError,
    WebSocketMessageError,
)
from hibachi_xyz.executors.interface import WsConnection, WsExecutor


class WebsocketsWsConnection(WsConnection):
    """WebSocket connection implementation using websockets.

    Wraps a websockets ClientConnection for WebSocket communication.
    """

    def __init__(self, ws: ClientConnection):
        """Initialize a WebSocket connection wrapper.

        Args:
            ws: The underlying websockets ClientConnection instance to wrap.

        """
        self._ws = ws

    @override
    async def send(self, serialized_body: str) -> None:
        """Send a message over the WebSocket connection.

        Args:
            serialized_body: The serialized message string to send.

        Raises:
            WebSocketConnectionError: If the connection is closed while sending.
            WebSocketMessageError: If sending the message fails for any other reason.

        """
        try:
            await self._ws.send(serialized_body)
        except websockets.exceptions.ConnectionClosed as e:
            raise WebSocketConnectionError(
                f"WebSocket connection closed while sending message: {e}"
            ) from e
        except Exception as e:
            raise WebSocketMessageError(f"Failed to send WebSocket message: {e}") from e

    @override
    async def recv(self) -> str:
        """Receive a message from the WebSocket connection.

        Returns:
            The received message as a UTF-8 decoded string.

        Raises:
            WebSocketConnectionError: If the connection is closed while receiving.
            DeserializationError: If the message cannot be decoded as UTF-8.
            WebSocketMessageError: If receiving the message fails for any other reason.

        """
        try:
            msg = await self._ws.recv()
            if isinstance(msg, bytes):
                return msg.decode("utf-8")
            return msg
        except websockets.exceptions.ConnectionClosed as e:
            raise WebSocketConnectionError(
                f"WebSocket connection closed while receiving message: {e}"
            ) from e
        except UnicodeDecodeError as e:
            raise DeserializationError(
                f"Failed to decode WebSocket message: {e}"
            ) from e
        except Exception as e:
            raise WebSocketMessageError(
                f"Failed to receive WebSocket message: {e}"
            ) from e

    @override
    async def close(self) -> None:
        """Close the WebSocket connection gracefully."""
        await self._ws.close()


class WebsocketsWsExecutor(WsExecutor):
    """WebSocket executor implementation using websockets.

    Establishes WebSocket connections using the websockets library.
    """

    @override
    async def connect(
        self, web_url: str, headers: dict[str, str] | None = None
    ) -> WsConnection:
        """Establish a WebSocket connection to the specified URL.

        Args:
            web_url: The WebSocket URL to connect to (ws:// or wss://).
            headers: Optional dictionary of additional HTTP headers to send during
                the handshake. Defaults to None.

        Returns:
            A WsConnection instance wrapping the established connection.

        Raises:
            WebSocketConnectionError: If the URL is invalid, the handshake fails,
                or the connection cannot be established.
            TransportError: If an unexpected error occurs during connection.

        """
        try:
            headers = headers or {}
            ws = await websockets.connect(web_url, additional_headers=headers)
            return WebsocketsWsConnection(ws)
        except websockets.exceptions.InvalidURI as e:
            raise WebSocketConnectionError(
                f"Invalid WebSocket URL: {web_url}", url=web_url
            ) from e
        except (
            websockets.exceptions.InvalidHandshake,
            websockets.exceptions.InvalidStatus,
        ) as e:
            raise WebSocketConnectionError(
                f"WebSocket handshake failed for {web_url}: {e}", url=web_url
            ) from e
        except (OSError, TimeoutError) as e:
            raise WebSocketConnectionError(
                f"Failed to connect to WebSocket at {web_url}: {e}", url=web_url
            ) from e
        except Exception as e:
            raise TransportError(
                f"Unexpected error connecting to WebSocket at {web_url}: {e}"
            ) from e
