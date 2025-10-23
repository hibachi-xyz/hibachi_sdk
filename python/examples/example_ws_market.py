import asyncio

from hibachi_xyz import (
    HibachiWSMarketClient,
    WebSocketSubscription,
    WebSocketSubscriptionTopic,
)


async def example_ws_market(max_messages: int = None):
    client = HibachiWSMarketClient()
    await client.connect()

    subscriptions = [
        WebSocketSubscription(
            symbol="BTC/USDT-P", topic=WebSocketSubscriptionTopic.MARK_PRICE
        ),
        WebSocketSubscription(
            symbol="BTC/USDT-P", topic=WebSocketSubscriptionTopic.TRADES
        ),
    ]

    # Async handlers for message topics
    async def handle_mark_price(msg):
        print("[Mark Price]", msg)

    async def handle_trades(msg):
        print("[Trades]", msg)

    client.on("mark_price", handle_mark_price)
    client.on("trades", handle_trades)

    await client.subscribe(subscriptions)
    print("Subscribed.")

    received = []

    try:
        if max_messages is None:
            print("Press Ctrl+C to exit.\n")
            while True:
                await asyncio.sleep(1)
        else:
            # Passive listening with message count limit
            while len(received) < max_messages:
                msg = await client.websocket.recv()
                print("[Raw]", msg)
                received.append(msg)
            return received

    except KeyboardInterrupt:
        print("\n[Shutdown] Ctrl+C detected.")

    finally:
        print("[Cleanup] Unsubscribing and disconnecting...")
        await client.unsubscribe(subscriptions)
        await client.disconnect()
        print("[Done] Gracefully exited.")


# Command line usage
if __name__ == "__main__":
    import sys

    try:
        asyncio.run(example_ws_market())
    except KeyboardInterrupt:
        print("\n[Exit] Keyboard interrupt received. Shutting down cleanly.")
        sys.exit(0)
