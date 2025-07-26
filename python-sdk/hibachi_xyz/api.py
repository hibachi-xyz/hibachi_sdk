from dataclasses import asdict
from enum import Enum
from hashlib import sha256
import hmac
import json
from math import floor
from time import time, time_ns
from typing import Any, Dict, Optional, TypeAlias, List, Tuple, Union

from eth_keys import keys
import requests

from hibachi_xyz.types import (
    BatchOrder,
    BatchResponse,
    BatchResponseOrder,
    ExchangeInfo,
    FeeConfig,
    FutureContract,
    MaintenanceWindow,
    Order,
    OrderIdVariant,
    PendingOrdersResponse,
    TriggerDirection,
    WithdrawalLimit,
    PriceResponse,
    FundingRateEstimation,
    StatsResponse,
    TradesResponse,
    Trade,
    TakerSide,
    KlinesResponse,
    Kline,
    OpenInterestResponse,
    OrderBookLevel,
    OrderBook,
    AccountInfo,
    Asset,
    Position,
    AccountTradesResponse,
    AccountTrade,
    SettlementsResponse,
    Settlement,
    Order,
    CapitalBalance,
    CapitalHistory,
    Transaction,
    WithdrawRequest,
    WithdrawResponse,
    DepositInfo,
    Side,
    InventoryResponse,
    CrossChainAsset,
    FeeConfig,
    Market,
    TradingTier,
    MarketInfo,
    TransferRequest,
    TransferResponse,
    TWAPConfig,
    TPSLConfig,
    HibachiApiError,
    Interval,
    Nonce,
    OrderId,
    OrderFlags,
    CreateOrder,
    UpdateOrder,
    CancelOrder,
)

from hibachi_xyz.helpers import create_with, default_api_url, default_data_api_url


def price_to_bytes(price: float, contract: FutureContract) -> bytes:
    return int(
        price
        * pow(2, 32)
        * pow(10, contract.settlementDecimals - contract.underlyingDecimals)
    ).to_bytes(8, "big")


def _get_http_error(response: requests.Response) -> Optional[HibachiApiError]:
    """Check if the response is an error and return an exception if it is
    The builtin response.raise_for_status() does not show the server's response
    """

    if response.status_code > 299:
        return HibachiApiError(response.status_code, response.text)
    return None


