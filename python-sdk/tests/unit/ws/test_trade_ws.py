import logging

import orjson
import pytest

from hibachi_xyz.api_ws_trade import HibachiWSTradeClient
from hibachi_xyz.errors import ValidationError
from hibachi_xyz.types import (
    EnableCancelOnDisconnectParams,
    OrdersBatchParams,
)
from tests.mock_executors import MockSuccessfulOutput, MockWsHarness

log = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_trade_websocket_connect_disconnect():
    """Test basic connection and disconnection."""
    harness = MockWsHarness()
    client = HibachiWSTradeClient(
        api_key="test_key",
        account_id=12345,
        account_public_key="test_public_key",
        api_url="https://api.test.com",
        data_api_url="https://data.test.com",
        executor=harness.executor,
    )
    client.api._http_executor = harness.http_executor

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
async def test_get_order_status():
    """Test getting status of a specific order."""
    harness = MockWsHarness()
    client = HibachiWSTradeClient(
        api_key="test_key",
        account_id=12345,
        account_public_key="test_public_key",
        executor=harness.executor,
    )

    await client.connect()

    mock_websocket = harness.connections[0]

    order_response = {
        "id": 1,
        "status": 200,
        "result": {
            "orderId": "12345",
            "accountId": 12345,
            "symbol": "BTC/USDT-P",
            "side": "BID",
            "orderType": "LIMIT",
            "availableQuantity": "0.1",
            "totalQuantity": "0.1",
            "price": "50000.0",
            "triggerPrice": None,
            "status": "PLACED",
            "creationTime": 1704067200000,
        },
    }
    mock_websocket.stage_recv(
        MockSuccessfulOutput(orjson.dumps(order_response).decode())
    )

    result = await client.get_order_status(orderId=12345)

    sent_msg = mock_websocket.call_log[-1]
    assert sent_msg.function_name == "send"
    sent_data = orjson.loads(sent_msg.arg_pack[0])
    assert sent_data["method"] == "order.status"
    assert sent_data["params"]["orderId"] == "12345"
    assert sent_data["params"]["accountId"] == 12345

    assert result.result.orderId == 12345
    assert result.result.symbol == "BTC/USDT-P"
    assert result.result.side.value == "BID"

    await client.disconnect()


@pytest.mark.asyncio
async def test_get_orders_status():
    """Test getting status of all orders."""
    harness = MockWsHarness()
    client = HibachiWSTradeClient(
        api_key="test_key",
        account_id=12345,
        account_public_key="test_public_key",
        executor=harness.executor,
    )

    await client.connect()

    mock_websocket = harness.connections[0]

    orders_response = {
        "id": 2,
        "status": 200,
        "result": [
            {
                "orderId": "12345",
                "accountId": 12345,
                "symbol": "BTC/USDT-P",
                "side": "BID",
                "orderType": "LIMIT",
                "availableQuantity": "0.1",
                "totalQuantity": "0.1",
                "price": "50000.0",
                "triggerPrice": None,
                "status": "PLACED",
                "creationTime": 1704067200000,
            },
            {
                "orderId": "12346",
                "accountId": 12345,
                "symbol": "ETH/USDT-P",
                "side": "ASK",
                "orderType": "LIMIT",
                "availableQuantity": "1.0",
                "totalQuantity": "1.0",
                "price": "3000.0",
                "triggerPrice": None,
                "status": "PLACED",
                "creationTime": 1704067200000,
            },
        ],
    }
    mock_websocket.stage_recv(
        MockSuccessfulOutput(orjson.dumps(orders_response).decode())
    )

    result = await client.get_orders_status()

    sent_msg = mock_websocket.call_log[-1]
    assert sent_msg.function_name == "send"
    sent_data = orjson.loads(sent_msg.arg_pack[0])
    assert sent_data["method"] == "orders.status"
    assert sent_data["params"]["accountId"] == 12345

    assert len(result.result) == 2
    assert result.result[0].orderId == 12345
    assert result.result[1].orderId == 12346

    await client.disconnect()


