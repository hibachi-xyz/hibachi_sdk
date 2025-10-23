import asyncio
import logging
from functools import partial

import orjson
import pytest

from hibachi_xyz.api_ws_market import HibachiWSMarketClient
from hibachi_xyz.errors import (
    SerializationError,
    ValidationError,
    WebSocketConnectionError,
    WebSocketMessageError,
)
from hibachi_xyz.types import (
    Json,
    WebSocketSubscription,
    WebSocketSubscriptionTopic,
)
from tests.mock_executors import (
    MockExceptionOutput,
    MockSuccessfulOutput,
    MockWsHarness,
)
from tests.unit.conftest import wait_for_predicate

log = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_market_websocket():
    harness = MockWsHarness()
    client = HibachiWSMarketClient(api_endpoint="foo", executor=harness.executor)

    assert len(harness.connections) == 0
    assert client._websocket is None

    await client.connect()

    assert len(harness.connections) == 1
    mock_websocket = harness.connections[0]
    assert client._websocket == mock_websocket

    subscriptions = [
        WebSocketSubscription("BTC/USDT-P", WebSocketSubscriptionTopic.MARK_PRICE),
        WebSocketSubscription("BTC/USDT-P", WebSocketSubscriptionTopic.TRADES),
    ]
    await client.subscribe(subscriptions)

    input = mock_websocket.call_log.pop()
    assert input.function_name == "send"
    assert len(input.arg_pack) == 1
    sent_msg = orjson.loads(input.arg_pack[0])
    log.critical(sent_msg)
    assert sent_msg == {
        "method": "subscribe",
        "parameters": {
            "subscriptions": [
                {"symbol": "BTC/USDT-P", "topic": "mark_price"},
                {"symbol": "BTC/USDT-P", "topic": "trades"},
            ]
        },
    }

    assert len(client._event_handlers) == 0

    client_received: asyncio.Queue[tuple[str, Json]] = asyncio.Queue()

    async def handler(msg: Json, *, handler_name: str):
        client_received.put_nowait((handler_name, msg))

    client.on("mark_price", partial(handler, handler_name="mark_price"))
    client.on("trades", partial(handler, handler_name="trades"))

    assert len(client._event_handlers) == 2

    assert client_received.qsize() == 0

    payload_1 = {
        "topic": "mark_price",
        "foo": "bar",
    }

    payload_1s = orjson.dumps(payload_1).decode()

    mock_websocket.stage_recv(MockSuccessfulOutput(payload_1s))

    # wait for the msg we just sent from the mock server to arrive. This should be near instant as it's just waiting for our very underloaded asyncio event loop to step a few times
    new_msg = await asyncio.wait_for(client_received.get(), 5)
    assert new_msg == ("mark_price", payload_1)

    payload_2 = {
        "topic": "trades",
        "bar": "foo",
    }
    payload_2s = orjson.dumps(payload_2).decode()
    mock_websocket.stage_recv(MockSuccessfulOutput(payload_2s))

    new_msg = await asyncio.wait_for(client_received.get(), 5)
    assert new_msg == ("trades", payload_2)

    await client.unsubscribe(subscriptions)

    # TODO this should be the behavior but is not the current behavior so we will not change ws api for which this would be a breaking change
    """
    mock_websocket.stage_recv(payload_1s)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(unread_client_msg.wait(), 1)

    assert len(client_received) == 0

    """
    assert client.websocket is not None

    await client.disconnect()

    with pytest.raises(ValidationError):
        # is None under the hood, property should raise
        client.websocket


@pytest.mark.asyncio
async def test_websocket_connection_error_handling(caplog):
    """Test that WebSocketConnectionError is caught and logged as warning."""
    harness = MockWsHarness()
    client = HibachiWSMarketClient(api_endpoint="foo", executor=harness.executor)

    await client.connect()
    mock_websocket = harness.connections[0]

    # Stage a WebSocketConnectionError
    error_msg = "Connection closed by server"
    mock_websocket.stage_recv(MockExceptionOutput(WebSocketConnectionError(error_msg)))

    # Wait for the warning to be logged
    await wait_for_predicate(
        lambda: any(
            record.levelname == "WARNING"
            and "WebSocket closed:" in record.message
            and error_msg in record.message
            for record in caplog.records
        ),
        timeout=1.0,
    )

    await client.disconnect()


