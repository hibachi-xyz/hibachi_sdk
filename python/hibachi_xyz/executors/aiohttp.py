"""WebSocket executor implementation using aiohttp.

This module provides WebSocket connection handling using the aiohttp library,
supporting async WebSocket operations for the Hibachi SDK.
"""

import asyncio
from typing import override

import aiohttp

from hibachi_xyz.errors import (
    DeserializationError,
    TransportError,
    WebSocketConnectionError,
    WebSocketMessageError,
)
from hibachi_xyz.executors.interface import WsConnection, WsExecutor


class AiohttpWsConnection(WsConnection):
    """WebSocket connection implementation using aiohttp.

    Wraps an aiohttp ClientWebSocketResponse for WebSocket communication.
    """

    def __init__(self, ws: aiohttp.ClientWebSocketResponse):
        """Initialize an AiohttpWsConnection wrapper.

        Args:
            ws: The aiohttp ClientWebSocketResponse object to wrap.

        """
        self._ws = ws

    @override
    async def send(self, serialized_body: str) -> None:
        """Send a message through the WebSocket connection.

        Args:
            serialized_body: The serialized message string to send.

        Raises:
            WebSocketConnectionError: If the connection is lost while sending.
            WebSocketMessageError: If sending the message fails for any other reason.

        """
        try:
            await self._ws.send_str(serialized_body)
        except ConnectionError as e:
            raise WebSocketConnectionError(
                f"WebSocket connection lost while sending message: {e}"
            ) from e
        except Exception as e:
            raise WebSocketMessageError(f"Failed to send WebSocket message: {e}") from e

    @override
    async def recv(self) -> str:
        """Receive a message from the WebSocket connection.

        Returns:
            The received message as a string.

        Raises:
            WebSocketConnectionError: If the WebSocket is closed or encounters an error.
            WebSocketMessageError: If an unexpected message type is received.
            DeserializationError: If decoding the message fails.
            TransportError: If receiving the message fails for any other reason.

        """
        try:
            msg = await self._ws.receive()
            if msg.type == aiohttp.WSMsgType.TEXT:
                return msg.data  # type: ignore
            elif msg.type == aiohttp.WSMsgType.BINARY:
                return msg.data.decode("utf-8")  # type: ignore
            elif msg.type == aiohttp.WSMsgType.CLOSE:
                raise WebSocketConnectionError("WebSocket closed")
            elif msg.type == aiohttp.WSMsgType.ERROR:
                raise WebSocketConnectionError(
                    f"WebSocket error: {self._ws.exception()}"
                )
            else:
                raise WebSocketMessageError(f"Unexpected message type: {msg.type}")
        except WebSocketConnectionError:
            raise
        except WebSocketMessageError:
            raise
        except UnicodeDecodeError as e:
            raise DeserializationError(
                f"Failed to decode WebSocket message: {e}"
            ) from e
        except Exception as e:
            raise TransportError(f"Failed to receive WebSocket message: {e}") from e

    @override
    async def close(self) -> None:
        """Close the WebSocket connection."""
        await self._ws.close()


class AiohttpWsExecutor(WsExecutor):
    """WebSocket executor implementation using aiohttp.

    Manages aiohttp ClientSession and establishes WebSocket connections.
    """

    def __init__(self) -> None:
        """Initialize an AiohttpWsExecutor.

        The executor manages an aiohttp ClientSession for WebSocket connections.
        """
        self._session: aiohttp.ClientSession | None = None

    @override
    async def connect(
        self, web_url: str, headers: dict[str, str] | None = None
    ) -> WsConnection:
        """Connect to a WebSocket endpoint.

        Args:
            web_url: The WebSocket URL to connect to.
            headers: Optional dictionary of HTTP headers to send with the connection request.

        Returns:
            A WsConnection instance wrapping the established WebSocket connection.

        Raises:
            WebSocketConnectionError: If the WebSocket handshake fails, connection fails,
                or the connection times out.
            TransportError: If an unexpected error occurs during connection.

        """
        try:
            if self._session is None:
                self._session = aiohttp.ClientSession()

            ws = await self._session.ws_connect(web_url, headers=headers)
            return AiohttpWsConnection(ws)
        except aiohttp.WSServerHandshakeError as e:
            raise WebSocketConnectionError(
                f"WebSocket handshake failed for {web_url}: {e}", url=web_url
            ) from e
        except aiohttp.ClientConnectionError as e:
            raise WebSocketConnectionError(
                f"Failed to connect to WebSocket at {web_url}: {e}", url=web_url
            ) from e
        except asyncio.TimeoutError as e:
            raise WebSocketConnectionError(
                f"Connection to WebSocket at {web_url} timed out", url=web_url
            ) from e
        except Exception as e:
            raise TransportError(
                f"Unexpected error connecting to WebSocket at {web_url}: {e}"
            ) from e

    async def close(self) -> None:
        """Close the executor and its underlying aiohttp session."""
        if self._session is not None:
            await self._session.close()
            self._session = None