@pytest.mark.asyncio
async def test_cancel_all_orders():
    """Test canceling all orders."""
    harness = MockWsHarness()
    client = HibachiWSTradeClient(
        api_key="test_key",
        account_id=12345,
        account_public_key="test_public_key",
        private_key="test_private_key",
        executor=harness.executor,
    )

    await client.connect()

    mock_websocket = harness.connections[0]

    cancel_response = {
        "id": client.message_id + 1,
        "status": 200,
        "result": {},
    }
    mock_websocket.stage_recv(
        MockSuccessfulOutput(orjson.dumps(cancel_response).decode())
    )

    result = await client.cancel_all_orders()

    sent_msg = mock_websocket.call_log[-1]
    assert sent_msg.function_name == "send"
    sent_data = orjson.loads(sent_msg.arg_pack[0])
    assert sent_data["method"] == "orders.cancel"
    assert sent_data["params"]["accountId"] == 12345
    assert "signature" in sent_data

    assert result is True

    await client.disconnect()


@pytest.mark.asyncio
async def test_batch_orders():
    """Test batch order operations."""
    harness = MockWsHarness()
    client = HibachiWSTradeClient(
        api_key="test_key",
        account_id=12345,
        account_public_key="test_public_key",
        executor=harness.executor,
    )

    await client.connect()

    mock_websocket = harness.connections[0]

    batch_response = {
        "id": client.message_id + 1,
        "result": {"success": True},
        "status": 200,
        "subscriptions": None,
    }
    mock_websocket.stage_recv(
        MockSuccessfulOutput(orjson.dumps(batch_response).decode())
    )

    batch_params = OrdersBatchParams(
        accountId="12345",
        orders=[],
    )
    result = await client.batch_orders(batch_params)

    sent_msg = mock_websocket.call_log[-1]
    assert sent_msg.function_name == "send"
    sent_data = orjson.loads(sent_msg.arg_pack[0])
    assert sent_data["method"] == "orders.batch"
    assert sent_data["params"]["accountId"] == "12345"

    assert result.result == {"success": True}

    await client.disconnect()


@pytest.mark.asyncio
async def test_enable_cancel_on_disconnect():
    """Test enabling cancel on disconnect."""
    harness = MockWsHarness()
    client = HibachiWSTradeClient(
        api_key="test_key",
        account_id=12345,
        account_public_key="test_public_key",
        executor=harness.executor,
    )

    await client.connect()

    mock_websocket = harness.connections[0]

    cod_response = {
        "id": client.message_id + 1,
        "result": {"enabled": True},
        "status": 200,
        "subscriptions": None,
    }
    mock_websocket.stage_recv(MockSuccessfulOutput(orjson.dumps(cod_response).decode()))

    import time

    cod_params = EnableCancelOnDisconnectParams(
        nonce=int(time.time_ns() // 1_000),
    )
    result = await client.enable_cancel_on_disconnect(cod_params)

    sent_msg = mock_websocket.call_log[-1]
    assert sent_msg.function_name == "send"
    sent_data = orjson.loads(sent_msg.arg_pack[0])
    assert sent_data["method"] == "orders.enableCancelOnDisconnect"
    assert "nonce" in sent_data["params"]

    assert result.result == {"enabled": True}

    await client.disconnect()


@pytest.mark.asyncio
async def test_message_id_increments():
    """Test that message ID increments with each request."""
    harness = MockWsHarness()
    client = HibachiWSTradeClient(
        api_key="test_key",
        account_id=12345,
        account_public_key="test_public_key",
        executor=harness.executor,
    )

    await client.connect()

    mock_websocket = harness.connections[0]

    initial_message_id = client.message_id

    for i in range(3):
        response = {
            "id": initial_message_id + i + 1,
            "status": 200,
            "result": [
                {
                    "orderId": "12345",
                    "accountId": 12345,
                    "symbol": "BTC/USDT-P",
                    "side": "BID",
                    "orderType": "LIMIT",
                    "availableQuantity": "0.1",
                    "totalQuantity": "0.1",
                    "price": "50000.0",
                    "triggerPrice": None,
                    "status": "PLACED",
                    "creationTime": 1704067200000,
                }
            ],
        }
        mock_websocket.stage_recv(MockSuccessfulOutput(orjson.dumps(response).decode()))

    await client.get_orders_status()
    first_id = client.message_id

    await client.get_orders_status()
    second_id = client.message_id

    await client.get_orders_status()
    third_id = client.message_id

    assert second_id == first_id + 1
    assert third_id == second_id + 1

    await client.disconnect()
