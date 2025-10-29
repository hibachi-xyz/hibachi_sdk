"""
WebSocket Trade Client Example

This example demonstrates how to use Hibachi's WebSocket Trade Client for
real-time order management and account operations. WebSocket connections provide
lower latency compared to REST API calls, making them ideal for active trading.

The WebSocket Trade Client supports:
- Real-time order placement (market, limit, trigger orders)
- Real-time order modification and cancellation
- Live order status monitoring
- Immediate order confirmations

This example shows:
1. Setting up and connecting to the WebSocket trade endpoint
2. Querying order status via WebSocket vs REST API
3. Placing orders using both REST API and WebSocket
4. Modifying orders in real-time via WebSocket
5. Cancelling orders via WebSocket

Key Differences - WebSocket vs REST:
- WebSocket: Lower latency, persistent connection, real-time updates
- REST API: Request/response pattern, higher latency, stateless

Environment Variables Required:
- HIBACHI_API_ENDPOINT: API endpoint URL
- HIBACHI_DATA_API_ENDPOINT: Data API endpoint URL
- HIBACHI_API_KEY: Your API key
- HIBACHI_ACCOUNT_ID: Your account ID
- HIBACHI_PRIVATE_KEY: Your private key for signing
- HIBACHI_PUBLIC_KEY: Your public key for authentication
"""

import asyncio

from hibachi_xyz import HibachiWSTradeClient, print_data
from hibachi_xyz.env_setup import setup_environment
from hibachi_xyz.types import OrderPlaceParams, OrderType, Side


