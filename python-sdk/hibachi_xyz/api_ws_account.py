"""WebSocket client for account data streams.

This module provides the HibachiWSAccountClient for streaming real-time
account updates including balance changes and position updates via WebSocket.
"""

import asyncio
import logging
import time

import orjson

from hibachi_xyz.connection import connect_with_retry
from hibachi_xyz.errors import ValidationError, WebSocketConnectionError
from hibachi_xyz.executors import DEFAULT_WS_EXECUTOR, WsConnection, WsExecutor
from hibachi_xyz.helpers import DEFAULT_API_URL, create_with, get_hibachi_client
from hibachi_xyz.types import (
    AccountSnapshot,
    AccountStreamStartResult,
    Json,
    Position,
    WsEventHandler,
)

log = logging.getLogger(__name__)


class HibachiWSAccountClient:
    """WebSocket client for streaming Hibachi account data.

    Provides real-time updates for account balances and positions via WebSocket connection.
    """

    def __init__(
        self,
        api_key: str,
        account_id: str,
        api_endpoint: str = DEFAULT_API_URL,
        executor: WsExecutor | None = None,
    ):
        """Initialize the Hibachi WebSocket Account Client.

        Args:
            api_key: The API key for authentication with the Hibachi API.
            account_id: The account ID to stream data for.
            api_endpoint: The base API endpoint URL. Defaults to DEFAULT_API_URL.
                Will be converted from https:// to wss:// protocol.
            executor: Optional WebSocket executor for handling connections. If None,
                uses the default executor.

        """
        self.api_endpoint = api_endpoint.replace("https://", "wss://") + "/ws/account"
        self._websocket: WsConnection | None = None
        self.message_id = 0
        self.api_key = api_key
        self.account_id = int(account_id)
        self.listenKey: str | None = None
        self._event_handlers: dict[str, list[WsEventHandler]] = {}
        self._executor: WsExecutor = (
            executor if executor is not None else DEFAULT_WS_EXECUTOR()
        )

    @property
    def websocket(self) -> WsConnection:
        """Get the active WebSocket connection.

        Returns:
            The active WebSocket connection.

        Raises:
            ValidationError: If no WebSocket connection exists. Must call connect() first.

        """
        if self._websocket is None:
            raise ValidationError from ValueError(
                "No existing ws connection. Call `connect` first"
            )
        return self._websocket

    def on(self, topic: str, handler: WsEventHandler) -> None:
        """Register an event handler for a specific topic.

        Registers a callback function that will be invoked when messages
        with the specified topic are received from the WebSocket.

        Args:
            topic: The topic name to listen for (e.g., 'account_update', 'position_change').
            handler: An async callback function that accepts a message dictionary.

        """
        if topic not in self._event_handlers:
            self._event_handlers[topic] = []
        self._event_handlers[topic].append(handler)

    async def connect(self) -> None:
        """Establish a WebSocket connection to the account data stream.

        Creates an authenticated WebSocket connection with automatic retry logic
        using the provided API key and account ID.

        Raises:
            WebSocketConnectionError: If connection fails after retry attempts.

        """
        self._websocket = await connect_with_retry(
            web_url=self.api_endpoint
            + f"?accountId={self.account_id}&hibachiClient={get_hibachi_client()}",
            headers=[("Authorization", self.api_key)],
            executor=self._executor,
        )

    def _next_message_id(self) -> int:
        """Generate and return the next message ID.

        Increments the internal message counter and returns the new value.
        Used for tracking request-response pairs in the WebSocket protocol.

        Returns:
            The next sequential message ID.

        """
        self.message_id += 1
        return self.message_id

    def _timestamp(self) -> int:
        """Get the current Unix timestamp in seconds.

        Returns:
            The current time as an integer Unix timestamp (seconds since epoch).

        """
        return int(time.time())

    async def stream_start(self) -> AccountStreamStartResult:
        """Start the account data stream and retrieve the initial snapshot.

        Sends a stream.start request to the WebSocket server and waits for
        the response containing the initial account snapshot and listen key.
        The listen key is stored for subsequent ping operations.

        Returns:
            AccountStreamStartResult containing the account snapshot (balance
            and positions) and the listen key for maintaining the stream.

        Raises:
            ValidationError: If WebSocket connection is not established.
            KeyError: If the response format is unexpected or missing required fields.

        """
        message = {
            "id": self._next_message_id(),
            "method": "stream.start",
            "params": {"accountId": self.account_id},
            "timestamp": self._timestamp(),
        }

        await self.websocket.send(orjson.dumps(message).decode())
        response = await self.websocket.recv()
        response_data = orjson.loads(response)

        snapshot_data = response_data["result"]["accountSnapshot"]
        snapshot = AccountSnapshot(
            account_id=snapshot_data["account_id"],
            balance=snapshot_data["balance"],
            positions=[
                create_with(Position, pos) for pos in snapshot_data["positions"]
            ],
        )

        result = AccountStreamStartResult(
            accountSnapshot=snapshot,
            listenKey=response_data["result"]["listenKey"],
        )

        self.listenKey = result.listenKey
        return result

    async def ping(self) -> None:
        """Send a ping message to keep the account stream alive.

        Sends a stream.ping request with the current listen key to prevent
        the server from closing the stream due to inactivity.

        Raises:
            ValueError: If listenKey is not initialized. Must call stream_start() first.
            ValidationError: If WebSocket connection is not established.

        """
        if not self.listenKey:
            raise ValueError("Cannot send ping: listenKey not initialized.")

        message = {
            "id": self._next_message_id(),
            "method": "stream.ping",
            "params": {"accountId": self.account_id, "listenKey": self.listenKey},
            "timestamp": self._timestamp(),
        }

        await self.websocket.send(orjson.dumps(message).decode())
        response = await self.websocket.recv()
        parsed = orjson.loads(response)
        if parsed.get("status") == 200:
            log.debug("pong!")

    async def listen(self) -> Json | None:
        """Listen for and process a single message from the account stream.

        Waits for a message from the WebSocket with a 15-second timeout.
        If a timeout occurs, automatically sends a ping to keep the stream alive.
        Dispatches received messages to registered event handlers based on topic.

        Returns:
            The parsed message as a JSON dictionary, or None if a timeout occurred
            or the connection was closed.

        Raises:
            ValidationError: If WebSocket connection is not established.
            WebSocketConnectionError: If the WebSocket connection is closed unexpectedly.
            Exception: For any other errors during message processing.

        """
        try:
            response = await asyncio.wait_for(self.websocket.recv(), timeout=15)
            message = orjson.loads(response)

            topic = message.get("topic")
            if topic in self._event_handlers:
                for handler in self._event_handlers[topic]:
                    await handler(message)

            return message  # type: ignore
        except asyncio.TimeoutError:
            await self.ping()
            return None
        except WebSocketConnectionError as e:
            log.warning("WebSocket closed: %s", e)
        except Exception as e:
            log.error("WebSocket closed: %s", e)
            raise
        return None

    async def disconnect(self) -> None:
        """Close the WebSocket connection and clean up resources.

        Closes the WebSocket connection and resets the internal state.
        After calling this method, the client must call connect() and
        stream_start() again before listening for messages.
        """
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
