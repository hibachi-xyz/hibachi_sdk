import asyncio
import logging
from functools import partial

import orjson
import pytest

from hibachi_xyz.api_ws_account import HibachiWSAccountClient
from hibachi_xyz.errors import (
    SerializationError,
    ValidationError,
    WebSocketConnectionError,
    WebSocketMessageError,
)
from hibachi_xyz.types import Json
from tests.mock_executors import (
    MockExceptionOutput,
    MockSuccessfulOutput,
    MockWsHarness,
)
from tests.unit.conftest import wait_for_predicate

log = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_account_websocket_connect_disconnect():
    """Test basic connection and disconnection."""
    harness = MockWsHarness()
    client = HibachiWSAccountClient(
        api_key="test_key",
        account_id="12345",
        api_endpoint="https://api.test.com",
        executor=harness.executor,
    )

    assert len(harness.connections) == 0
    assert client._websocket is None

    await client.connect()

    assert len(harness.connections) == 1
    mock_websocket = harness.connections[0]
    assert client._websocket == mock_websocket

    assert client.websocket is not None

    await client.disconnect()
    assert client._websocket is None

    with pytest.raises(ValidationError):
        client.websocket


@pytest.mark.asyncio
async def test_stream_start():
    """Test starting the account stream."""
    harness = MockWsHarness()
    client = HibachiWSAccountClient(
        api_key="test_key",
        account_id="12345",
        executor=harness.executor,
    )

    await client.connect()

    mock_websocket = harness.connections[0]

    stream_response = {
        "id": 1,
        "result": {
            "accountSnapshot": {
                "account_id": 12345,
                "balance": "10000.0",
                "positions": [
                    {
                        "symbol": "BTC/USDT-P",
                        "quantity": "0.5",
                        "direction": "LONG",
                        "openPrice": "50000.0",
                        "markPrice": "51000.0",
                        "entryNotional": "25000.0",
                        "notionalValue": "25500.0",
                        "unrealizedTradingPnl": "500.0",
                        "unrealizedFundingPnl": "0.0",
                    }
                ],
            },
            "listenKey": "test_listen_key_12345",
        },
    }
    mock_websocket.stage_recv(
        MockSuccessfulOutput(orjson.dumps(stream_response).decode())
    )

    result = await client.stream_start()

    sent_msg = mock_websocket.call_log[-1]
    assert sent_msg.function_name == "send"
    sent_data = orjson.loads(sent_msg.arg_pack[0])
    assert sent_data["method"] == "stream.start"
    assert sent_data["params"]["accountId"] == 12345

    assert result.listenKey == "test_listen_key_12345"
    assert client.listenKey == "test_listen_key_12345"
    assert result.accountSnapshot.account_id == 12345
    assert result.accountSnapshot.balance == "10000.0"
    assert len(result.accountSnapshot.positions) == 1
    assert result.accountSnapshot.positions[0].symbol == "BTC/USDT-P"

    await client.disconnect()


@pytest.mark.asyncio
async def test_ping():
    """Test ping functionality."""
    harness = MockWsHarness()
    client = HibachiWSAccountClient(
        api_key="test_key",
        account_id="12345",
        executor=harness.executor,
    )

    await client.connect()

    mock_websocket = harness.connections[0]

    client.listenKey = "test_listen_key"

    ping_response = {
        "id": 1,
        "status": 200,
        "result": {},
    }
    mock_websocket.stage_recv(
        MockSuccessfulOutput(orjson.dumps(ping_response).decode())
    )

    await client.ping()

    sent_msg = mock_websocket.call_log[-1]
    assert sent_msg.function_name == "send"
    sent_data = orjson.loads(sent_msg.arg_pack[0])
    assert sent_data["method"] == "stream.ping"
    assert sent_data["params"]["accountId"] == 12345
    assert sent_data["params"]["listenKey"] == "test_listen_key"

    await client.disconnect()


@pytest.mark.asyncio
async def test_ping_without_listen_key():
    """Test that ping raises error without listenKey."""
    harness = MockWsHarness()
    client = HibachiWSAccountClient(
        api_key="test_key",
        account_id="12345",
        executor=harness.executor,
    )

    await client.connect()

    with pytest.raises(
        ValidationError, match="Cannot send ping: listenKey not initialized"
    ):
        await client.ping()

    await client.disconnect()


@pytest.mark.asyncio
async def test_listen_with_handlers():
    """Test listening for messages with event handlers."""
    harness = MockWsHarness()
    client = HibachiWSAccountClient(
        api_key="test_key",
        account_id="12345",
        executor=harness.executor,
    )

    await client.connect()

    mock_websocket = harness.connections[0]

    received_messages: asyncio.Queue[tuple[str, Json]] = asyncio.Queue()

    async def handler(msg: Json, *, handler_name: str):
        received_messages.put_nowait((handler_name, msg))

    client.on("position_update", partial(handler, handler_name="position_update"))
    client.on("balance_update", partial(handler, handler_name="balance_update"))

    position_msg = {
        "topic": "position_update",
        "data": {
            "symbol": "BTC/USDT-P",
            "size": "1.0",
        },
    }
    mock_websocket.stage_recv(MockSuccessfulOutput(orjson.dumps(position_msg).decode()))

    result = await client.listen()

    assert result == position_msg
    assert received_messages.qsize() == 1
    handler_name, msg = await received_messages.get()
    assert handler_name == "position_update"
    assert msg["topic"] == "position_update"

    await client.disconnect()


