import asyncio
import json
import time
from typing import Callable, Dict, List, Optional

import websockets
from hibachi_xyz.helpers import connect_with_retry, default_api_url
from hibachi_xyz.types import AccountSnapshot, AccountStreamStartResult, Position


class HibachiWSAccountClient:
    def __init__(
        self, api_key: str, account_id: str, api_endpoint: str = default_api_url
    ):
        self.api_endpoint = api_endpoint.replace("https://", "wss://")
        self.websocket = None
        self.message_id = 0
        self.api_key = api_key
        self.account_id = int(account_id)
        self.listenKey: Optional[str] = None
        self._event_handlers: Dict[str, List[Callable[[dict], None]]] = {}

    def on(self, topic: str, handler: Callable[[dict], None]):
        if topic not in self._event_handlers:
            self._event_handlers[topic] = []
        self._event_handlers[topic].append(handler)

    async def connect(self):
        self.websocket = await connect_with_retry(
            web_url=self.api_endpoint + f"/ws/account?accountId={self.account_id}",
            headers=[("Authorization", self.api_key)],
        )

    def _next_message_id(self) -> int:
        self.message_id += 1
        return self.message_id

    def _timestamp(self) -> int:
        return int(time.time())

    async def stream_start(self) -> AccountStreamStartResult:
        message = {
            "id": self._next_message_id(),
            "method": "stream.start",
            "params": {"accountId": self.account_id},
            "timestamp": self._timestamp(),
        }

        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()
        response_data = json.loads(response)

        result = AccountStreamStartResult(**response_data["result"])
        result.accountSnapshot = AccountSnapshot(
            **response_data["result"]["accountSnapshot"]
        )
        result.accountSnapshot.positions = [
            Position(**pos) for pos in result.accountSnapshot.positions
        ]
        self.listenKey = result.listenKey
        return result

    async def ping(self):
        if not self.listenKey:
            raise ValueError("Cannot send ping: listenKey not initialized.")

        message = {
            "id": self._next_message_id(),
            "method": "stream.ping",
            "params": {"accountId": self.account_id, "listenKey": self.listenKey},
            "timestamp": self._timestamp(),
        }

        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()
        parsed = json.loads(response)
        if parsed.get("status") == 200:
            print("pong!")

    async def listen(self) -> Optional[dict]:
        try:
            response = await asyncio.wait_for(self.websocket.recv(), timeout=15)
            message = json.loads(response)

            topic = message.get("topic")
            if topic in self._event_handlers:
                for handler in self._event_handlers[topic]:
                    await handler(message)

            return message
        except asyncio.TimeoutError:
            await self.ping()
            return None
        except websockets.exceptions.ConnectionClosed as e:
            print(f"[listen] WebSocket closed: code={e.code}, reason={e.reason}")
            raise

    async def disconnect(self):
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