async def example_ws_trade() -> None:
    """Demonstrate WebSocket trading operations and order management."""

    print("=" * 70)
    print("Hibachi WebSocket Trade Client Example")
    print("=" * 70)

    # ==================================================================
    # SETUP: Load credentials and initialize WebSocket client
    # ==================================================================
    print("\n[Setup] Loading credentials from environment...")
    api_endpoint, data_api_endpoint, api_key, account_id, private_key, public_key, _ = (
        setup_environment()
    )
    print(f"[Setup] Account ID: {account_id}")
    print(f"[Setup] API Endpoint: {api_endpoint}")

    # Initialize WebSocket Trade Client
    # Note: The client includes both WebSocket capabilities AND a REST API client
    print("\n[Setup] Initializing WebSocket trade client...")
    client = HibachiWSTradeClient(
        api_url=api_endpoint,
        api_key=api_key,
        account_id=account_id,
        account_public_key=public_key,
        private_key=private_key,
    )
    print("[Setup] Client initialized successfully!")

    try:
        # ==================================================================
        # PART 1: ESTABLISH WEBSOCKET CONNECTION
        # ==================================================================
        print("\n" + "=" * 70)
        print("PART 1: ESTABLISHING WEBSOCKET CONNECTION")
        print("=" * 70)

        print("\n[WebSocket] Connecting to trade endpoint...")
        await client.connect()
        print("[WebSocket] Connected successfully! Ready for real-time trading.\n")

        # ==================================================================
        # PART 2: CLEAN SLATE - CANCEL ALL EXISTING ORDERS
        # ==================================================================
        print("=" * 70)
        print("PART 2: PREPARING CLEAN TEST ENVIRONMENT")
        print("=" * 70)

        print("\n[REST API] Cancelling all existing orders to start fresh...")
        client.api.cancel_all_orders()
        print("[REST API] All orders cancelled.\n")

        # ==================================================================
        # PART 3: VERIFY EMPTY ORDER BOOK (WebSocket vs REST)
        # ==================================================================
        print("=" * 70)
        print("PART 3: VERIFYING EMPTY ORDER BOOK")
        print("=" * 70)

        # Check via WebSocket
        print("\n[WebSocket] Fetching order status via WebSocket...")
        orders_start = await client.get_orders_status()
        print_data(orders_start)

        # Verify empty order list
        print(f"[WebSocket] Orders found: {len(orders_start.result)}")
        assert len(orders_start.result) == 0
        print("[WebSocket] Confirmed: No pending orders.\n")

        # Cross-check with REST API
        print("[REST API] Cross-verifying with REST API...")
        orders_rest = client.api.get_pending_orders()
        print_data(orders_rest)

        print(f"[REST API] Orders found: {len(orders_rest.orders)}")
        assert len(orders_rest.orders) == 0
        print("[REST API] Confirmed: No pending orders.\n")

        # ==================================================================
        # PART 4: PLACE ORDER VIA REST API
        # ==================================================================
        print("=" * 70)
        print("PART 4: PLACING ORDER VIA REST API")
        print("=" * 70)

        # Get current market prices
        print("\n[Market Data] Fetching current BTC/USDT-P prices...")
        current_price = client.api.get_prices("BTC/USDT-P")
        print(f"[Market Data] Current Ask Price: ${current_price.askPrice}")
        print(f"[Market Data] Current Bid Price: ${current_price.bidPrice}")
        print(f"[Market Data] Current Mark Price: ${current_price.markPrice}\n")

        # Place a limit order using REST API
        order_price = float(current_price.askPrice) * 1.05
        print(
            f"[REST API] Placing limit order to SELL 0.0001 BTC at ${order_price:.2f}"
        )
        print(f"[REST API] This is {5}% above current ask price")

        (nonce, order_id) = client.api.place_limit_order(
            symbol="BTC/USDT-P",
            quantity=0.0001,
            side=Side.ASK,
            max_fees_percent=0.005,
            price=order_price,
        )
        print("[REST API] Order placed successfully!")
        print(f"[REST API]   Nonce: {nonce}")
        print(f"[REST API]   Order ID: {order_id}\n")

        # ==================================================================
        # PART 5: VERIFY ORDER VIA WEBSOCKET AND REST
        # ==================================================================
        print("=" * 70)
        print("PART 5: VERIFYING ORDER PLACEMENT")
        print("=" * 70)

        # Check via WebSocket
        print("\n[WebSocket] Fetching order status via WebSocket...")
        orders_start = await client.get_orders_status()
        print(f"[WebSocket] Found {len(orders_start.result)} order(s)")

        # Cross-verify with REST API
        print("\n[REST API] Cross-verifying with REST API...")
        orders_rest = client.api.get_pending_orders()
        print(f"[REST API] Found {len(orders_rest.orders)} order(s)\n")

        # ==================================================================
        # PART 6: CANCEL ALL ORDERS VIA WEBSOCKET
        # ==================================================================
        print("=" * 70)
        print("PART 6: CANCELLING ORDERS VIA WEBSOCKET")
        print("=" * 70)

        print("\n[WebSocket] Cancelling all orders via WebSocket...")
        await client.cancel_all_orders()
        print("[WebSocket] All orders cancelled successfully!")
        print("[WebSocket] Order book cleared for next test.\n")

        # ==================================================================
        # PART 7: PLACE ORDER VIA WEBSOCKET
        # ==================================================================
        print("=" * 70)
        print("PART 7: PLACING ORDER VIA WEBSOCKET")
        print("=" * 70)

        # Place a limit order using WebSocket (lower latency than REST)
        price_before = float(current_price.askPrice) * 0.9
        print(
            f"\n[WebSocket] Placing limit order to BUY 0.0001 BTC at ${price_before:.2f}"
        )
        print(f"[WebSocket] This is {10}% below current ask price")
        print("[WebSocket] Using WebSocket for lower latency...")

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

        print("[WebSocket] Order placed successfully!")
        print(f"[WebSocket]   Nonce: {nonce}")
        print(f"[WebSocket]   Order ID: {order_id}\n")

        # Get order details via WebSocket
        print("[WebSocket] Fetching order details via WebSocket...")
        order = await client.get_order_status(order_id)
        print(f"[WebSocket] Order Status: {order.result.status}")
        print(f"[WebSocket] Order Price: ${order.result.price}")
        print(f"[WebSocket] Order Quantity: {order.result.totalQuantity}\n")

        # ==================================================================
        # PART 8: VERIFY ORDER WITH REST API
        # ==================================================================
        print("=" * 70)
        print("PART 8: CROSS-VERIFYING WITH REST API")
        print("=" * 70)

        # Cross-verify the WebSocket order using REST API
        print("\n[REST API] Fetching order details via REST API...")
        order_details = client.api.get_order_details(order_id=int(order.result.orderId))
        print("[REST API] Order details fetched successfully:")
        print_data(order_details)

        # ==================================================================
        # PART 9: MODIFY ORDER VIA WEBSOCKET
        # ==================================================================
        print("\n" + "=" * 70)
        print("PART 9: MODIFYING ORDER VIA WEBSOCKET")
        print("=" * 70)

        # Modify the order price slightly
        price_after = float(current_price.askPrice) * 0.91
        print(
            f"\n[WebSocket] Modifying order price from ${price_before:.2f} to ${price_after:.2f}"
        )
        print(f"[WebSocket] New price is {9}% below current ask price")

        await client.modify_order(
            order=order.result,
            quantity=0.0001,
            price=str(price_after),
            side=order.result.side,
            maxFeesPercent=0.0005,
            nonce=nonce + 1,
        )

        print("[WebSocket] Order modified successfully!")
        print(f"[WebSocket]   New Nonce: {nonce + 1}")
        print(f"[WebSocket]   New Price: ${price_after:.2f}\n")

        # ==================================================================
        # PART 10: FINAL VERIFICATION
        # ==================================================================
        print("=" * 70)
        print("PART 10: FINAL ORDER STATUS VERIFICATION")
        print("=" * 70)

        print("\n[WebSocket] Fetching final order status...")
        orders_end = await client.get_orders_status()
        print(f"[WebSocket] Current order count: {len(orders_end.result)}")
        print_data(orders_end)
        print("\n[WebSocket] Example completed successfully!")

    except Exception as e:
        # Handle any errors that occur during execution
        print(f"\n[Error] An error occurred: {e}")
        raise

    finally:
        # ==================================================================
        # CLEANUP: Always disconnect WebSocket connection
        # ==================================================================
        print("\n" + "=" * 70)
        print("CLEANUP: CLOSING WEBSOCKET CONNECTION")
        print("=" * 70)

        print("\n[WebSocket] Disconnecting from trade endpoint...")
        await client.disconnect()
        print("[WebSocket] Disconnected successfully!")
        print("[Done] Example execution completed.\n")


# Command line usage
if __name__ == "__main__":
    """
    Run the WebSocket trade example.

    This example demonstrates the full lifecycle of WebSocket trading:
    - Connection establishment
    - Order placement and monitoring
    - Order modification
    - Comparison between WebSocket and REST API operations
    """
    try:
        asyncio.run(example_ws_trade())
    except KeyboardInterrupt:
        print("\n[Exit] Keyboard interrupt received. Shutting down cleanly.")
    except Exception as e:
        print(f"\n[Exit] Example failed with error: {e}")
