import asyncio

from hibachi_xyz import HibachiWSTradeClient, print_data
from hibachi_xyz.env_setup import setup_environment
from hibachi_xyz.types import OrderPlaceParams, OrderType, Side


async def example_ws_trade():
    api_endpoint, data_api_endpoint, api_key, account_id, private_key, public_key, _ = (
        setup_environment()
    )

    client = HibachiWSTradeClient(
        api_url=api_endpoint,
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

        # test cancel using websocket
        await client.cancel_all_orders()

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

        print(f"place new order nonce: {nonce} order_id: {order_id}")
        order = await client.get_order_status(order_id)
        price_after = float(current_price.askPrice) * 0.91

        # ---- test using rest
        order_details = client.api.get_order_details(order_id=int(order.result.orderId))
        print("FETCHED ORDER USING REST API:")
        print_data(order_details)

        print("TESTING WITH WEBSOCKET")

        await client.modify_order(
            order=order.result,
            quantity=0.0001,
            price=price_after,
            side=order.result.side,
            maxFeesPercent=0.0005,
            nonce=nonce + 1,
        )

        print("confirm order is in orders status")

        orders_end = await client.get_orders_status()
        print_data(orders_end)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Closing connection.")
        await client.disconnect()


if __name__ == "__main__":
    # This code only runs when the file is executed directly
    asyncio.run(example_ws_trade())
