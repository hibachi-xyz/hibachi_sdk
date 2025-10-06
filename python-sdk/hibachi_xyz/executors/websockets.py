from typing import override

import websockets
from websockets.client import WebSocketClientProtocol

from hibachi_xyz.errors import (
    DeserializationError,
    TransportError,
    WebSocketConnectionError,
    WebSocketMessageError,
)
from hibachi_xyz.executors.interface import WsConnection, WsExecutor


class WebsocketsWsConnection(WsConnection):
    def __init__(self, ws: WebSocketClientProtocol):
        self._ws = ws

    @override
    async def send(self, serialized_body: str) -> None:
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
        await self._ws.close()


class WebsocketsWsExecutor(WsExecutor):
    @override
    async def connect(
        self, web_url: str, headers: dict[str, str] | None = None
    ) -> WsConnection:
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
            websockets.exceptions.InvalidStatusCode,
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
