import asyncio
import json
from dataclasses import asdict
from typing import Callable, Dict, List, Optional

import websockets

from .helpers import connect_with_retry, default_data_api_url
from .types import WebSocketSubscription


class HibachiWSMarketClient:
    def __init__(self, api_endpoint: str = default_data_api_url):
        self.api_endpoint = api_endpoint.replace("https://", "wss://") + "/ws/market"
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._event_handlers: Dict[str, List[Callable[[dict], None]]] = {}
        self._receive_task: Optional[asyncio.Task] = None

    async def connect(self):
        self.websocket = await connect_with_retry(self.api_endpoint)
        self._receive_task = asyncio.create_task(self._receive_loop())
        return self

    async def subscribe(self, subscriptions: List[WebSocketSubscription]):
        message = {
            "method": "subscribe",
            "parameters": {
                "subscriptions": [
                    {**asdict(sub), "topic": sub.topic.value} for sub in subscriptions
                ]
            },
        }
        await self.websocket.send(json.dumps(message))

    async def unsubscribe(self, subscriptions: List[WebSocketSubscription]):
        message = {
            "method": "unsubscribe",
            "parameters": {
                "subscriptions": [
                    {**asdict(sub), "topic": sub.topic.value} for sub in subscriptions
                ]
            },
        }
        await self.websocket.send(json.dumps(message))

    def on(self, topic: str, handler: Callable[[dict], None]):
        """Register a callback for raw topic name (e.g., 'mark_price')."""
        if topic not in self._event_handlers:
            self._event_handlers[topic] = []
        self._event_handlers[topic].append(handler)

    async def _receive_loop(self):
        try:
            while True:
                raw = await self.websocket.recv()
                msg = json.loads(raw)
                topic = msg.get("topic")
                if topic and topic in self._event_handlers:
                    for handler in self._event_handlers[topic]:
                        await handler(msg)
        except asyncio.CancelledError:
            pass
        except websockets.ConnectionClosed:
            print("[MarketClient] WebSocket closed.")
        except Exception as e:
            print(f"[MarketClient] Receive loop error: {e}")

    async def disconnect(self):
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
