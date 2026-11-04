from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from hibachi_xyz.errors import (
    DeserializationError,
    WebSocketConnectionError,
    WebSocketMessageError,
)
from hibachi_xyz.executors.aiohttp import AiohttpWsConnection, AiohttpWsExecutor


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message_type",
    [aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.CLOSED],
)
async def test_recv_reports_closed_connection(message_type):
    websocket = Mock(spec=aiohttp.ClientWebSocketResponse)
    websocket.receive = AsyncMock(
        return_value=aiohttp.WSMessage(message_type, None, None)
    )

    with pytest.raises(WebSocketConnectionError, match="WebSocket closed"):
        await AiohttpWsConnection(websocket).recv()


@pytest.mark.asyncio
async def test_recv_preserves_websocket_error_details():
    error = ValueError("bad frame")
    websocket = Mock(spec=aiohttp.ClientWebSocketResponse)
    websocket.receive = AsyncMock(
        return_value=aiohttp.WSMessage(aiohttp.WSMsgType.ERROR, error, None)
    )
    websocket.exception.return_value = error

    with pytest.raises(WebSocketConnectionError, match="WebSocket error: bad frame"):
        await AiohttpWsConnection(websocket).recv()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message", "expected_error"),
    [
        (aiohttp.WSMessage(aiohttp.WSMsgType.PING, b"", None), WebSocketMessageError),
        (
            aiohttp.WSMessage(aiohttp.WSMsgType.BINARY, b"\xff", None),
            DeserializationError,
        ),
    ],
)
async def test_recv_preserves_message_errors(message, expected_error):
    websocket = Mock(spec=aiohttp.ClientWebSocketResponse)
    websocket.receive = AsyncMock(return_value=message)

    with pytest.raises(expected_error):
        await AiohttpWsConnection(websocket).recv()


@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_recv_reports_abrupt_peer_disconnect_after_messages():
    async def handler(request):
        websocket = web.WebSocketResponse()
        await websocket.prepare(request)
        await websocket.receive()
        await websocket.send_str("text message")
        await websocket.send_bytes(b"binary message")
        request.transport.close()
        return websocket

    application = web.Application()
    application.router.add_get("/ws", handler)
    executor = AiohttpWsExecutor()

    async with TestServer(application) as server:
        try:
            connection = await executor.connect(str(server.make_url("/ws")))
            await connection.send("ready")

            assert await connection.recv() == "text message"
            assert await connection.recv() == "binary message"
            with pytest.raises(WebSocketConnectionError, match="WebSocket closed"):
                await connection.recv()
        finally:
            await executor.close()
