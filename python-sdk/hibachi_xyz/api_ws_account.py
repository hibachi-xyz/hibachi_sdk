import asyncio
import json
import logging
import time
from typing import Callable, Dict, List

from hibachi_xyz.errors import WebSocketConnectionError
from hibachi_xyz.executors import WsConnection
from hibachi_xyz.helpers import DEFAULT_API_URL, connect_with_retry, get_hibachi_client
from hibachi_xyz.types import AccountSnapshot, AccountStreamStartResult, Position

log = logging.getLogger(__name__)


class HibachiWSAccountClient:
    def __init__(
        self,
        api_key: str,
        account_id: str,
        api_endpoint: str = DEFAULT_API_URL,
    ):
        self.api_endpoint = api_endpoint.replace("https://", "wss://") + "/ws/account"
        self.websocket: WsConnection | None = None
        self.message_id = 0
        self.api_key = api_key
        self.account_id = int(account_id)
        self.listenKey: str | None = None
        self._event_handlers: Dict[str, List[Callable[[dict], None]]] = {}

    def on(self, topic: str, handler: Callable[[dict], None]):
        if topic not in self._event_handlers:
            self._event_handlers[topic] = []
        self._event_handlers[topic].append(handler)

    async def connect(self):
        self.websocket = await connect_with_retry(
            web_url=self.api_endpoint
            + f"?accountId={self.account_id}&hibachiClient={get_hibachi_client()}",
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
            log.debug("pong!")

    async def listen(self) -> dict | None:
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
        except WebSocketConnectionError as e:
            log.warning("WebSocket closed: %s", e)
        except Exception as e:
            log.error("WebSocket closed: %s", e)
            raise

    async def disconnect(self):
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
