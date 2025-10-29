"""
WebSocket Account Client Example

This example demonstrates how to connect to the Hibachi WebSocket account stream
to receive real-time updates for:
- Balance changes (deposits, withdrawals, PnL updates)
- Position updates (opens, closes, size changes)

The example includes automatic reconnection logic with exponential backoff.
"""

import asyncio
import time
from datetime import datetime, timezone

from hibachi_xyz import HibachiWSAccountClient, print_data
from hibachi_xyz.env_setup import setup_environment
from hibachi_xyz.types import JsonValue


def now() -> str:
    """Return current UTC timestamp in readable format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


async def handle_balance(msg: object) -> None:
    """Handle incoming balance update messages."""
    print(f"[{now()}] [Balance Update] {msg}")


async def handle_position(msg: object) -> None:
    """Handle incoming position update messages."""
    print(f"[{now()}] [Position Update] {msg}")


async def example_ws_account(
    max_messages: int | None = None,
) -> list[dict[str, JsonValue]] | None:
    """
    Connect to the Hibachi WebSocket account stream.

    Args:
        max_messages: Optional limit on number of messages to receive before exiting.
                     If None, runs indefinitely until Ctrl+C.
    """
    print("=" * 60)
    print("Hibachi WebSocket Account Client Example")
    print("=" * 60)
    print("\n[Setup] Loading environment variables from .env file...")
    api_endpoint, _, api_key, account_id, _, _, _ = setup_environment()
    ws_base_url = api_endpoint.replace("https://", "wss://")
    print(f"[Setup] WebSocket endpoint: {ws_base_url}")
    print(f"[Setup] Account ID: {account_id}\n")

    # Reconnection configuration
    attempt = 1
    backoff = 1  # Start with 1 second backoff, doubles on each retry

    # Main connection loop with automatic reconnection
    while True:
        print(
            f"[{now()}] [Connection Attempt #{attempt}] Establishing WebSocket connection..."
        )
        client = HibachiWSAccountClient(
            api_endpoint=ws_base_url, api_key=api_key, account_id=str(account_id)
        )

        # Register event handlers for real-time updates
        print("[Setup] Registering event handlers...")
        client.on("balance_update", handle_balance)
        client.on("position_update", handle_position)

        start_time = time.time()
        try:
            # Establish WebSocket connection
            await client.connect()
            print(f"[{now()}] [SUCCESS] WebSocket connected!")

            # Start the account stream
            result_start = await client.stream_start()
            print("\n[Stream Started] Initial stream status:")
            print_data(result_start)

            print(
                "\n[Listening] Waiting for real-time account updates (Ctrl+C to stop)..."
            )
            print(
                "[Info] You will see balance updates and position changes as they happen.\n"
            )
            last_msg_time = time.time()
            received = []

            # Main message listening loop
            while True:
                message = await client.listen()

                # Handle heartbeat/ping messages
                if message is None:
                    elapsed = int(time.time() - last_msg_time)
                    print(
                        f"[{now()}] [Heartbeat] No new updates. Ping sent. "
                        f"Last message received {elapsed}s ago."
                    )
                    continue

                # Process actual account updates
                last_msg_time = time.time()
                print(f"\n[{now()}] [New Message] Received account update:")
                print_data(message)
                received.append(message)

                # Check if we've reached the message limit
                if max_messages is not None and len(received) >= max_messages:
                    print(
                        f"\n[{now()}] [Complete] Received {max_messages} messages. Exiting."
                    )
                    break

            if max_messages is not None:
                return received

        except asyncio.CancelledError:
            print(f"\n[{now()}] [Shutdown] Cancellation detected. Cleaning up...")
            await client.disconnect()
            break

        except Exception as e:
            print(f"\n[{now()}] [ERROR] Connection failed: {e}")
            print(f"[Error Details] Type: {type(e).__name__}")

        finally:
            duration = time.time() - start_time
            print(f"[{now()}] [Disconnected] Connection lasted {duration:.2f} seconds.")
            await client.disconnect()
            print(f"[{now()}] [Cleanup] Client resources released.")

        # Exit if we were limiting messages
        if max_messages is not None:
            break

        # Exponential backoff for reconnection
        print(f"\n[{now()}] [Reconnecting] Waiting {backoff} seconds before retry...\n")
        try:
            await asyncio.sleep(backoff)
        except asyncio.CancelledError:
            print(f"[{now()}] [Cancelled] Shutdown during reconnection wait. Exiting.")
            break

        attempt += 1
        backoff = min(backoff * 2, 60)  # Cap at 60 seconds

    return None


if __name__ == "__main__":
    """
    Run the WebSocket account client example.

    Usage:
        python example_ws_account.py

    Environment Variables Required:
        - HIBACHI_API_ENDPOINT: API endpoint URL
        - HIBACHI_API_KEY: Your API key
        - HIBACHI_ACCOUNT_ID: Your account ID

    Press Ctrl+C to stop the example.
    """
    try:
        asyncio.run(example_ws_account())
    except KeyboardInterrupt:
        print(
            f"\n[{now()}] [Exit] KeyboardInterrupt received. Shutting down gracefully."
        )
        print("[Done] Example completed successfully.")
