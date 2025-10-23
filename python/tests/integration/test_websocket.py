import asyncio

import orjson
import pytest

from hibachi_xyz.api_ws_account import HibachiWSAccountClient
from hibachi_xyz.api_ws_market import HibachiWSMarketClient
from hibachi_xyz.api_ws_trade import HibachiWSTradeClient
from hibachi_xyz.env_setup import setup_environment
from hibachi_xyz.helpers import print_data
from hibachi_xyz.types import (
    AccountSnapshot,
    Nonce,
    OrderPlaceParams,
    OrderType,
    Position,
    Side,
    WebSocketSubscription,
    WebSocketSubscriptionTopic,
)

api_endpoint, data_api_endpoint, api_key, account_id, private_key, public_key, _ = (
    setup_environment()
)


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_market_websocket():
    _, data_api_endpoint, *_ = setup_environment()
    ws_endpoint = data_api_endpoint.replace("https://", "wss://")

    client = HibachiWSMarketClient(api_endpoint=ws_endpoint)

    try:
        await client.connect()

        subscriptions = [
            WebSocketSubscription("BTC/USDT-P", WebSocketSubscriptionTopic.MARK_PRICE),
            WebSocketSubscription("BTC/USDT-P", WebSocketSubscriptionTopic.TRADES),
        ]
        await client.subscribe(subscriptions)

        # Receive 3 valid messages
        count = 0
        while count < 3:
            msg = await client.websocket.recv()
            parsed = orjson.loads(msg)
            assert "symbol" in parsed
            assert "topic" in parsed
            count += 1

        await client.unsubscribe(subscriptions)

    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_trade_websocket():
    client = HibachiWSTradeClient(
        api_url=api_endpoint,
        data_api_url=data_api_endpoint,
        api_key=api_key,
        account_id=account_id,
        account_public_key=public_key,
        private_key=private_key,
    )
    try:
        await client.connect()

        client.api.cancel_all_orders()

        # websocket orders status
        orders_start = await client.get_orders_status()
        print_data(orders_start)

        # confirm list is empty over websockets
        assert len(orders_start.result) == 0

        # confirm with rest api
        orders_rest = client.api.get_pending_orders()
        print_data(orders_rest)

        assert len(orders_rest.orders) == len(orders_start.result)
        assert len(orders_rest.orders) == 0

        # place an order using REST
        current_price = client.api.get_prices("BTC/USDT-P")
        print(f"current_price: {current_price}")

        len(client.api.get_pending_orders().orders)

        (nonce, order_id) = client.api.place_limit_order(
            symbol="BTC/USDT-P",
            quantity=0.0001,
            side=Side.ASK,
            max_fees_percent=0.005,
            price=float(current_price.askPrice) * 1.05,
        )

        # websocket orders status
        orders_start = await client.get_orders_status()

        # confirm with rest api
        orders_rest = client.api.get_pending_orders()

        assert len(orders_rest.orders) == len(orders_start.result)
        assert len(orders_rest.orders) == 1

        # test cancel using websocket

        await client.cancel_all_orders()

        assert len(client.api.get_pending_orders().orders) == 0

        # all orders cleared again...

        price_before = float(current_price.askPrice) * 0.9
        # place an order using websocket
        (nonce, order_id) = await client.place_order(
            OrderPlaceParams(
                symbol="BTC/USDT-P",
                quantity=0.0001,
                side=Side.BID,
                maxFeesPercent=0.0005,
                orderType=OrderType.LIMIT,
                price=price_before,
                orderFlags=None,
                trigger_price=None,
                twap_config=None,
            )
        )

        assert nonce is not None
        assert order_id is not None

        assert isinstance(nonce, Nonce)
        assert isinstance(order_id, int)

        print(f"place new order nonce: {nonce} order_id: {order_id}")

        order = await client.get_order_status(order_id)

        assert order.result.orderId

        price_after = float(current_price.askPrice) * 0.91

        # ---- test using rest
        order_details = client.api.get_order_details(order_id=int(order.result.orderId))

        print("FETCHED ORDER USING REST API:")
        print_data(order_details)

        assert order_details.orderId == order.result.orderId

        print("TESTING WITH WEBSOCKET")

        # ---- modify using websocket:
        # todo: ENG-4232/websocket-trade-ordermodify-not-finding-order-to-modify
        modify_result = await client.modify_order(
            order=order.result,
            quantity=0.0001,
            price=price_after,
            side=order.result.side,
            maxFeesPercent=0.0005,
            nonce=nonce + 1,
        )

        assert modify_result.get("status") == 200

        print("confirm order is in orders status")
        orders_end = await client.get_orders_status()
        print_data(orders_end)

        assert len(orders_end.result) == 1
        assert orders_end.result[0].orderId == order.result.orderId
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Ensure cleanup of tasks and WebSocket connection
        print("Finished WebSocket interaction, cleaning up...")
        try:
            # Disconnect the WebSocket connection
            await client.disconnect()
        except Exception as e:
            print(f"Error during disconnect: {e}")

        # Handle any CancelledError to prevent test failure
        tasks = asyncio.all_tasks()
        for task in tasks:
            if not task.done():
                print(f"Cancelling task: {task}")
                task.cancel()

        for task in tasks:
            try:
                await task  # Await the task again to ensure it has fully finished
            except asyncio.CancelledError:
                print(f"Task {task} was cancelled as expected.")


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_account_websocket():
    api_endpoint, _, api_key, account_id, *_ = setup_environment()
    ws_endpoint = api_endpoint.replace("https://", "wss://")

    client = HibachiWSAccountClient(
        api_endpoint=ws_endpoint, api_key=api_key, account_id=account_id
    )

    try:
        await client.connect()
        result = await client.stream_start()

        assert isinstance(result.listenKey, str), "listenKey should be a string"
        assert isinstance(result.accountSnapshot, AccountSnapshot), (
            "accountSnapshot missing"
        )
        assert isinstance(result.accountSnapshot.positions, list)
        for position in result.accountSnapshot.positions:
            assert isinstance(position, Position), "Invalid Position object"

    finally:
        await client.disconnect()
