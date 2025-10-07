import asyncio
import logging
from dataclasses import asdict
from typing import Self

import orjson

from hibachi_xyz.errors import ValidationError, WebSocketConnectionError
from hibachi_xyz.executors import WsConnection
from hibachi_xyz.helpers import (
    DEFAULT_DATA_API_URL,
    connect_with_retry,
    get_hibachi_client,
)
from hibachi_xyz.types import WebSocketSubscription, WsEventHandler

log = logging.getLogger(__name__)


class HibachiWSMarketClient:
    def __init__(self, api_endpoint: str = DEFAULT_DATA_API_URL):
        self.api_endpoint = api_endpoint.replace("https://", "wss://") + "/ws/market"
        self._websocket: WsConnection | None = None
        self._event_handlers: dict[str, list[WsEventHandler]] = {}
        self._receive_task: asyncio.Task[None] | None = None

    @property
    def websocket(self) -> WsConnection:
        if self._websocket is None:
            raise ValidationError from ValueError(
                "No existing ws connection. Call `connect` first"
            )
        return self._websocket

    async def connect(self) -> Self:
        self._websocket = await connect_with_retry(
            self.api_endpoint + f"?hibachiClient={get_hibachi_client()}"
        )
        self._receive_task = asyncio.create_task(self._receive_loop())
        return self

    async def subscribe(self, subscriptions: list[WebSocketSubscription]) -> None:
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
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
