"""WebSocket client for trade operations.

This module provides the HibachiWSTradeClient for placing, modifying, and
canceling orders via WebSocket connections with lower latency than HTTP.
"""

import logging
import random
import time
from dataclasses import asdict
from typing import Self

import orjson

from hibachi_xyz.api import HibachiApiClient
from hibachi_xyz.connection import connect_with_retry
from hibachi_xyz.errors import (
    BadWebsocketResponse,
    DeserializationError,
    SerializationError,
    ValidationError,
    WebSocketMessageError,
)
from hibachi_xyz.executors import DEFAULT_WS_EXECUTOR, WsConnection, WsExecutor
from hibachi_xyz.helpers import (
    DEFAULT_API_URL,
    DEFAULT_DATA_API_URL,
    create_with,
    get_hibachi_client,
)
from hibachi_xyz.types import (
    EnableCancelOnDisconnectParams,
    JsonObject,
    Nonce,
    Order,
    OrderPlaceParams,
    OrdersBatchParams,
    OrdersStatusResponse,
    OrderStatusResponse,
    Side,
    WebSocketResponse,
)

log = logging.getLogger(__name__)


class HibachiWSTradeClient:
    """Trade Websocket Client is used to place, modify and cancel orders.

    Examples:
        .. code-block:: python

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

                modify_result = await client.modify_order(
                    order=order.result,
                    quantity=float("0.002"),
                    price=str(float("93500.0")),
                    side=order.result.side,
                    maxFeesPercent=float("0.00045"),
                )

                print_data(modify_result)

            asyncio.run(main())
    """

    def __init__(
        self,
        api_key: str,
        account_id: int | str,
        account_public_key: str,
        api_url: str = DEFAULT_API_URL,
        data_api_url: str = DEFAULT_DATA_API_URL,
        private_key: str | None = None,
        executor: WsExecutor | None = None,
    ):
        """Initialize the Hibachi WebSocket trade client.

        Args:
            api_key: Your API key for authentication
            account_id: Your Hibachi account ID (int or numeric string)
            account_public_key: Your account's public key
            api_url: Base URL for the Hibachi API (default: production URL)
            data_api_url: Base URL for the data API (default: production data URL)
            private_key: Private key for signing requests (hex string with or without 0x prefix,
                or HMAC key for web accounts)
            executor: Custom WebSocket executor (optional, uses default if not provided)

        """
        self.api_endpoint = api_url
        self.api_endpoint = (
            self.api_endpoint.replace("https://", "wss://") + "/ws/trade"
        )
        self._websocket: WsConnection | None = None

        # random id start
        self.message_id = random.randint(1, 1000000)
        self.api_key = api_key
        try:
            self.account_id: int = (
                int(account_id) if isinstance(account_id, str) else account_id
            )
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid account_id format: {e}") from e
        self.account_public_key = account_public_key
        self._executor: WsExecutor = (
            executor if executor is not None else DEFAULT_WS_EXECUTOR()
        )

        self.api = HibachiApiClient(
            api_url=api_url,
            data_api_url=data_api_url,
            account_id=self.account_id,
            api_key=api_key,
            private_key=private_key,
        )

    @property
    def websocket(self) -> WsConnection:
        """Get the WebSocket connection.

        Returns:
            Active WebSocket connection.

        Raises:
            ValidationError: If no connection exists. Call connect() first.

        """
        if self._websocket is None:
            raise ValidationError from ValueError(
                "No existing ws connection. Call `connect` first"
            )
        return self._websocket

    async def connect(self) -> Self:
        """Establish WebSocket connection with retry logic."""
        self._websocket = await connect_with_retry(
            web_url=self.api_endpoint
            + f"?accountId={self.account_id}&hibachiClient={get_hibachi_client()}",
            headers=[("Authorization", self.api_key)],
            executor=self._executor,
        )

        return self

    async def place_order(self, params: OrderPlaceParams) -> tuple[Nonce, int]:
        """Place a new order."""
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

        try:
            payload = orjson.dumps(message).decode()
        except (ValueError, TypeError) as e:
            raise SerializationError(
                f"Failed to serialize order.place message: {e}"
            ) from e
        try:
            await self.websocket.send(payload)
        except Exception as e:
            raise WebSocketMessageError("Failed to send order.place message") from e

        response = await self.websocket.recv()

        try:
            response_data = orjson.loads(response)
        except (ValueError, TypeError) as e:
            raise DeserializationError(
                f"Failed to parse WebSocket response: {e}"
            ) from e

        log.debug("ws place_order -------------------------------------------")
        log.debug("Response data: %s", response_data)

        try:
            order_id = int(response_data.get("result").get("orderId"))
        except (ValueError, TypeError, AttributeError, KeyError) as e:
            raise DeserializationError(
                f"Failed to extract orderId from response: {e}"
            ) from e

        return (nonce, order_id)

    async def cancel_order(
        self, orderId: int | None, nonce: int | None
    ) -> WebSocketResponse:
        """Cancel an existing order."""
        if orderId is None and nonce is None:
            raise ValidationError("Either 'orderId' or 'nonce' must be not None")

        self.message_id += 1

        prepare_packet = self.api._cancel_order_request_data(
            order_id=orderId, nonce=nonce
        )

        log.debug("prepare_packet -------------------------------------------")
        log.debug("Prepare packet: %s", prepare_packet)

        message: JsonObject = {
            "id": self.message_id,
            "method": "order.cancel",
            "params": {
                "accountId": int(self.account_id),
            },
            "signature": prepare_packet.get("signature"),
        }
        if orderId is not None:
            message["params"]["orderId"] = str(orderId)  # type: ignore
        else:
            message["params"]["nonce"] = str(nonce)  # type: ignore

        try:
            payload = orjson.dumps(message).decode()
        except (ValueError, TypeError) as e:
            raise SerializationError(
                f"Failed to serialize order.cancel message: {e}"
            ) from e
        try:
            await self.websocket.send(payload)
        except Exception as e:
            raise WebSocketMessageError(
                f"Failed to send order.cancel message {orderId=}"
            ) from e

        response = await self.websocket.recv()

        try:
            response_data = orjson.loads(response)
        except (ValueError, TypeError) as e:
            raise DeserializationError(
                f"Failed to parse WebSocket response: {e}"
            ) from e

        log.debug("Response data: %s", response_data)

        return create_with(WebSocketResponse, response_data, implicit_null=True)

    async def modify_order(
        self,
        order: Order,
        quantity: float,
        price: str,
        side: Side,
        maxFeesPercent: float,
        nonce: Nonce | None = None,
    ) -> WebSocketResponse:
        """Modify an existing order."""
        self.message_id += 1

        try:
            price_float = float(price)
            trigger_price_float = (
                float(order.triggerPrice)
                if isinstance(order.triggerPrice, str)
                else order.triggerPrice
            )
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid price or trigger_price format: {e}") from e

        prepare_packet = self.api._update_order_generate_sig(
            order,
            side=side,
            max_fees_percent=maxFeesPercent,
            quantity=quantity,
            price=price_float,
            trigger_price=trigger_price_float,
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

        try:
            payload = orjson.dumps(message).decode()
        except (ValueError, TypeError) as e:
            raise SerializationError(
                f"Failed to serialize order.modify message: {e}"
            ) from e
        try:
            await self.websocket.send(payload)
        except Exception as e:
            raise WebSocketMessageError("Failed to send order.modify message") from e

        response = await self.websocket.recv()

        try:
            response_data = orjson.loads(response)
        except (ValueError, TypeError) as e:
            raise DeserializationError(
                f"Failed to parse WebSocket response: {e}"
            ) from e

        if "error" in response_data and response_data["error"]:
            raise BadWebsocketResponse(
                f"Error modifying order: {response_data['error']['message']}"
            )

        return create_with(WebSocketResponse, response_data, implicit_null=True)

    async def get_order_status(self, orderId: int) -> OrderStatusResponse:
        """Get status of a specific order."""
        self.message_id += 1
        message = {
            "id": self.message_id,
            "method": "order.status",
            "params": {"orderId": str(orderId), "accountId": int(self.account_id)},
        }

        try:
            payload = orjson.dumps(message).decode()
        except (ValueError, TypeError) as e:
            raise SerializationError(
                f"Failed to serialize order.status message: {e}"
            ) from e
        try:
            await self.websocket.send(payload)
        except Exception as e:
            raise WebSocketMessageError(
                f"Failed to send order.status message {orderId=}"
            ) from e

        response = await self.websocket.recv()

        try:
            response_data = orjson.loads(response)
        except (ValueError, TypeError) as e:
            raise DeserializationError(
                f"Failed to parse WebSocket response: {e}"
            ) from e

        log.debug("Response data: %s", response_data)

        response_data["result"] = create_with(Order, response_data["result"])
        return create_with(OrderStatusResponse, response_data, implicit_null=True)

    async def get_orders_status(self) -> OrdersStatusResponse:
        """Get status of all orders."""
        self.message_id += 1

        message = {
            "id": self.message_id,
            "method": "orders.status",
            "params": {"accountId": int(self.account_id)},
        }

        try:
            payload = orjson.dumps(message).decode()
        except (ValueError, TypeError) as e:
            raise SerializationError(
                f"Failed to serialize orders.status message: {e}"
            ) from e
        try:
            await self.websocket.send(payload)
        except Exception as e:
            raise WebSocketMessageError("Failed to send orders.status message") from e

        response = await self.websocket.recv()

        try:
            response_data = orjson.loads(response)
        except (ValueError, TypeError) as e:
            raise DeserializationError(
                f"Failed to parse WebSocket response: {e}"
            ) from e

        response_data["result"] = [
            create_with(Order, order) for order in response_data["result"]
        ]
        return create_with(OrdersStatusResponse, response_data)

    async def cancel_all_orders(self) -> bool:
        """Cancel all orders."""
        self.message_id += 1

        nonce = time.time_ns() // 1_000

        signed_packet = self.api._cancel_order_request_data(order_id=None, nonce=nonce)

        message = {
            "id": self.message_id,
            "method": "orders.cancel",
            "params": {
                "accountId": self.account_id,
                "nonce": nonce,
                # TODO: get contract id
            },
            "signature": signed_packet.get("signature"),
        }

        try:
            payload = orjson.dumps(message).decode()
        except (ValueError, TypeError) as e:
            raise SerializationError(
                f"Failed to serialize orders.cancel message: {e}"
            ) from e
        try:
            await self.websocket.send(payload)
        except Exception as e:
            raise WebSocketMessageError("Failed to send orders.cancel message") from e

        response = await self.websocket.recv()

        try:
            response_data = orjson.loads(response)
        except (ValueError, TypeError) as e:
            raise DeserializationError(
                f"Failed to parse WebSocket response: {e}"
            ) from e

        log.debug("Response data: %s", response_data)

        if response_data.get("id") == self.message_id:
            return response_data.get("status") == 200  # type: ignore
        else:
            return False

    async def batch_orders(self, params: OrdersBatchParams) -> WebSocketResponse:
        """Execute multiple order operations in a single request."""
        self.message_id += 1
        message = {
            "id": self.message_id,
            "method": "orders.batch",
            "params": asdict(params),
        }

        try:
            payload = orjson.dumps(message).decode()
        except (ValueError, TypeError) as e:
            raise SerializationError(
                f"Failed to serialize orders.batch message: {e}"
            ) from e
        try:
            await self.websocket.send(payload)
        except Exception as e:
            raise WebSocketMessageError("Failed to send orders.batch message") from e

        response = await self.websocket.recv()

        try:
            response_data = orjson.loads(response)
        except (ValueError, TypeError) as e:
            raise DeserializationError(
                f"Failed to parse WebSocket response: {e}"
            ) from e

        return create_with(WebSocketResponse, response_data, implicit_null=True)

    async def enable_cancel_on_disconnect(
        self, params: EnableCancelOnDisconnectParams
    ) -> WebSocketResponse:
        """Enable automatic order cancellation on WebSocket disconnect."""
        self.message_id += 1
        message = {
            "id": self.message_id,
            "method": "orders.enableCancelOnDisconnect",
            "params": asdict(params),
        }

        try:
            payload = orjson.dumps(message).decode()
        except (ValueError, TypeError) as e:
            raise SerializationError(
                f"Failed to serialize orders.enableCancelOnDisconnect message: {e}"
            ) from e
        try:
            await self.websocket.send(payload)
        except Exception as e:
            raise WebSocketMessageError(
                "Failed to send orders.enableCancelOnDisconnect message"
            ) from e

        response = await self.websocket.recv()

        try:
            response_data = orjson.loads(response)
        except (ValueError, TypeError) as e:
            raise DeserializationError(
                f"Failed to parse WebSocket response: {e}"
            ) from e

        return create_with(WebSocketResponse, response_data, implicit_null=True)

    async def disconnect(self) -> None:
        """Close the WebSocket connection."""
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
