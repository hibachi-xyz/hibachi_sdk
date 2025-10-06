import json
import random
import time
from dataclasses import asdict
from typing import Callable, Dict, List

from hibachi_xyz.executors import WsConnection
from hibachi_xyz.api import HibachiApiClient
from hibachi_xyz.helpers import (
    get_hibachi_client,
    connect_with_retry,
    DEFAULT_API_URL,
    DEFAULT_DATA_API_URL,
    print_data,
)

from .types import (
    EnableCancelOnDisconnectParams,
    Nonce,
    Order,
    OrderPlaceParams,
    OrdersBatchParams,
    OrdersStatusResponse,
    OrderStatusResponse,
    Side,
    WebSocketResponse,
)


class HibachiWSTradeClient:
    """
    Trade Websocket Client is used to place, modify and cancel orders.

    ```python
    import asyncio
    import os
    from hibachi_xyz import HibachiWSTradeClient, print_data

    from dotenv import load_dotenv
    load_dotenv()

    account_id = int(os.environ.get('HIBACHI_ACCOUNT_ID', "your-account-id"))
    private_key = os.environ.get('HIBACHI_PRIVATE_KEY', "your-private")
    api_key = os.environ.get('HIBACHI_API_KEY', "your-api-key")
    public_key = os.environ.get('HIBACHI_PUBLIC_KEY', "your-public")

    async def main():
        client = HibachiWSTradeClient(
            api_key=api_key,
            account_id=account_id,
            account_public_key=public_key,
            private_key=private_key
        )

        await client.connect()
        orders = await client.get_orders_status()
        first_order = orders.result[0]

        # single order
        order = await client.get_order_status(first_order.orderId)
        print_data(order)

        # client.api.set_private_key(private_key)
        modify_result = await client.modify_order(
            order=order.result,
            quantity=float("0.002"),
            price=str(float("93500.0")),
            side=order.result.side,
            maxFeesPercent=float("0.00045"),
        )

        print_data(modify_result)

    asyncio.run(main())
    ```

    """

    def __init__(
        self,
        api_key: str,
        account_id: int,
        account_public_key: str,
        api_url: str = DEFAULT_API_URL,
        data_api_url: str = DEFAULT_DATA_API_URL,
        private_key: str | None = None,
    ):
        self.api_endpoint = api_url
        self.api_endpoint = (
            self.api_endpoint.replace("https://", "wss://") + "/ws/trade"
        )
        self.websocket: WsConnection | None = None

        # random id start
        self.message_id = random.randint(1, 1000000)
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._response_handlers: Dict[int, Callable] = {}
        self.api_key = api_key
        self.account_id = int(account_id) if isinstance(account_id, str) else account_id
        self.account_public_key = account_public_key

        self.api = HibachiApiClient(
            api_url=api_url,
            data_api_url=data_api_url,
            account_id=account_id,
            api_key=api_key,
            private_key=private_key,
        )

    async def connect(self):
        """Establish WebSocket connection with retry logic"""
        self.websocket = await connect_with_retry(
            web_url=self.api_endpoint
            + f"?accountId={self.account_id}&hibachiClient={get_hibachi_client()}",
            headers=[("Authorization", self.api_key)],
        )

        return self

    async def place_order(self, params: OrderPlaceParams) -> tuple[Nonce, int]:
        """Place a new order"""
        self.message_id += 1

        nonce = time.time_ns() // 1_000
        side = params.side
        if side == Side.BUY:
            side = Side.BID
        elif side == Side.SELL:
            side = Side.ASK

        prepare_packet = self.api._create_order_request_data(
            nonce=nonce,
            symbol=params.symbol,
            quantity=params.quantity,
            side=side,
            max_fees_percent=params.maxFeesPercent,
            trigger_price=params.trigger_price,
            price=params.price,
            creation_deadline=params.creation_deadline,
            twap_config=params.twap_config,
        )

        prepare_packet["accountId"] = self.account_id

        message = {
            "id": self.message_id,
            "method": "order.place",
            "params": prepare_packet,
            "signature": prepare_packet.get("signature"),
        }

        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()
        response_data = json.loads(response)

        print("ws place_order -------------------------------------------")
        print_data(response_data)

        # response_data["result"] = OrderPlaceResponseResult(**response_data["result"])
        # nonce: Nonce = prepare_packet.get("nonce")
        return (nonce, int(response_data.get("result").get("orderId")))

    async def cancel_order(self, orderId: int, nonce: int) -> WebSocketResponse:
        """Cancel an existing order"""
        self.message_id += 1

        prepare_packet = self.api._cancel_order_request_data(orderId, nonce, False)

        print("prepare_packet -------------------------------------------")
        print_data(prepare_packet)

        message = {
            "id": self.message_id,
            "method": "order.cancel",
            "params": {
                "orderId": str(orderId),
                "accountId": str(self.account_id),
                # "nonce": str(nonce)
            },
            "signature": prepare_packet.get("signature"),
        }
        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()
        response_data = json.loads(response)

        print_data(response_data)

        # return WebSocketResponse(**response_data)
        return response_data

    async def modify_order(
        self,
        order: Order,
        quantity: float,
        price: str,
        side: Side,
        maxFeesPercent: float,
        nonce: Nonce | None = None,
    ) -> WebSocketResponse:
        """Modify an existing order"""
        self.message_id += 1

        prepare_packet = self.api._update_order_generate_sig(
            order,
            side=side,
            max_fees_percent=maxFeesPercent,
            quantity=quantity,
            price=float(price),
            trigger_price=float(order.triggerPrice)
            if isinstance(order.triggerPrice, str)
            else order.triggerPrice,
            nonce=nonce,
        )

        signature = prepare_packet.get("signature")
        del prepare_packet["signature"]

        message = {
            "id": self.message_id,
            "method": "order.modify",
            "params": prepare_packet,
            "signature": signature,
        }

        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()
        response_data = json.loads(response)

        if "error" in response_data and response_data["error"]:
            raise Exception(
                f"Error modifying order: {response_data["error"]["message"]}"
            )

        return response_data
        # return WebSocketResponse(**response_data)

    async def get_order_status(self, orderId: int) -> OrderStatusResponse:
        """Get status of a specific order"""
        self.message_id += 1
        message = {
            "id": self.message_id,
            "method": "order.status",
            "params": {"orderId": str(orderId), "accountId": int(self.account_id)},
        }

        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()
        response_data = json.loads(response)

        print_data(response_data)

        response_data["result"] = Order(**response_data["result"])
        return OrderStatusResponse(**response_data)

    async def get_orders_status(self) -> OrdersStatusResponse:
        """Get status of all orders"""
        self.message_id += 1

        message = {
            "id": self.message_id,
            "method": "orders.status",
            "params": {"accountId": int(self.account_id)},
        }

        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()
        response_data = json.loads(response)
        response_data["result"] = [Order(**order) for order in response_data["result"]]
        return OrdersStatusResponse(**response_data)

    async def cancel_all_orders(self) -> bool:
        """Cancel all orders"""
        self.message_id += 1

        nonce = time.time_ns() // 1_000

        signed_packet = self.api._cancel_order_request_data(None, nonce, False)

        message = {
            "id": self.message_id,
            "method": "orders.cancel",
            "params": {
                "accountId": self.account_id,
                "nonce": nonce,
                # "contractId": 2 # TODO: get contract id
            },
            "signature": signed_packet.get("signature"),
        }
        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()
        response_data = json.loads(response)

        print_data(response_data)

        if response_data.get("id") == self.message_id:
            return response_data.get("status") == 200
        else:
            return False

    async def batch_orders(self, params: OrdersBatchParams) -> WebSocketResponse:
        """Execute multiple order operations in a single request"""
        self.message_id += 1
        message = {
            "id": self.message_id,
            "method": "orders.batch",
            "params": asdict(params),
        }
        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()
        response_data = json.loads(response)
        return WebSocketResponse(**response_data)

    async def enable_cancel_on_disconnect(
        self, params: EnableCancelOnDisconnectParams
    ) -> WebSocketResponse:
        """Enable automatic order cancellation on WebSocket disconnect"""
        self.message_id += 1
        message = {
            "id": self.message_id,
            "method": "orders.enableCancelOnDisconnect",
            "params": asdict(params),
        }
        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()
        response_data = json.loads(response)
        return WebSocketResponse(**response_data)

    async def disconnect(self):
        """Close the WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
