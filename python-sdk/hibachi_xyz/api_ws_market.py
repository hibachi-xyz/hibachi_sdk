"""WebSocket client for market data streams.

This module provides the HibachiWSMarketClient for subscribing to real-time
market data including prices, order books, and trades via WebSocket.
"""

import asyncio
import logging
from dataclasses import asdict
from typing import Self

import orjson

from hibachi_xyz.connection import connect_with_retry
from hibachi_xyz.errors import ValidationError, WebSocketConnectionError
from hibachi_xyz.executors.defaults import DEFAULT_WS_EXECUTOR
from hibachi_xyz.executors.interface import WsConnection, WsExecutor
from hibachi_xyz.helpers import DEFAULT_DATA_API_URL, get_hibachi_client
from hibachi_xyz.types import WebSocketSubscription, WsEventHandler

log = logging.getLogger(__name__)


class HibachiWSMarketClient:
    """WebSocket client for streaming Hibachi market data.

    Provides real-time market data including mark prices, order books, and trades.
    """

    def __init__(
        self,
        api_endpoint: str = DEFAULT_DATA_API_URL,
        executor: WsExecutor | None = None,
    ):
        """Initialize the Hibachi WebSocket Market Client.

        Args:
            api_endpoint: The base API endpoint URL. Defaults to DEFAULT_DATA_API_URL.
                Will be converted from https:// to wss:// protocol.
            executor: Optional WebSocket executor for handling connections. If None,
                uses the default executor.

        """
        self.api_endpoint = api_endpoint.replace("https://", "wss://") + "/ws/market"
        self._websocket: WsConnection | None = None
        self._event_handlers: dict[str, list[WsEventHandler]] = {}
        self._receive_task: asyncio.Task[None] | None = None
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

    async def connect(self) -> Self:
        """Establish a WebSocket connection to the market data stream.

        Creates a WebSocket connection with automatic retry logic and starts
        the receive loop task to handle incoming messages.

        Returns:
            Self: This instance for method chaining.

        Raises:
            WebSocketConnectionError: If connection fails after retry attempts.

        """
        self._websocket = await connect_with_retry(
            self.api_endpoint + f"?hibachiClient={get_hibachi_client()}",
            executor=self._executor,
        )
        self._receive_task = asyncio.create_task(self._receive_loop())
        return self

    async def subscribe(self, subscriptions: list[WebSocketSubscription]) -> None:
        """Subscribe to one or more market data topics.

        Sends a subscribe request to the WebSocket server for the specified
        market data subscriptions (e.g., mark price, order book, trades).

        Args:
            subscriptions: List of WebSocketSubscription objects defining the
                topics and parameters to subscribe to.

        Raises:
            ValidationError: If WebSocket connection is not established.

        """
        message = {
            "method": "subscribe",
            "parameters": {
                "subscriptions": [
                    {**asdict(sub), "topic": sub.topic.value} for sub in subscriptions
                ]
            },
        }
        await self.websocket.send(orjson.dumps(message).decode())

    async def unsubscribe(self, subscriptions: list[WebSocketSubscription]) -> None:
        """Unsubscribe from one or more market data topics.

        Sends an unsubscribe request to the WebSocket server to stop receiving
        updates for the specified market data subscriptions.

        Args:
            subscriptions: List of WebSocketSubscription objects defining the
                topics and parameters to unsubscribe from.

        Raises:
            ValidationError: If WebSocket connection is not established.

        """
        message = {
            "method": "unsubscribe",
            "parameters": {
                "subscriptions": [
                    {**asdict(sub), "topic": sub.topic.value} for sub in subscriptions
                ]
            },
        }
        await self.websocket.send(orjson.dumps(message).decode())

    def on(self, topic: str, handler: WsEventHandler) -> None:
        """Register a callback for raw topic name (e.g., 'mark_price')."""
        if topic not in self._event_handlers:
            self._event_handlers[topic] = []
        self._event_handlers[topic].append(handler)

    async def _receive_loop(self) -> None:
        """Continuously receive and process WebSocket messages.

        Receives messages from the WebSocket, parses them, and dispatches
        them to registered event handlers based on the message topic.
        Runs until cancelled or an error occurs.

        Raises:
            WebSocketConnectionError: If the WebSocket connection is closed unexpectedly.
            Exception: For any other errors during message processing.

        """
        try:
            while True:
                raw = await self.websocket.recv()
                msg = orjson.loads(raw)
                topic = msg.get("topic")
                if topic and topic in self._event_handlers:
                    for handler in self._event_handlers[topic]:
                        await handler(msg)
        except asyncio.CancelledError:
            pass
        except WebSocketConnectionError as e:
            log.warning("WebSocket closed: %s", e)
        except Exception as e:
            log.error("Receive loop error: %s", e)

    async def disconnect(self) -> None:
        """Close the WebSocket connection and clean up resources.

        Cancels the receive loop task, waits for it to complete, and closes
        the WebSocket connection. After calling this method, the client must
        call connect() again before subscribing to topics.
        """
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
