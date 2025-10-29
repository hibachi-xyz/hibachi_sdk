"""
Take Profit / Stop Loss (TPSL) Orders Example

This example demonstrates how to use TPSL (Take Profit / Stop Loss) orders
with Hibachi's trading API. TPSL orders are risk management tools that
automatically close positions when the market reaches specified price levels.

What are TPSL Orders?
---------------------
- TAKE PROFIT: Automatically closes a position at a profit target
  (e.g., sell when price rises 10% for a long position)

- STOP LOSS: Automatically closes a position to limit losses
  (e.g., sell when price drops 10% for a long position)

Key Features:
-------------
1. Attached TPSLs: Add TPSL orders when opening a position
   - Automatically linked to the parent order
   - Can specify multiple TP/SL levels with different quantities

2. Standalone TPSLs: Add TPSL orders to existing positions
   - Created as trigger orders with ReduceOnly flag
   - Ensures they only close positions, never increase them

3. Partial Closes: Define different quantities for each TP/SL level
   - e.g., Take 25% profit at +20%, take remaining 75% at +10%
   - Scale out of positions at multiple price levels

Use Cases:
----------
- Protect profits by automatically selling when targets are reached
- Limit losses by exiting positions before losses grow too large
- Implement multi-level exit strategies (scaling out)
- Reduce emotional trading decisions with predefined exit points

Environment Variables Required:
-------------------------------
- HIBACHI_API_ENDPOINT: API endpoint URL
- HIBACHI_DATA_API_ENDPOINT: Data API endpoint URL
- HIBACHI_API_KEY: Your API key
- HIBACHI_ACCOUNT_ID: Your account ID
- HIBACHI_PRIVATE_KEY: Your private key for signing
- HIBACHI_PUBLIC_KEY: Your public key (for WebSocket example)
"""

import asyncio

from hibachi_xyz import (
    HibachiApiClient,
    HibachiWSTradeClient,
    TPSLConfig,
)
from hibachi_xyz.env_setup import setup_environment
from hibachi_xyz.types import (
    OrderFlags,
    Side,
)


