import asyncio
import time
from datetime import datetime, timezone

from hibachi_xyz import HibachiWSAccountClient, print_data
from hibachi_xyz.env_setup import setup_environment


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


async def handle_balance(msg):
    print(f"[{now()}] [Balance Update] {msg}")


async def handle_position(msg):
    print(f"[{now()}] [Position Update] {msg}")


async def example_ws_account(max_messages: int = None):
    print("Loading environment variables from .env file")
    api_endpoint, _, api_key, account_id, _, _, _ = setup_environment()
    ws_base_url = api_endpoint.replace("https://", "wss://")

    attempt = 1
    backoff = 1  # seconds

    while True:
        print(f"[{now()}] [Attempt {attempt}] Connecting to WebSocket...")
        client = HibachiWSAccountClient(
            api_endpoint=ws_base_url, api_key=api_key, account_id=account_id
        )

        client.on("balance_update", handle_balance)
        client.on("position_update", handle_position)

        start_time = time.time()
        try:
            await client.connect()
            result_start = await client.stream_start()
            print("[Connected] stream_start result:")
            print_data(result_start)

            print("Listening for account WebSocket messages (Ctrl+C to stop)...")
            last_msg_time = time.time()
            received = []

            while True:
                message = await client.listen()
                if message is None:
                    print(
                        f"[{now()}] No message received. (Ping sent.) "
                        f"Last message was {int(time.time() - last_msg_time)}s ago."
                    )
                    continue

                last_msg_time = time.time()
                print_data(message)
                received.append(message)

                if max_messages is not None and len(received) >= max_messages:
                    print(f"[{now()}] Received {max_messages} messages. Exiting.")
                    break

            if max_messages is not None:
                return received

        except asyncio.CancelledError:
            print(f"[{now()}] CancelledError caught. Cleaning up WebSocket connection.")
            await client.disconnect()
            break

        except Exception as e:
            print(f"[Error] {e}")

        finally:
            duration = time.time() - start_time
            print(f"[{now()}] Disconnected. Connection lasted {duration:.2f} seconds.")
            await client.disconnect()
            print(f"[{now()}] Client cleaned up.")

        if max_messages is not None:
            break

        print(f"Reconnecting in {backoff} seconds...\n")
        try:
            await asyncio.sleep(backoff)
        except asyncio.CancelledError:
            print(f"[{now()}] Cancelled during backoff sleep. Exiting.")
            break

        attempt += 1
        backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    try:
        asyncio.run(example_ws_account())
    except KeyboardInterrupt:
        print(f"[{now()}] KeyboardInterrupt received. Exiting cleanly.")