class HibachiApiClient:
    """
    Example usage:
    ```python
    from hibachi_xyz import HibachiApiClient
    from dotenv import load_dotenv
    load_dotenv()

    hibachi = HibachiApiClient(
        api_key = os.environ.get('HIBACHI_API_KEY', "your-api-key"),
        account_id = os.environ.get('HIBACHI_ACCOUNT_ID', "your-account-id"),
        private_key = os.environ.get('HIBACHI_PRIVATE_KEY', "your-private"),
    )

    account_info = hibachi.get_account_info()
    print(f"Account Balance: {account_info.balance}")
    print(f"total Position Notional: {account_info.totalPositionNotional}")

    exchange_info = api.get_exchange_info()
    print(exchange_info)
    ```

    Args:
        api_url: The base URL of the API
        data_api_url: The base URL of the data API
        account_id: The account ID
        api_key: The API key
        private_key: The private key for the account

    """

    api_url: str
    data_api_url: str
    account_id: Optional[int] = None
    api_key: Optional[str] = None

    _private_key: Optional[keys.PrivateKey] = None  # ECDSA for wallet account
    _private_key_hmac: Optional[str] = None  # HMAC for web account

    future_contracts: Optional[Dict[str, FutureContract]] = None

    def __init__(
        self,
        api_url: str = default_api_url,
        data_api_url: str = default_data_api_url,
        account_id: Optional[int] = None,
        api_key: Optional[str] = None,
        private_key: Optional[str] = None,
    ):
        self.api_url = api_url
        self.data_api_url = data_api_url
        self.account_id = (
            int(account_id)
            if isinstance(account_id, str) and account_id.isdigit()
            else account_id
        )
        self.api_key = api_key
        if private_key is not None:
            self.set_private_key(private_key)

    def set_account_id(self, account_id: int):
        self.account_id = account_id

    def set_api_key(self, api_key: str):
        self.api_key = api_key

    def set_private_key(self, private_key: str):
        if private_key.startswith("0x"):
            private_key = private_key[2:]
            private_key_bytes = bytes.fromhex(private_key)
            self._private_key = keys.PrivateKey(private_key_bytes)

        if private_key.startswith("0x") == False:
            self._private_key_hmac = private_key

    """ Market API endpoints, can be called without having an account """

    def get_exchange_info(self) -> ExchangeInfo:
        """
        Return exchange metadata, currently it will return all futureContracts.

        Also returns a list of exchange maintenance windows in the "maintenanceWindow" field. For each window, the fields "begin" and "end" denote the beginning and end of the window, in seconds since the UNIX epoch. The field "note" contains a note.

        The field "maintenanceStatus" can have the values "NORMAL", "UNSCHEDULED_MAINTENANCE", "SCHEDULED_MAINTENANCE". If the exchange is currently under scheduled maintenance, the field "currentMaintenanceWindow" displays information on the current maintenance window.

        Endpoint: `GET /market/exchange-info`

        ```python
        exchange_info = client.get_exchange_info()
        print(exchange_info)
        ```
        Return type:
        ```python
        ExchangeInfo {
            feeConfig: FeeConfig
            futureContracts: List[FutureContract]
            instantWithdrawalLimit: WithdrawalLimit
            maintenanceWindow: List[MaintenanceWindow]
            # can be NORMAL, MAINTENANCE
            status: str
        }
        ```

        """
        exchange_info = self.__send_simple_request("/market/exchange-info")

        self.future_contracts = {}
        for contract in exchange_info["futureContracts"]:
            self.future_contracts[contract["symbol"]] = create_with(
                FutureContract, contract
            )

        fee_config = create_with(FeeConfig, exchange_info["feeConfig"])

        # Parse future contracts
        future_contracts = [
            create_with(FutureContract, contract)
            for contract in exchange_info["futureContracts"]
        ]

        # Parse withdrawal limit
        withdrawal_limit = create_with(
            WithdrawalLimit, exchange_info["instantWithdrawalLimit"]
        )

        # Parse maintenance windows
        maintenance_windows = [
            create_with(MaintenanceWindow, window)
            for window in exchange_info["maintenanceWindow"]
        ]

        # Create exchange info object
        return ExchangeInfo(
            feeConfig=fee_config,
            futureContracts=future_contracts,
            instantWithdrawalLimit=withdrawal_limit,
            maintenanceWindow=maintenance_windows,
            status=exchange_info["status"],
        )

        # exchange_info_types = create_with(ExchangeInfo, exchange_info)

        # return exchange_info_types

    def get_inventory(self) -> InventoryResponse:
        """
        Similar to /market/exchange-info, in addition to the contract metadata we will return their latest price info.

        Return type:
        ```python
        InventoryResponse {
            crossChainAssets: {
                chain: str
                exchangeRateFromUSDT: str
                exchangeRateToUSDT: str
                instantWithdrawalLowerLimitInUSDT: str
                instantWithdrawalUpperLimitInUSDT: str
                token: str
            }[]
            feeConfig: {
                depositFees: str
                instantWithdrawDstPublicKey: str
                instantWithdrawalFees: List[List[Union[int, float]]]
                tradeMakerFeeRate: str
                tradeTakerFeeRate: str
                transferFeeRate: str
                withdrawalFees: str
            }
            markets: {
                contract: {
                    displayName: str
                    id: int
                    maintenanceFactorForPositions: str
                    marketCloseTimestamp: Optional[str]
                    marketOpenTimestamp: Optional[str]
                    minNotional: str
                    minOrderSize: str
                    orderbookGranularities: List[str]
                    riskFactorForOrders: str
                    riskFactorForPositions: str
                    settlementDecimals: int
                    settlementSymbol: str
                    status: str
                    stepSize: str
                    symbol: str
                    tickSize: str
                    underlyingDecimals: int
                    underlyingSymbol: str
                }
                info: {
                    category: str
                    markPrice: str
                    price24hAgo: str
                    priceLatest: str
                    tags: List[str]
                }
            }[]
            tradingTiers: {
                level: int
                lowerThreshold: str
                title: str
                upperThreshold: str
            }[]
        }
        ```
        """
        market_inventory = self.__send_simple_request("/market/inventory")

        self.future_contracts = {}
        for market in market_inventory["markets"]:
            contract = create_with(FutureContract, market["contract"])
            self.future_contracts[contract.symbol] = contract

        markets = [
            Market(
                contract=create_with(FutureContract, m["contract"]),
                info=create_with(MarketInfo, m["info"]),
            )
            for m in market_inventory["markets"]
        ]

        output = InventoryResponse(
            crossChainAssets=[
                create_with(CrossChainAsset, cca)
                for cca in market_inventory["crossChainAssets"]
            ],
            feeConfig=create_with(FeeConfig, market_inventory["feeConfig"]),
            markets=markets,
            tradingTiers=[
                create_with(TradingTier, tt) for tt in market_inventory["tradingTiers"]
            ],
        )

        return output

    def get_prices(self, symbol: str) -> PriceResponse:
        response = self.__send_simple_request(f"/market/data/prices?symbol={symbol}")
        response["fundingRateEstimation"] = create_with(
            FundingRateEstimation,
            response["fundingRateEstimation"],
        )
        return create_with(PriceResponse, response)

    def get_stats(self, symbol: str) -> StatsResponse:
        return create_with(
            StatsResponse,
            self.__send_simple_request(f"/market/data/stats?symbol={symbol}"),
        )

    def get_trades(self, symbol: str) -> TradesResponse:
        response = self.__send_simple_request(f"/market/data/trades?symbol={symbol}")
        return TradesResponse(
            trades=[
                Trade(
                    price=t["price"],
                    quantity=t["quantity"],
                    takerSide=TakerSide(t["takerSide"]),
                    timestamp=t["timestamp"],
                )
                for t in response["trades"]
            ]
        )

    def get_klines(self, symbol: str, interval: Interval) -> KlinesResponse:
        response = self.__send_simple_request(
            f"/market/data/klines?symbol={symbol}&interval={interval.value}"
        )
        return KlinesResponse(
            klines=[create_with(Kline, kline) for kline in response["klines"]]
        )

    def get_open_interest(self, symbol: str) -> OpenInterestResponse:
        """Get open interest for a symbol

        Endpoint: `GET /market/data/open-interest`

        Args:
            symbol: The trading symbol (e.g. "BTC/USDT-P")

        Returns:
            OpenInterestResponse: The open interest data

        -----------------------------------------------------------------------
        """
        response = self.__send_simple_request(
            f"/market/data/open-interest?symbol={symbol}"
        )
        return create_with(OpenInterestResponse, response)

    def get_orderbook(self, symbol: str, depth: int, granularity: float) -> OrderBook:
        """
        Get the orderbook price levels.
        It will return up to depth price levels on both side. The price level will be aggreated based on granularity.

        Endpoint: `GET /market/data/orderbook`

        Args:
            symbol: The trading symbol (e.g. "BTC/USDT-P")
            depth: The number of price levels to return on each side
            granularity: The price level granularity (e.g. 0.01)

        Return type:
        ```python
         OrderBook {
            ask: {
                price: str
                quantity: str
            }[]
            bid: {
                price: str
                quantity: str
            }[]
        }
        ```

        -----------------------------------------------------------------------
        """
        depth = int(depth)
        if depth < 1 or depth > 100:
            raise ValueError(
                "Depth must be a positive integer between 1 and 100, inclusive"
            )

        self.__check_symbol(symbol)

        contract = self.future_contracts.get(symbol)
        granularities = contract.orderbookGranularities
        if str(granularity) not in granularities:
            raise ValueError(
                f"Granularity for symbol {symbol} must be one of {granularities}"
            )

        response = self.__send_simple_request(
            f"/market/data/orderbook?symbol={symbol}&depth={depth}&granularity={granularity}"
        )

        ask_levels = [
            OrderBookLevel(price=level["price"], quantity=level["quantity"])
            for level in response["ask"]["levels"]
        ]
        bid_levels = [
            OrderBookLevel(price=level["price"], quantity=level["quantity"])
            for level in response["bid"]["levels"]
        ]

        return OrderBook(ask=ask_levels, bid=bid_levels)

    ### ===================================================== Account API =====================================================

    ### ------------------------------------------------ Account API - Capital ------------------------------------------------

    def get_capital_balance(self) -> CapitalBalance:
        """
        Get the balance of your account.
        The returned balance is your net equity which includes unrealized PnL.

        Endpoint: `GET /capital/balance`

        ```python
        capital_balance = client.get_capital_balance()
        print(capital_balance.balance)
        ```

        ```
        CapitalBalance {
            balance: str
        }
        ```
        -----------------------------------------------------------------------
        """
        self.__check_auth_data()
        response = self.__send_authorized_request(
            "GET", f"/capital/balance?accountId={self.account_id}"
        )
        return create_with(CapitalBalance, response)

    def get_capital_history(self) -> CapitalHistory:
        """
        Get the deposit and withdraw history of your account.
        It will return most recent up to 100 deposit and 100 withdraw.

        Endpoint: `GET /capital/history`

        ```python
        capital_history = client.get_capital_history()
        ```

        ```python
        Transaction {
            assetId: int
            blockNumber: int
            chain: Optional[str]
            etaTsSec: int
            id: int
            quantity: str
            status: str
            timestampSec: int
            token: Optional[str]
            transactionHash: Union[str,str]
            transactionType: str
        }

        CapitalHistory {
            transactions: List[Transaction]
        }
        ```
        -----------------------------------------------------------------------
        """
        self.__check_auth_data()
        response = self.__send_authorized_request(
            "GET", f"/capital/history?accountId={self.account_id}"
        )

        return CapitalHistory(
            transactions=[
                create_with(Transaction, tx) for tx in response["transactions"]
            ]
        )

    def withdraw(
        self,
        coin: str,
        withdraw_address: str,
        quantity: str,
        max_fees: str,
        network: str = "arbitrum",
    ) -> WithdrawResponse:
        """Submit a withdraw request.

        Endpoint: `POST /capital/withdraw`

        Args:
            coin: The coin to withdraw (e.g. "USDT")
            withdraw_address: The address to withdraw to
            quantity: The amount to withdraw should be no more than maximalWithdraw returned by /trade/account/info endpoint, otherwise it will be rejected.
            max_fees: Maximum fees allowed for the withdrawal
            network: The network to withdraw on (default "arbitrum")

        Returns:
            WithdrawResponse: The response containing the order ID

        -----------------------------------------------------------------------
        """
        self.__check_auth_data()

        # Create withdraw request payload
        request = WithdrawRequest(
            accountId=self.account_id,
            coin=coin,
            withdrawAddress=withdraw_address,
            network=network,
            quantity=quantity,
            maxFees=max_fees,
            signature=self.__sign_withdraw_payload(
                coin, withdraw_address, quantity, max_fees
            ),
        )

        response = self.__send_authorized_request(
            "POST", "/capital/withdraw", json=asdict(request)
        )
        return create_with(WithdrawResponse, response)

    def transfer(self, coin: str, quantity: str, dstPublicKey: str, max_fees: str):
        """
        Request fund transfer to another account.

        Endpoint: `POST /capital/transfer`

        Args:
            coin: The coin to transfer
            fees: The fees to transfer
            quantity: The quantity to transfer
        """

        nonce = time_ns() // 1_000

        request = TransferRequest(
            accountId=self.account_id,
            coin=coin,
            nonce=nonce,
            dstPublicKey=dstPublicKey.replace("0x", ""),
            fees=max_fees,
            quantity=quantity,
            signature=self.__sign_transfer_payload(
                nonce, coin, quantity, dstPublicKey, max_fees
            ),
        )

        response = self.__send_authorized_request(
            "POST", "/capital/transfer", json=asdict(request)
        )

        return create_with(TransferResponse, response)

    def get_deposit_info(self, public_key: str) -> DepositInfo:
        """Get deposit address information.

        Endpoint: `GET /capital/deposit-info`

        Args:
            public_key: The public key to get deposit info for

        Returns:
            DepositInfo: The deposit address information

        ```python
        DepositInfo { depositAddressEvm: str }
        ```
        -----------------------------------------------------------------------
        """
        response = self.__send_authorized_request(
            "GET",
            f"/capital/deposit-info?accountId={self.account_id}&publicKey={public_key}",
        )
        return create_with(DepositInfo, response)

    def __sign_withdraw_payload(
        self, coin: str, withdraw_address: str, quantity: str, max_fees: str
    ) -> str:
        """Sign a withdrawal request payload.

        Args:
            coin: The coin to withdraw
            withdraw_address: The withdrawal address
            quantity: The withdrawal amount
            max_fees: Maximum fees allowed

        Returns:
            str: The signature for the withdrawal request
        """
        # Get asset ID from exchange info
        if self.future_contracts is None:
            self.get_exchange_info()

        # Find asset ID for the coin
        asset_id = None
        for contract in self.future_contracts.values():
            if contract.settlementSymbol == coin:
                asset_id = contract.id
                break

        if asset_id is None:
            raise ValueError(f"Unknown coin: {coin}")

        # Create payload bytes
        asset_id_bytes = asset_id.to_bytes(4, "big")
        quantity_bytes = int(float(quantity) * 1e6).to_bytes(
            8, "big"
        )  # Assuming 6 decimals for USDT
        max_fees_bytes = int(float(max_fees) * 1e6).to_bytes(
            8, "big"
        )  # Assuming 6 decimals for USDT
        address_bytes = bytes.fromhex(withdraw_address.replace("0x", ""))

        # Combine payload
        payload = asset_id_bytes + quantity_bytes + max_fees_bytes + address_bytes

        # Sign payload
        return self.__sign_payload(payload)

    def __sign_transfer_payload(
        self,
        nonce: int,
        coin: str,
        quantity: int,
        dst_account_public_key: str,
        max_fees_percent: str,
    ) -> str:
        # Get asset ID from exchange info
        if self.future_contracts is None:
            self.get_exchange_info()

        # Find asset ID for the coin
        asset_id = None
        for contract in self.future_contracts.values():
            if contract.settlementSymbol == coin:
                asset_id = contract.id
                break

        if asset_id is None:
            raise ValueError(f"Unknown coin: {coin}")

        # Create payload bytes
        nonce_bytes = nonce.to_bytes(8, "big")
        asset_id_bytes = asset_id.to_bytes(4, "big")
        quantity_bytes = int(float(quantity) * 1e6).to_bytes(
            8, "big"
        )  # Assuming 6 decimals for USDT
        max_fees_bytes = int(float(max_fees_percent)).to_bytes(8, "big")
        address_bytes = bytes.fromhex(dst_account_public_key.replace("0x", ""))

        # Combine payload
        payload = (
            nonce_bytes
            + asset_id_bytes
            + quantity_bytes
            + address_bytes
            + max_fees_bytes
        )

        # Sign payload
        return self.__sign_payload(payload)

    ############################################################################
    ## Trade API endpoints, account_id and api_key must be set

    def get_account_info(self) -> AccountInfo:
        """
        Get account information/details

        Endpoint: `GET /trade/account/info`

        ```python
        account_info = client.get_account_info()
        print(account_info.balance)
        ```

        Return type:

        ```python
        AccountInfo {
            assets: {
                quantity: str
                symbol: str
            }[]
            balance: str
            maximalWithdraw: str
            numFreeTransfersRemaining: int
            positions: {
                direction: str
                entryNotional: str
                markPrice: str
                notionalValue: str
                openPrice: str
                quantity: str
                symbol: str
                unrealizedFundingPnl: str
                unrealizedTradingPnl: str
            }[]
            totalOrderNotional: str
            totalPositionNotional: str
            totalUnrealizedFundingPnl: str
            totalUnrealizedPnl: str
            totalUnrealizedTradingPnl: str
            tradeMakerFeeRate: str
            tradeTakerFeeRate: str
        }
        ```
        -----------------------------------------------------------------------
        """
        self.__check_auth_data()
        response = self.__send_authorized_request(
            "GET", f"/trade/account/info?accountId={self.account_id}"
        )

        assets = [create_with(Asset, asset) for asset in response["assets"]]
        positions = [
            create_with(Position, position) for position in response["positions"]
        ]

        return AccountInfo(
            assets=assets,
            balance=response["balance"],
            maximalWithdraw=response["maximalWithdraw"],
            numFreeTransfersRemaining=response["numFreeTransfersRemaining"],
            positions=positions,
            totalOrderNotional=response["totalOrderNotional"],
            totalPositionNotional=response["totalPositionNotional"],
            totalUnrealizedFundingPnl=response["totalUnrealizedFundingPnl"],
            totalUnrealizedPnl=response["totalUnrealizedPnl"],
            totalUnrealizedTradingPnl=response["totalUnrealizedTradingPnl"],
            tradeMakerFeeRate=response["tradeMakerFeeRate"],
            tradeTakerFeeRate=response["tradeTakerFeeRate"],
        )

    def get_account_trades(self) -> AccountTradesResponse:
        """
        Get the trades history of your account.
        It will return most recent up to 100 records.

        Endpoint: `GET /trade/account/trades`

        ```python
        account_trades = client.get_account_trades()
        ```

        Return type:

        ```python
        AccountTradesResponse {
            trades: {
                askAccountId: int
                askOrderId: int
                bidAccountId: int
                bidOrderId: int
                fee: str
                id: int
                orderType: str
                price: str
                quantity: str
                realizedPnl: str
                side: str
                symbol: str
                timestamp: int
            }[]
        }
        ```
        -----------------------------------------------------------------------
        """
        self.__check_auth_data()
        response = self.__send_authorized_request(
            "GET", f"/trade/account/trades?accountId={self.account_id}"
        )
        trades = [create_with(AccountTrade, trade) for trade in response["trades"]]
        return AccountTradesResponse(trades=trades)

    def get_settlements_history(self) -> SettlementsResponse:
        """
        You can obtain the history of settled trades.

        Endpoint: `GET /trade/account/settlements_history`

        ```python
        settlements = client.get_settlements_history()
        ```

        Return type:

        ```python
        SettlementsResponse {
            settlements: {
                direction: str
                indexPrice: str
                quantity: str
                settledAmount: str
                symbol: str
                timestamp: int
            }[]
        }
        ```
        -----------------------------------------------------------------------
        """
        self.__check_auth_data()
        response = self.__send_authorized_request(
            "GET", f"/trade/account/settlements_history?accountId={self.account_id}"
        )
        settlements = [
            create_with(Settlement, settlement)
            for settlement in response["settlements"]
        ]
        return SettlementsResponse(settlements=settlements)

    def get_pending_orders(self) -> PendingOrdersResponse:
        """
        Get pending orders

        Endpoint: `GET /trade/orders`

        ```python
        pending_orders = client.get_pending_orders()
        ```

        Return type:
        ```python
        PendingOrdersResponse {
            orders: {
                accountId: int
                availableQuantity: str
                contractId: Optional[int]
                creationTime: Optional[int]
                finishTime: Optional[int]
                numOrdersRemaining: Optional[int]
                numOrdersTotal: Optional[int]
                orderId: str
                orderType: OrderType
                price: Optional[str]
                quantityMode: Optional[str]
                side: Side
                status: OrderStatus
                symbol: str
                totalQuantity: Optional[str]
                triggerPrice: Optional[str]
            }[]
        }
        ```
        -----------------------------------------------------------------------
        """
        self.__check_auth_data()
        response = self.__send_authorized_request(
            "GET", f"/trade/orders?accountId={self.account_id}"
        )
        orders = [create_with(Order, order_data) for order_data in response]
        return PendingOrdersResponse(orders=orders)

    def get_order_details(
        self, order_id: Optional[int] = None, nonce: Optional[int] = None
    ) -> Order:
        """
        Get order details

        Endpoint: `GET /trade/order`

        Either the order_id or the nonce can be used to query the order details

        ```python
        order_details = client.get_order_details(order_id=123)
        # or
        order_details = client.get_order_details(nonce=1234567)
        ```

        Return type:
        ```python
        Order {
            accountId: int
            availableQuantity: str
            contractId: Optional[int]
            creationTime: Optional[int]
            finishTime: Optional[int]
            numOrdersRemaining: Optional[int]
            numOrdersTotal: Optional[int]
            orderId: str
            orderType: OrderType
            price: Optional[str]
            quantityMode: Optional[str]
            side: Side
            status: OrderStatus
            symbol: str
            totalQuantity: Optional[str]
            triggerPrice: Optional[str]
        }
        ```
        -----------------------------------------------------------------------
        """
        self.__check_order_selector(order_id, nonce)
        self.__check_auth_data()

        order_selector = (
            f"orderId={order_id}" if order_id is not None else f"nonce={nonce}"
        )
        response = self.__send_authorized_request(
            "GET", f"/trade/order?accountId={self.account_id}&{order_selector}"
        )

        response["numOrdersTotal"] = response.get("numOrdersTotal")
        response["numOrdersRemaining"] = response.get("numOrdersRemaining")
        response["totalQuantity"] = response.get("totalQuantity")
        response["quantityMode"] = response.get("quantityMode")
        response["price"] = response.get("price")
        response["triggerPrice"] = response.get("triggerPrice")
        response["finishTime"] = response.get("finishTime")
        response["orderFlags"] = response.get("orderFlags")

        return create_with(Order, response)

    # Order API endpoints require the private key to be set

    def place_market_order(
        self,
        symbol: str,
        quantity: float,
        side: Side,
        max_fees_percent: float,
        trigger_price: Optional[float] = None,
        twap_config: Optional[TWAPConfig] = None,
        creation_deadline: Optional[int] = None,
        order_flags: Optional[OrderFlags] = None,
        tpsl: Optional[TPSLConfig] = None,
    ) -> tuple[Nonce, OrderId]:
        """
        Place a market order

        Endpoint: `POST /trade/order`

        ```python
        (nonce, order_id) = client.place_market_order("BTC/USDT-P", 0.0001, Side.BUY, max_fees_percent)
        (nonce, order_id) = client.place_market_order("BTC/USDT-P", 0.0001, Side.SELL, max_fees_percent)
        (nonce, order_id) = client.place_market_order("BTC/USDT-P", 0.0001, Side.BID, max_fees_percent, creation_deadline=2)
        (nonce, order_id) = client.place_market_order("BTC/USDT-P", 0.0001, Side.ASK, max_fees_percent, trigger_price=1_000_000)
        (nonce, order_id) = client.place_market_order("SOL/USDT-P", 1, Side.BID, max_fees_percent, twap_config=twap_config)
        (nonce, trigger_market_order_id) = client.place_market_order("BTC/USDT-P", 0.001, Side.ASK, max_fees_percent, trigger_price=90_100)
        ```
        """
        self.__check_auth_data()
        self.__check_symbol(symbol)

        if side == Side.BUY:
            side = Side.BID
        elif side == Side.SELL:
            side = Side.ASK

        if twap_config is not None and trigger_price is not None:
            raise ValueError("Can not set trigger price for TWAP order")

        if twap_config is not None and tpsl is not None:
            raise ValueError("Can not set tpsl for TWAP order")

        if tpsl is not None and len(tpsl.legs) > 0:
            return self._place_parent_with_tpsl(
                symbol=symbol,
                price=None,
                quantity=quantity,
                side=side,
                max_fees_percent=max_fees_percent,
                trigger_price=trigger_price,
                creation_deadline=creation_deadline,
                order_flags=order_flags,
                tpsl=tpsl,
            )

        nonce = time_ns() // 1_000
        request_data = self._create_order_request_data(
            nonce,
            symbol,
            quantity,
            side,
            max_fees_percent,
            trigger_price,
            None,
            creation_deadline,
            twap_config=twap_config,
            order_flags=order_flags,
        )
        request_data["accountId"] = self.account_id
        response = self.__send_authorized_request(
            "POST", f"/trade/order", json=request_data
        )
        order_id = int(response["orderId"])
        return (nonce, order_id)

    def place_limit_order(
        self,
        symbol: str,
        quantity: float,
        price: float,
        side: Side,
        max_fees_percent: float,
        trigger_price: Optional[float] = None,
        creation_deadline: Optional[int] = None,
        order_flags: Optional[OrderFlags] = None,
        tpsl: Optional[TPSLConfig] = None,
    ) -> tuple[Nonce, OrderId]:
        """
        Place a limit order

        Endpoint: `POST /trade/order`

        ```python
        (nonce, order_id) = client.place_limit_order("BTC/USDT-P", 0.0001, 80_000, Side.BUY, max_fees_percent)
        (nonce, order_id) = client.place_limit_order("BTC/USDT-P", 0.0001, 80_000, Side.SELL, max_fees_percent)
        (nonce, order_id) = client.place_limit_order("BTC/USDT-P", 0.0001, 80_000, Side.BID, max_fees_percent, creation_deadline=2)
        (nonce, order_id) = client.place_limit_order("BTC/USDT-P", 0.0001, 1_001_000, Side.ASK, max_fees_percent, trigger_price=1_000_000)
        (nonce, limit_order_id) = client.place_limit_order("BTC/USDT-P", 0.001, 6_000, Side.BID, max_fees_percent)
        (nonce, trigger_limit_order_id) = client.place_limit_order("BTC/USDT-P", 0.001, 90_000, Side.ASK, max_fees_percent, trigger_price=90_100)
        ```
        """
        self.__check_auth_data()
        self.__check_symbol(symbol)

        if side == Side.BUY:
            side = Side.BID
        elif side == Side.SELL:
            side = Side.ASK

        if tpsl is not None and len(tpsl.legs) > 0:
            return self._place_parent_with_tpsl(
                symbol=symbol,
                price=price,
                quantity=quantity,
                side=side,
                max_fees_percent=max_fees_percent,
                trigger_price=trigger_price,
                creation_deadline=creation_deadline,
                order_flags=order_flags,
                tpsl=tpsl,
            )

        nonce = time_ns() // 1_000
        request_data = self._create_order_request_data(
            nonce,
            symbol,
            quantity,
            side,
            max_fees_percent,
            trigger_price,
            price,
            creation_deadline,
            order_flags=order_flags,
        )
        request_data["accountId"] = self.account_id
        response = self.__send_authorized_request(
            "POST", f"/trade/order", json=request_data
        )
        order_id = int(response["orderId"])
        return (nonce, order_id)

    def _place_parent_with_tpsl(
        self,
        symbol: str,
        quantity: float,
        price: Optional[float],
        side: Side,
        max_fees_percent: float,
        trigger_price: Optional[float] = None,
        creation_deadline: Optional[int] = None,
        order_flags: Optional[OrderFlags] = None,
        tpsl: Optional[TPSLConfig] = None,
    ) -> tuple[Nonce, OrderId]:
        parent_order_request = CreateOrder(
            symbol=symbol,
            quantity=quantity,
            side=side,
            price=price,
            trigger_price=trigger_price,
            creation_deadline=creation_deadline,
            order_flags=order_flags,
            max_fees_percent=max_fees_percent,
        )

        nonce = time_ns() // 1_000

        tpsl_order_requests = tpsl._as_requests(
            parent_symbol=symbol,
            parent_quantity=quantity,
            parent_side=side,
            parent_nonce=nonce,
            max_fees_percent=max_fees_percent,
        )

        orders = [parent_order_request] + tpsl_order_requests
        orders_data = [
            self.__batch_order_request_data(nonce + i, order)
            for (i, order) in enumerate(orders)
        ]
        request_data = {"accountId": int(self.account_id), "orders": orders_data}

        result = self.__send_authorized_request(
            "POST", f"/trade/orders", json=request_data
        )
        orders = [create_with(BatchResponseOrder, order) for order in result["orders"]]
        if len(orders) < 1:
            raise RuntimeError(
                f"Received empty response to batch order request {request_data=}"
            )
        parent_order: BatchResponseOrder = orders[0]
        return (parent_order.nonce, parent_order.orderId)

    def update_order(
        self,
        order_id: int,
        max_fees_percent: float,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        creation_deadline: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Update an order

        Endpoint: `PUT /trade/order`

        ```python
        max_fees_percent = 0.0005
        client.update_order(order_id, max_fees_percent, quantity=0.002)
        client.update_order(order_id, max_fees_percent, price=1_050_000)
        client.update_order(order_id, max_fees_percent, trigger_price=1_100_000)
        client.update_order(order_id, max_fees_percent, quantity=0.001, price=1_210_000, trigger_price=1_250_000)
        ```
        """
        self.__check_auth_data()
        order = self.get_order_details(order_id=order_id)
        symbol = order.symbol

        request_data_two = self._update_order_generate_sig(
            order,
            price=price,
            side=Side(order.side),
            max_fees_percent=max_fees_percent,
            trigger_price=trigger_price,
            quantity=quantity,
            creation_deadline=creation_deadline,
        )

        return self.__send_authorized_request(
            "PUT", f"/trade/order", json=request_data_two
        )

    def _update_order_generate_sig(
        self,
        order: Order,
        side: Side,
        max_fees_percent: float,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        quantity: Optional[float] = None,
        creation_deadline: Optional[int] = None,
        nonce: Optional[Nonce] = None,
    ) -> Dict[str, Any]:
        """used to generate the signature for the update order request"""
        symbol = order.symbol
        self.__check_symbol(symbol)

        if order.orderType == "MARKET" and price is not None:
            raise ValueError("Can not update price for a market order")

        if order.orderType == "LIMIT" and price is None:
            price = float(order.price)

        if order.triggerPrice is None and trigger_price is not None:
            raise ValueError("Can not update trigger price for a non trigger order")

        if order.triggerPrice is not None and trigger_price is None:
            trigger_price = float(order.triggerPrice)

        if quantity is None:
            quantity = float(order.totalQuantity)

        side = Side(order.side)

        if side == Side.BUY:
            side = Side.BID
        elif side == Side.SELL:
            side = Side.ASK

        nonce = time_ns() // 1_000 if nonce is None else nonce
        request_data = self.__update_order_request_data(
            order.orderId,
            nonce,
            symbol,
            quantity,
            side,
            max_fees_percent,
            price=price,
            trigger_price=trigger_price,
            creation_deadline=creation_deadline,
        )
        request_data["accountId"] = self.account_id
        return request_data

    def cancel_order(
        self, order_id: Optional[int] = None, nonce: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Cancel an order

        Endpoint: `DELETE /trade/order`

        ```python
        client.cancel_order(order_id=123)
        client.cancel_order(nonce=1234567)
        ```
        """
        self.__check_order_selector(order_id, nonce)
        self.__check_auth_data()

        request_data = self._cancel_order_request_data(order_id, nonce, True)
        request_data["accountId"] = int(self.account_id)
        return self.__send_authorized_request(
            "DELETE", f"/trade/order", json=request_data
        )

    def cancel_all_orders(self, contractId: Optional[int] = None) -> Dict[str, Any]:
        """
        Cancel all orders

        Endpoint: `DELETE /trade/orders`

        ```python
        client.cancel_all_orders()
        ```

        Note: currently there is a bug in the API where cancelling all orders is not working.
        This is a workaround to cancel all orders.
        """
        workaround = True

        if workaround:
            orders = self.get_pending_orders().orders
            for order in orders:
                self.cancel_order(order_id=int(order.orderId))
            return
        else:
            self.__check_auth_data()
            nonce = time_ns() // 1_000
            request_data = self._cancel_order_request_data(None, nonce, False)
            request_data["accountId"] = int(self.account_id)
            return self.__send_authorized_request(
                "DELETE", f"/trade/orders", json=request_data
            )

    def batch_orders(
        self, orders: list[CreateOrder | UpdateOrder | CancelOrder]
    ) -> BatchResponse:
        """
        Creating, updating and cancelling orders can be done in a batch
        This requires knowing all details of the existing orders, there is no shortcut for update order details

        Endpoint: `POST /trade/orders`

        ```python
        response = client.batch_orders([
            # Simple market order
            CreateOrder("BTC/USDT-P", Side.SELL, 0.001, max_fees_percent),
            # Simple limit order
            CreateOrder("BTC/USDT-P", Side.SELL, 0.001, max_fees_percent, price=90_000),
            # Trigger market order
            CreateOrder("BTC/USDT-P", Side.SELL, 0.001, max_fees_percent, trigger_price=85_000),
            # Trigger limit order
            CreateOrder("BTC/USDT-P", Side.SELL, 0.001, max_fees_percent, price=84_750, trigger_price=85_000),
            # TWAP order
            CreateOrder("BTC/USDT-P", Side.SELL, 0.001, max_fees_percent, twap_config=TWAPConfig(5, TWAPQuantityMode.FIXED)),
            # Market order, only valid if placed within two seconds
            CreateOrder("BTC/USDT-P", Side.BUY, 0.001, max_fees_percent, creation_deadline=2),
            # Limit order, only valid if placed within one seconds
            CreateOrder("BTC/USDT-P", Side.BUY, 0.001, max_fees_percent, price=90_000, creation_deadline=1),
            # Trigger market order, only valid if placed within three seconds
            CreateOrder("BTC/USDT-P", Side.BUY, 0.001, max_fees_percent, trigger_price=85_000, creation_deadline=3),
            # Trigger limit order, only valid if placed within five seconds
            CreateOrder("BTC/USDT-P", Side.BUY, 0.001, max_fees_percent, price=75_250, trigger_price=75_000, creation_deadline=5),
            # TWAP order only valid if placed within two seconds
            CreateOrder("BTC/USDT-P", Side.SELL, 0.001, max_fees_percent, twap_config=TWAPConfig(5, TWAPQuantityMode.FIXED), creation_deadline=2),
            # Update limit order
            # Need to fill all relevant optional parameters
            UpdateOrder(limit_order_id, "BTC/USDT-P", Side.BUY, 0.001, max_fees_percent, price=60_000),
            # update trigger limit order
            # Need to fill all relevant optional parameters
            UpdateOrder(trigger_limit_order_id, "BTC/USDT-P", Side.ASK, 0.002, max_fees_percent, price=94_000, trigger_price=94_500),
            # update trigger market order
            # Need to fill all relevant optional parameters
            UpdateOrder(trigger_market_order_id, "BTC/USDT-P", Side.ASK, 0.001, max_fees_percent, trigger_price=93_000),
            # Cancel order
            CancelOrder(order_id=limit_order_id),
            CancelOrder(nonce=nonce),
        ])
        ```
        """
        self.__check_auth_data()

        nonce = time_ns() // 1_000
        orders_data = [
            self.__batch_order_request_data(nonce + i, order)
            for (i, order) in enumerate(orders)
        ]
        request_data = {"accountId": int(self.account_id), "orders": orders_data}

        result = self.__send_authorized_request(
            "POST", f"/trade/orders", json=request_data
        )
        orders = [create_with(BatchResponseOrder, order) for order in result["orders"]]
        result["orders"] = orders
        return create_with(BatchResponse, result)

    """ Private helpers """

    def __send_simple_request(self, path: str) -> Any:
        response = requests.get(f"{self.data_api_url}{path}")
        error = _get_http_error(response)
        if error is not None:
            raise error
        return response.json()

    def __check_auth_data(self):
        if self.account_id is None:
            raise RuntimeError("Account ID is not set")

        if self.api_key is None:
            raise RuntimeError("API key is not set")

    def __send_authorized_request(
        self, method: str, path: str, json: Optional[Any] = None
    ) -> Any:
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        response = requests.request(
            method, f"{self.api_url}{path}", headers=headers, json=json
        )
        error = _get_http_error(response)
        if error is not None:
            raise error

        return response.json()

    def __check_symbol(self, symbol: str):
        if self.future_contracts is None:
            self.get_exchange_info()

        if self.future_contracts.get(symbol) is None:
            raise ValueError(f"Unknown symbol: {symbol}")

    def __check_order_selector(self, order_id: Optional[int], nonce: Optional[int]):
        if order_id is None and nonce is None:
            raise ValueError("Either order_id or nonce must be provided")
        # if order_id is not None and nonce is not None:
        #     raise ValueError("Only one of order_id or nonce must be provided")

    def __sign_payload(self, payload: bytes) -> str:
        if self._private_key:
            # Hash the payload
            message_hash = sha256(payload).digest()

            # Sign the hash
            signed_message = self._private_key.sign_msg_hash(message_hash)

            # Extract signature components
            r = signed_message.r.to_bytes(32, "big")
            s = signed_message.s.to_bytes(32, "big")
            v = signed_message.v.to_bytes(1, "big")

            # Combine to form the signature
            signature_hex = r.hex() + s.hex() + v.hex()

            return signature_hex

        if self._private_key_hmac:
            return hmac.new(
                self._private_key_hmac.encode(), payload, sha256
            ).hexdigest()

        raise RuntimeError("Private key is not set")

    def __create_or_update_order_payload(
        self,
        contract: FutureContract,
        nonce: int,
        quantity: float,
        side: Side,
        max_fees_percent: float,
        price: Optional[float],
    ) -> bytes:
        contract_id = contract.id

        nonce_bytes = nonce.to_bytes(8, "big")
        contract_id_bytes = contract_id.to_bytes(4, "big")
        quantity_bytes = int(quantity * pow(10, contract.underlyingDecimals)).to_bytes(
            8, "big"
        )
        price_bytes = b"" if price is None else price_to_bytes(price, contract)
        side_bytes = (0 if side.value == "ASK" else 1).to_bytes(4, "big")
        max_fees_percent_bytes = int(max_fees_percent * pow(10, 8)).to_bytes(8, "big")

        payload = (
            nonce_bytes
            + contract_id_bytes
            + quantity_bytes
            + side_bytes
            + price_bytes
            + max_fees_percent_bytes
        )

        return payload

    def _create_order_request_data(
        self,
        nonce: int,
        symbol: str,
        quantity: float,
        side: Side,
        max_fees_percent: float,
        trigger_price: Optional[float],
        price: Optional[float],
        creation_deadline: Optional[int],
        twap_config: Optional[TWAPConfig] = None,
        parent_order: Optional[OrderIdVariant] = None,
        order_flags: Optional[OrderFlags] = None,
        trigger_direction: Optional[TriggerDirection] = None,
    ) -> Dict[str, Any]:
        self.__check_auth_data()
        self.__check_symbol(symbol)
        contract = self.future_contracts.get(symbol)
        payload = self.__create_or_update_order_payload(
            contract, nonce, quantity, side, max_fees_percent, price
        )
        signature = self.__sign_payload(payload)

        if side == Side.BUY:
            side = Side.BID
        elif side == Side.SELL:
            side = Side.ASK

        request = {
            "nonce": nonce,
            "symbol": symbol,
            "quantity": str(quantity),
            "orderType": "MARKET",
            "side": side.value,
            "maxFeesPercent": str(max_fees_percent),
            "signature": signature,
        }
        if price is not None:
            request["orderType"] = "LIMIT"
            request["price"] = str(price)
        if trigger_price is not None:
            request["triggerPrice"] = str(trigger_price)
            if trigger_direction is not None:
                request["triggerDirection"] = trigger_direction.value
        if twap_config is not None:
            request = request | twap_config.to_dict()
        if creation_deadline is not None:
            deadline = floor(time()) + creation_deadline
            request["creationDeadline"] = deadline
        if parent_order is not None:
            request["parentOrder"] = parent_order.to_dict()
        if order_flags is not None:
            request["orderFlags"] = order_flags.value

        return request

    def __update_order_request_data(
        self,
        order_id: int,
        nonce: int,
        symbol: str,
        quantity: float,
        side: Side,
        max_fees_percent: float,
        price: Optional[float],
        trigger_price: Optional[float],
        creation_deadline: Optional[int],
        order_flags: Optional[OrderFlags] = None,
    ) -> Dict[str, Any]:
        contract = self.future_contracts.get(symbol)
        payload = self.__create_or_update_order_payload(
            contract, nonce, quantity, side, max_fees_percent, price
        )
        signature = self.__sign_payload(payload)
        request = {
            "nonce": nonce,
            "updatedQuantity": str(quantity),
            "quantity": str(quantity),
            "maxFeesPercent": str(max_fees_percent),
            "signature": signature,
        }
        if price is not None:
            request["updatedPrice"] = str(price)
            request["price"] = str(price)
        if order_id is not None:
            request["orderId"] = str(order_id)
        if trigger_price is not None:
            request["updatedTriggerPrice"] = str(trigger_price)
            request["trigger_price"] = str(trigger_price)
        if creation_deadline is not None:
            deadline = floor(time()) + creation_deadline
            request["creationDeadline"] = deadline
        if order_flags is not None:
            request["orderFlags"] = order_flags.value
        return request

    def __cancel_order_payload(
        self, order_id: Optional[int], nonce: Optional[int]
    ) -> bytes:
        if order_id is not None:
            return order_id.to_bytes(8, "big")
        return nonce.to_bytes(8, "big")

    def _cancel_order_request_data(
        self, order_id: Optional[int], nonce: Optional[int], nonce_as_str: bool
    ) -> Dict[str, Any]:
        payload = self.__cancel_order_payload(order_id, nonce)
        signature = self.__sign_payload(payload)
        request = {"signature": signature}
        if order_id is not None:
            request["orderId"] = str(order_id)
        elif nonce_as_str:
            request["nonce"] = str(nonce)
        else:
            request["nonce"] = nonce
        return request

    def __batch_order_request_data(
        self, nonce: int, o: CreateOrder | UpdateOrder | CancelOrder
    ) -> Dict[str, Any]:
        if type(o) is CreateOrder:
            payload = self._create_order_request_data(
                nonce,
                o.symbol,
                o.quantity,
                o.side,
                o.max_fees_percent,
                o.trigger_price,
                o.price,
                o.creation_deadline,
                twap_config=o.twap_config,
                order_flags=o.order_flags,
                parent_order=o.parent_order,
                trigger_direction=o.trigger_direction,
            )
        elif type(o) is UpdateOrder:
            payload = self.__update_order_request_data(
                o.order_id,
                nonce,
                o.symbol,
                o.quantity,
                o.side,
                o.max_fees_percent,
                o.price,
                o.trigger_price,
                o.creation_deadline,
                order_flags=o.order_flags,
            )
        else:
            payload = self._cancel_order_request_data(o.order_id, o.nonce, True)
        payload["action"] = o.action
        return payload
