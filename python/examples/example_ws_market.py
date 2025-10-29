"""
WebSocket Market Data Client Example

This example demonstrates how to connect to the Hibachi WebSocket market data stream
to receive real-time market updates for:
- Mark Prices: The fair value price used for liquidation calculations
- Trades: Real-time trade executions on the exchange

The client uses an event-driven architecture where you subscribe to specific topics
and register handlers to process incoming messages. This example shows how to:
1. Establish a WebSocket connection
2. Subscribe to multiple market data topics
3. Register custom event handlers for each topic
4. Handle graceful shutdown and cleanup
"""

import asyncio

from hibachi_xyz import (
    HibachiWSMarketClient,
    WebSocketSubscription,
    WebSocketSubscriptionTopic,
)


async def example_ws_market(max_messages: int | None = None) -> list[str] | None:
    """
    Connect to the Hibachi WebSocket market data stream.

    Args:
        max_messages: Optional limit on number of messages to receive before exiting.
                     If None, runs indefinitely until Ctrl+C.
    """
    # ======================================================================
    # Setup & Connection
    # ======================================================================
    print("=" * 70)
    print("Hibachi WebSocket Market Data Client Example")
    print("=" * 70)
    print("\n[Setup] Initializing market data WebSocket client...")
    client = HibachiWSMarketClient()

    print("[Connecting] Establishing WebSocket connection...")
    await client.connect()
    print("[SUCCESS] WebSocket connected!\n")

    # ======================================================================
    # Define Subscriptions
    # ======================================================================
    print("[Subscriptions] Configuring market data subscriptions...")
    subscriptions = [
        WebSocketSubscription(
            symbol="BTC/USDT-P", topic=WebSocketSubscriptionTopic.MARK_PRICE
        ),
        WebSocketSubscription(
            symbol="BTC/USDT-P", topic=WebSocketSubscriptionTopic.TRADES
        ),
    ]
    print(f"[Subscriptions] Will subscribe to {len(subscriptions)} topics:")
    print("  - BTC/USDT-P: Mark Price (fair value for liquidations)")
    print("  - BTC/USDT-P: Trades (real-time executions)\n")

    # ======================================================================
    # Register Event Handlers
    # ======================================================================
    print("[Setup] Registering event handlers for each topic...")

    # Handler for mark price updates
    async def handle_mark_price(msg: object) -> None:
        """Process incoming mark price updates."""
        print(f"[Mark Price Update] {msg}")

    # Handler for trade executions
    async def handle_trades(msg: object) -> None:
        """Process incoming trade execution messages."""
        print(f"[Trade Execution] {msg}")

    # Register the handlers with the client
    client.on("mark_price", handle_mark_price)
    client.on("trades", handle_trades)
    print("[Setup] Event handlers registered.\n")

    # ======================================================================
    # Subscribe to Market Data
    # ======================================================================
    print("[Subscribing] Sending subscription requests...")
    await client.subscribe(subscriptions)
    print("[SUCCESS] Subscribed to all market data topics!\n")

    # Storage for received messages (used when max_messages is set)
    received: list[str] = []

    # ======================================================================
    # Main Message Loop
    # ======================================================================
    try:
        if max_messages is None:
            # Continuous mode: run until user interrupts
            print("[Listening] Waiting for real-time market data updates...")
            print("[Info] Event handlers will process messages as they arrive.")
            print("[Info] Press Ctrl+C to stop.\n")
            print("=" * 70)
            while True:
                await asyncio.sleep(1)
        else:
            # Limited mode: collect specific number of raw messages
            print(f"[Listening] Collecting {max_messages} raw messages...")
            print("[Info] In this mode, raw WebSocket messages are captured.\n")
            print("=" * 70)
            while len(received) < max_messages:
                msg = await client.websocket.recv()
                print(f"[Raw Message #{len(received) + 1}] {msg}")
                received.append(msg)
            print("=" * 70)
            print(f"[Complete] Received {max_messages} messages.\n")
            return received

    except KeyboardInterrupt:
        print("\n" + "=" * 70)
        print("[Shutdown] Ctrl+C detected. Initiating graceful shutdown...")

    finally:
        # ======================================================================
        # Cleanup
        # ======================================================================
        print("[Cleanup] Unsubscribing from all topics...")
        await client.unsubscribe(subscriptions)
        print("[Cleanup] Closing WebSocket connection...")
        await client.disconnect()
        print("[Done] Gracefully exited.")
        print("=" * 70)

    return None


if __name__ == "__main__":
    """
    Run the WebSocket market data client example.

    Usage:
        python example_ws_market.py

    This example connects to public market data streams and does not require
    authentication or API keys.

    Press Ctrl+C to stop the example.
    """
    import sys

    try:
        asyncio.run(example_ws_market())
    except KeyboardInterrupt:
        print("\n[Exit] Keyboard interrupt received. Shutting down cleanly.")
        sys.exit(0)