def example_tpsl_rest() -> None:
    """Demonstrate TPSL orders using the REST API client."""

    print("=" * 70)
    print("Hibachi TPSL Orders Example (REST API)")
    print("=" * 70)

    # ==================================================================
    # SETUP: Initialize Client and Get Market Data
    # ==================================================================
    print("\n[Setup] Loading credentials from environment...")
    api_endpoint, data_api_endpoint, api_key, account_id, private_key, _, _ = (
        setup_environment()
    )
    print(f"[Setup] Account ID: {account_id}")

    print("[Setup] Initializing API client...")
    hibachi = HibachiApiClient(
        api_url=api_endpoint,
        data_api_url=data_api_endpoint,
        api_key=api_key,
        account_id=account_id,
        private_key=private_key,
    )
    print("[Setup] Client initialized successfully!\n")

    # Get exchange configuration and current market prices
    print("[Setup] Fetching exchange info and market prices...")
    exch_info = hibachi.get_exchange_info()
    prices = hibachi.get_prices("SOL/USDT-P")

    print(f"[Info] SOL/USDT-P Mark Price: ${prices.markPrice}")
    print(f"[Info] Taker Fee Rate: {exch_info.feeConfig.tradeTakerFeeRate}")

    # Calculate maximum acceptable fees (2x taker rate for safety margin)
    max_fees_percent = float(exch_info.feeConfig.tradeTakerFeeRate) * 2.0

    # Position size for examples
    position_quantity = 0.02
    print(f"[Info] Position Quantity: {position_quantity} SOL\n")

    # ==================================================================
    # EXAMPLE 1: Limit Order with Attached TPSL
    # ==================================================================
    print("=" * 70)
    print("EXAMPLE 1: Limit Order with Simple TPSL")
    print("=" * 70)
    print("\n[Trading] Placing limit order with attached TPSL orders...")
    print(f"[Trading] Entry: Limit buy at ${prices.markPrice} (current mark price)")
    print(f"[Trading] Take Profit: +10% at ${float(prices.markPrice) * 1.10:.2f}")
    print(f"[Trading] Stop Loss: -10% at ${float(prices.markPrice) * 0.9:.2f}")

    # Place a limit order at the current mark price with TPSL orders
    # The TPSLs will automatically close the position when price targets are hit
    (nonce, order_id) = hibachi.place_limit_order(
        symbol="SOL/USDT-P",
        quantity=position_quantity,
        price=float(prices.markPrice),
        side=Side.BID,
        max_fees_percent=max_fees_percent,
        tpsl=TPSLConfig()
        .add_take_profit(price=float(prices.markPrice) * 1.10)
        .add_stop_loss(price=float(prices.markPrice) * 0.9),
    )

    print("[Success] Order placed!")
    print(f"[Success] Order ID: {order_id}")
    print(f"[Success] Nonce: {nonce}\n")

    # ==================================================================
    # EXAMPLE 2: Market Order with Multiple TPSL Levels
    # ==================================================================
    print("=" * 70)
    print("EXAMPLE 2: Market Order with Multi-Level TPSL (Scaling Out)")
    print("=" * 70)
    print("\n[Trading] Placing market order with multiple TPSL levels...")
    print("[Trading] Entry: Market buy at current price")
    print("\n[Trading] Multi-Level Exit Strategy:")
    print(
        f"  Take Profit 1: +20% at ${float(prices.markPrice) * 1.20:.2f} (25% of position)"
    )
    print(
        f"  Take Profit 2: +10% at ${float(prices.markPrice) * 1.10:.2f} (75% of position)"
    )
    print(
        f"  Stop Loss 1:   -10% at ${float(prices.markPrice) * 0.9:.2f} (75% of position)"
    )
    print(
        f"  Stop Loss 2:   -15% at ${float(prices.markPrice) * 0.85:.2f} (remaining position)"
    )

    # Place a market order with multiple TPSL levels for scaling out
    # This allows you to take partial profits at different levels
    # and protect remaining position with multiple stop losses
    (nonce, order_id) = hibachi.place_market_order(
        symbol="SOL/USDT-P",
        quantity=position_quantity,
        side=Side.BID,
        max_fees_percent=max_fees_percent,
        tpsl=TPSLConfig()
        .add_take_profit(
            price=float(prices.markPrice) * 1.20, quantity=position_quantity * 0.25
        )
        .add_take_profit(
            price=float(prices.markPrice) * 1.10, quantity=position_quantity * 0.75
        )
        .add_stop_loss(
            price=float(prices.markPrice) * 0.9, quantity=position_quantity * 0.75
        )
        .add_stop_loss(price=float(prices.markPrice) * 0.85),
    )

    print("\n[Success] Order placed with multi-level TPSLs!")
    print(f"[Success] Order ID: {order_id}")
    print(f"[Success] Nonce: {nonce}")
    print("[Info] This strategy scales out of the position at different price levels\n")

    # ==================================================================
    # EXAMPLE 3: Standalone TPSL Orders on Existing Position
    # ==================================================================
    print("=" * 70)
    print("EXAMPLE 3: Adding TPSL to Existing Position")
    print("=" * 70)
    print("\n[Info] TPSL orders can also be placed on existing positions")
    print("[Info] These are trigger orders with the ReduceOnly flag")
    print("[Info] ReduceOnly ensures they only close positions, never increase them\n")

    # Assuming we have an existing long position of 0.02 SOL
    # entered at the current mark price, we can add standalone TPSL orders

    print("[Trading] Placing standalone Take Profit order...")
    print(
        f"[Trading] Take profit for 75% of position at +10% (${float(prices.markPrice) * 1.10:.2f})"
    )

    # Standalone Take Profit: Close 75% of position at +10% profit
    (nonce, order_id) = hibachi.place_market_order(
        symbol="SOL/USDT-P",
        quantity=position_quantity * 0.75,
        side=Side.ASK,
        max_fees_percent=max_fees_percent,
        trigger_price=float(prices.markPrice) * 1.10,
        order_flags=OrderFlags.ReduceOnly,
    )

    print("[Success] Take Profit order placed!")
    print(f"[Success] Order ID: {order_id}\n")

    print("[Trading] Placing standalone Stop Loss order...")
    print(
        f"[Trading] Stop loss for 50% of position at -10% (${float(prices.markPrice) * 0.9:.2f})"
    )

    # Standalone Stop Loss: Close 50% of position at -10% loss
    (nonce, order_id) = hibachi.place_market_order(
        symbol="SOL/USDT-P",
        quantity=position_quantity * 0.5,
        side=Side.ASK,
        max_fees_percent=max_fees_percent,
        trigger_price=float(prices.markPrice) * 0.9,
        order_flags=OrderFlags.ReduceOnly,
    )

    print("[Success] Stop Loss order placed!")
    print(f"[Success] Order ID: {order_id}")
    print("\n[Complete] All TPSL examples finished!\n")