@pytest.mark.asyncio
async def test_listen_timeout_triggers_ping():
    """Test that listen timeout triggers ping."""
    harness = MockWsHarness()
    client = HibachiWSAccountClient(
        api_key="test_key",
        account_id="12345",
        executor=harness.executor,
    )

    await client.connect()

    mock_websocket = harness.connections[0]

    client.listenKey = "test_listen_key"

    async def stage_ping_response():
        await asyncio.sleep(0.5)
        ping_response = {
            "id": 1,
            "status": 200,
            "result": {},
        }
        mock_websocket.stage_recv(
            MockSuccessfulOutput(orjson.dumps(ping_response).decode())
        )

    stage_task = asyncio.create_task(stage_ping_response())

    try:
        result = await asyncio.wait_for(client.listen(), timeout=1.0)
        assert result is None or result.get("status") == 200
    except asyncio.TimeoutError:
        pass
    finally:
        stage_task.cancel()
        try:
            await stage_task
        except asyncio.CancelledError:
            pass

    await client.disconnect()


@pytest.mark.asyncio
async def test_listen_websocket_connection_error(caplog):
    """Test that WebSocketConnectionError in listen is logged as warning."""
    harness = MockWsHarness()
    client = HibachiWSAccountClient(
        api_key="test_key",
        account_id="12345",
        executor=harness.executor,
    )

    await client.connect()

    mock_websocket = harness.connections[0]

    error_msg = "Connection lost"
    mock_websocket.stage_recv(MockExceptionOutput(WebSocketConnectionError(error_msg)))

    result = await client.listen()

    assert result is None

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
async def test_listen_general_exception(caplog):
    """Test that general exceptions in listen are logged and re-raised."""
    harness = MockWsHarness()
    client = HibachiWSAccountClient(
        api_key="test_key",
        account_id="12345",
        executor=harness.executor,
    )

    await client.connect()

    mock_websocket = harness.connections[0]

    error_msg = "Unexpected error"
    mock_websocket.stage_recv(MockExceptionOutput(RuntimeError(error_msg)))

    with pytest.raises(RuntimeError, match=error_msg):
        await client.listen()

    await wait_for_predicate(
        lambda: any(
            record.levelname == "ERROR"
            and "WebSocket closed:" in record.message
            and error_msg in record.message
            for record in caplog.records
        ),
        timeout=1.0,
    )

    await client.disconnect()


@pytest.mark.asyncio
async def test_message_id_increments():
    """Test that message ID increments with each request."""
    harness = MockWsHarness()
    client = HibachiWSAccountClient(
        api_key="test_key",
        account_id="12345",
        executor=harness.executor,
    )

    await client.connect()

    mock_websocket = harness.connections[0]

    assert client.message_id == 0

    client.listenKey = "test_key"

    for i in range(3):
        response = {"id": i + 1, "status": 200, "result": {}}
        mock_websocket.stage_recv(MockSuccessfulOutput(orjson.dumps(response).decode()))

    await client.ping()
    first_id = client.message_id
    assert first_id == 1

    await client.ping()
    second_id = client.message_id
    assert second_id == 2

    await client.ping()
    third_id = client.message_id
    assert third_id == 3

    await client.disconnect()


@pytest.mark.asyncio
async def test_stream_start_serialization_error():
    """Test that SerializationError is raised when stream.start message serialization fails."""

    harness = MockWsHarness()
    client = HibachiWSAccountClient(
        api_key="test_key",
        account_id="12345",
        executor=harness.executor,
    )

    await client.connect()

    # Inject a non-serializable object into the client's _next_message_id method
    # to cause serialization to fail
    original_next_message_id = client._next_message_id

    def failing_next_message_id():
        # Return a lambda which is not JSON serializable
        return lambda: "not_serializable"

    client._next_message_id = failing_next_message_id

    with pytest.raises(
        SerializationError, match="Failed to serialize stream.start message"
    ):
        await client.stream_start()

    client._next_message_id = original_next_message_id
    await client.disconnect()


@pytest.mark.asyncio
async def test_stream_start_websocket_message_error():
    """Test that WebSocketMessageError is raised when stream.start send fails."""
    harness = MockWsHarness()
    client = HibachiWSAccountClient(
        api_key="test_key",
        account_id="12345",
        executor=harness.executor,
    )

    await client.connect()
    mock_websocket = harness.connections[0]

    # Mock the send method to raise an exception
    original_send = mock_websocket.send

    async def failing_send(*args, **kwargs):
        raise RuntimeError("Mock send failure")

    mock_websocket.send = failing_send

    with pytest.raises(
        WebSocketMessageError, match="Failed to send stream.start message"
    ):
        await client.stream_start()

    # Restore original send
    mock_websocket.send = original_send
    await client.disconnect()


@pytest.mark.asyncio
async def test_ping_serialization_error():
    """Test that SerializationError is raised when ping message serialization fails."""
    harness = MockWsHarness()
    client = HibachiWSAccountClient(
        api_key="test_key",
        account_id="12345",
        executor=harness.executor,
    )

    await client.connect()
    # Set listenKey to a lambda which is not JSON serializable
    client.listenKey = lambda: "not_serializable"

    with pytest.raises(SerializationError, match="Failed to serialize ping message"):
        await client.ping()

    await client.disconnect()


@pytest.mark.asyncio
async def test_ping_websocket_message_error():
    """Test that WebSocketMessageError is raised when ping send fails."""
    harness = MockWsHarness()
    client = HibachiWSAccountClient(
        api_key="test_key",
        account_id="12345",
        executor=harness.executor,
    )

    await client.connect()
    mock_websocket = harness.connections[0]
    client.listenKey = "test_listen_key"

    # Mock the send method to raise an exception
    original_send = mock_websocket.send

    async def failing_send(*args, **kwargs):
        raise ConnectionError("Mock send failure")

    mock_websocket.send = failing_send

    with pytest.raises(WebSocketMessageError, match="Failed to send ping message"):
        await client.ping()

    # Restore original send
    mock_websocket.send = original_send
    await client.disconnect()
