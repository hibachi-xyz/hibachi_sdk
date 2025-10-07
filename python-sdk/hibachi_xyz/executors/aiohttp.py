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
    def __init__(self, ws: aiohttp.ClientWebSocketResponse):
        self._ws = ws

    @override
    async def send(self, serialized_body: str) -> None:
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
        await self._ws.close()


class AiohttpWsExecutor(WsExecutor):
    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None

    @override
    async def connect(
        self, web_url: str, headers: dict[str, str] | None = None
    ) -> WsConnection:
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
        if self._session is not None:
            await self._session.close()
            self._session = None