async def example_tpsl_ws_client() -> None:
    """Demonstrate TPSL orders using the WebSocket Trade client."""

    print("=" * 70)
    print("Hibachi TPSL Orders Example (WebSocket API)")
    print("=" * 70)

    # ==================================================================
    # SETUP: Initialize WebSocket Client and Get Market Data
    # ==================================================================
    print("\n[Setup] Loading credentials from environment...")
    api_endpoint, data_api_endpoint, api_key, account_id, private_key, public_key, _ = (
        setup_environment()
    )
    print(f"[Setup] Account ID: {account_id}")

    print("[Setup] Initializing WebSocket trade client...")
    client = HibachiWSTradeClient(
        api_url=api_endpoint,
        data_api_url=data_api_endpoint,
        api_key=api_key,
        account_id=account_id,
        private_key=private_key,
        account_public_key=public_key,
    )

    print("[Setup] Connecting to WebSocket...")
    await client.connect()
    print("[Setup] WebSocket connected successfully!\n")

    # Note: The WebSocket client still uses REST for trading operations
    # WebSocket is primarily for receiving real-time updates
    print("[Setup] Fetching exchange info and market prices...")
    exch_info = client.api.get_exchange_info()
    prices = client.api.get_prices("SOL/USDT-P")

    print(f"[Info] SOL/USDT-P Mark Price: ${prices.markPrice}")
    print(f"[Info] Taker Fee Rate: {exch_info.feeConfig.tradeTakerFeeRate}")

    # Calculate maximum acceptable fees (2x taker rate for safety margin)
    max_fees_percent = float(exch_info.feeConfig.tradeTakerFeeRate) * 2.0

    # Position size for examples
    position_quantity = 0.02
    print(f"[Info] Position Quantity: {position_quantity} SOL\n")

    # ==================================================================
    # EXAMPLE 1: Limit Order with Attached TPSL
    # ==================================================================
    print("=" * 70)
    print("EXAMPLE 1: Limit Order with Simple TPSL")
    print("=" * 70)
    print("\n[Trading] Placing limit order with attached TPSL orders...")
    print(f"[Trading] Entry: Limit buy at ${prices.markPrice} (current mark price)")
    print(f"[Trading] Take Profit: +10% at ${float(prices.markPrice) * 1.10:.2f}")
    print(f"[Trading] Stop Loss: -10% at ${float(prices.markPrice) * 0.9:.2f}")

    # Place a limit order at the current mark price with TPSL orders
    # The TPSLs will automatically close the position when price targets are hit
    (nonce, order_id) = client.api.place_limit_order(
        symbol="SOL/USDT-P",
        quantity=position_quantity,
        price=float(prices.markPrice),
        side=Side.BID,
        max_fees_percent=max_fees_percent,
        tpsl=TPSLConfig()
        .add_take_profit(price=float(prices.markPrice) * 1.10)
        .add_stop_loss(price=float(prices.markPrice) * 0.9),
    )

    print("[Success] Order placed!")
    print(f"[Success] Order ID: {order_id}")
    print(f"[Success] Nonce: {nonce}\n")

    # ==================================================================
    # EXAMPLE 2: Market Order with Multiple TPSL Levels
    # ==================================================================
    print("=" * 70)
    print("EXAMPLE 2: Market Order with Multi-Level TPSL (Scaling Out)")
    print("=" * 70)
    print("\n[Trading] Placing market order with multiple TPSL levels...")
    print("[Trading] Entry: Market buy at current price")
    print("\n[Trading] Multi-Level Exit Strategy:")
    print(
        f"  Take Profit 1: +20% at ${float(prices.markPrice) * 1.20:.2f} (25% of position)"
    )
    print(
        f"  Take Profit 2: +10% at ${float(prices.markPrice) * 1.10:.2f} (75% of position)"
    )
    print(
        f"  Stop Loss 1:   -10% at ${float(prices.markPrice) * 0.9:.2f} (75% of position)"
    )
    print(
        f"  Stop Loss 2:   -15% at ${float(prices.markPrice) * 0.85:.2f} (remaining position)"
    )

    # Place a market order with multiple TPSL levels for scaling out
    # This allows you to take partial profits at different levels
    # and protect remaining position with multiple stop losses
    (nonce, order_id) = client.api.place_market_order(
        symbol="SOL/USDT-P",
        quantity=position_quantity,
        side=Side.BID,
        max_fees_percent=max_fees_percent,
        tpsl=TPSLConfig()
        .add_take_profit(
            price=float(prices.markPrice) * 1.20, quantity=position_quantity * 0.25
        )
        .add_take_profit(
            price=float(prices.markPrice) * 1.10, quantity=position_quantity * 0.75
        )
        .add_stop_loss(
            price=float(prices.markPrice) * 0.9, quantity=position_quantity * 0.75
        )
        .add_stop_loss(price=float(prices.markPrice) * 0.85),
    )

    print("\n[Success] Order placed with multi-level TPSLs!")
    print(f"[Success] Order ID: {order_id}")
    print(f"[Success] Nonce: {nonce}")
    print("[Info] This strategy scales out of the position at different price levels\n")

    # ==================================================================
    # EXAMPLE 3: Standalone TPSL Orders on Existing Position
    # ==================================================================
    print("=" * 70)
    print("EXAMPLE 3: Adding TPSL to Existing Position")
    print("=" * 70)
    print("\n[Info] TPSL orders can also be placed on existing positions")
    print("[Info] These are trigger orders with the ReduceOnly flag")
    print("[Info] ReduceOnly ensures they only close positions, never increase them\n")

    # Assuming we have an existing long position of 0.02 SOL
    # entered at the current mark price, we can add standalone TPSL orders

    print("[Trading] Placing standalone Take Profit order...")
    print(
        f"[Trading] Take profit for 75% of position at +10% (${float(prices.markPrice) * 1.10:.2f})"
    )

    # Standalone Take Profit: Close 75% of position at +10% profit
    (nonce, order_id) = client.api.place_market_order(
        symbol="SOL/USDT-P",
        quantity=position_quantity * 0.75,
        side=Side.ASK,
        max_fees_percent=max_fees_percent,
        trigger_price=float(prices.markPrice) * 1.10,
        order_flags=OrderFlags.ReduceOnly,
    )

    print("[Success] Take Profit order placed!")
    print(f"[Success] Order ID: {order_id}\n")

    print("[Trading] Placing standalone Stop Loss order...")
    print(
        f"[Trading] Stop loss for 50% of position at -10% (${float(prices.markPrice) * 0.9:.2f})"
    )

    # Standalone Stop Loss: Close 50% of position at -10% loss
    (nonce, order_id) = client.api.place_market_order(
        symbol="SOL/USDT-P",
        quantity=position_quantity * 0.5,
        side=Side.ASK,
        max_fees_percent=max_fees_percent,
        trigger_price=float(prices.markPrice) * 0.9,
        order_flags=OrderFlags.ReduceOnly,
    )

    print("[Success] Stop Loss order placed!")
    print(f"[Success] Order ID: {order_id}")
    print("\n[Complete] All TPSL examples finished!\n")


if __name__ == "__main__":
    """
    Run TPSL examples.

    Uncomment the example you want to run:
    - example_tpsl_rest(): REST API client examples
    - example_tpsl_ws_client(): WebSocket client examples (both use same trading operations)
    """
    # Run REST API example
    # example_tpsl_rest()

    # Run WebSocket API example
    asyncio.run(example_tpsl_ws_client())