@pytest.mark.asyncio
async def test_general_exception_handling(caplog):
    """Test that general exceptions are caught and logged as error."""
    harness = MockWsHarness()
    client = HibachiWSMarketClient(api_endpoint="foo", executor=harness.executor)

    await client.connect()
    mock_websocket = harness.connections[0]

    # Stage a general exception
    error_msg = "Unexpected error occurred"
    mock_websocket.stage_recv(MockExceptionOutput(ValueError(error_msg)))

    # Wait for the error to be logged
    await wait_for_predicate(
        lambda: any(
            record.levelname == "ERROR"
            and "Receive loop error:" in record.message
            and error_msg in record.message
            for record in caplog.records
        ),
        timeout=1.0,
    )

    await client.disconnect()


@pytest.mark.asyncio
async def test_subscribe_serialization_error():
    """Test that SerializationError is raised when message serialization fails."""
    import unittest.mock

    harness = MockWsHarness()
    client = HibachiWSMarketClient(api_endpoint="foo", executor=harness.executor)

    await client.connect()

    # Patch orjson.dumps to raise an error
    with unittest.mock.patch("hibachi_xyz.api_ws_market.orjson.dumps") as mock_dumps:
        mock_dumps.side_effect = TypeError("Mock serialization error")

        subscriptions = [
            WebSocketSubscription("BTC/USDT-P", WebSocketSubscriptionTopic.MARK_PRICE),
        ]

        with pytest.raises(
            SerializationError, match="Failed to serialize unsubscribe message"
        ):
            await client.subscribe(subscriptions)

    await client.disconnect()


@pytest.mark.asyncio
async def test_subscribe_websocket_message_error():
    """Test that WebSocketMessageError is raised when send fails."""

    harness = MockWsHarness()
    client = HibachiWSMarketClient(api_endpoint="foo", executor=harness.executor)

    await client.connect()
    mock_websocket = harness.connections[0]

    subscriptions = [
        WebSocketSubscription("BTC/USDT-P", WebSocketSubscriptionTopic.MARK_PRICE),
    ]

    # Mock the send method to raise an exception
    original_send = mock_websocket.send

    async def failing_send(*args, **kwargs):
        raise RuntimeError("Mock send failure")

    mock_websocket.send = failing_send

    with pytest.raises(
        WebSocketMessageError, match="Failed to send unsubscribe message"
    ):
        await client.subscribe(subscriptions)

    # Restore original send
    mock_websocket.send = original_send
    await client.disconnect()


@pytest.mark.asyncio
async def test_unsubscribe_serialization_error():
    """Test that SerializationError is raised when unsubscribe message serialization fails."""
    import unittest.mock

    harness = MockWsHarness()
    client = HibachiWSMarketClient(api_endpoint="foo", executor=harness.executor)

    await client.connect()

    # Patch orjson.dumps to raise an error
    with unittest.mock.patch("hibachi_xyz.api_ws_market.orjson.dumps") as mock_dumps:
        mock_dumps.side_effect = ValueError("Mock serialization error")

        subscriptions = [
            WebSocketSubscription("BTC/USDT-P", WebSocketSubscriptionTopic.MARK_PRICE),
        ]

        with pytest.raises(
            SerializationError, match="Failed to serialize unsubscribe message"
        ):
            await client.unsubscribe(subscriptions)

    await client.disconnect()


@pytest.mark.asyncio
async def test_unsubscribe_websocket_message_error():
    """Test that WebSocketMessageError is raised when unsubscribe send fails."""

    harness = MockWsHarness()
    client = HibachiWSMarketClient(api_endpoint="foo", executor=harness.executor)

    await client.connect()
    mock_websocket = harness.connections[0]

    subscriptions = [
        WebSocketSubscription("BTC/USDT-P", WebSocketSubscriptionTopic.MARK_PRICE),
    ]

    # Mock the send method to raise an exception
    original_send = mock_websocket.send

    async def failing_send(*args, **kwargs):
        raise ConnectionError("Mock send failure")

    mock_websocket.send = failing_send

    with pytest.raises(
        WebSocketMessageError, match="Failed to send unsubscribe message"
    ):
        await client.unsubscribe(subscriptions)

    # Restore original send
    mock_websocket.send = original_send
    await client.disconnect()
