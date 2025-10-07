import hmac
import logging
from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256
from time import time_ns
from types import NoneType
from typing import Any, Dict, cast

import eth_keys.datatypes

from hibachi_xyz.errors import (
    DeserializationError,
    ValidationError,
)
from hibachi_xyz.executors import HttpExecutor, RequestsHttpExecutor
from hibachi_xyz.helpers import (
    DEFAULT_API_URL,
    DEFAULT_DATA_API_URL,
    absolute_creation_deadline,
    check_maintenance_window,
    create_with,
)
from hibachi_xyz.types import (
    AccountInfo,
    AccountTrade,
    AccountTradesResponse,
    Asset,
    BatchResponse,
    CancelOrder,
    CapitalBalance,
    CapitalHistory,
    CreateOrder,
    CreateOrderBatchResponse,
    CrossChainAsset,
    DepositInfo,
    ErrorBatchResponse,
    ExchangeInfo,
    FeeConfig,
    FundingRateEstimation,
    FutureContract,
    HibachiNumericInput,
    Interval,
    InventoryResponse,
    Json,
    JsonArray,
    JsonObject,
    Kline,
    KlinesResponse,
    MaintenanceWindow,
    Market,
    MarketInfo,
    Nonce,
    OpenInterestResponse,
    Order,
    OrderBook,
    OrderBookLevel,
    OrderFlags,
    OrderId,
    OrderIdVariant,
    OrderType,
    PendingOrdersResponse,
    Position,
    PriceResponse,
    Settlement,
    SettlementsResponse,
    Side,
    StatsResponse,
    TakerSide,
    TPSLConfig,
    Trade,
    TradesResponse,
    TradingTier,
    Transaction,
    TransferRequest,
    TransferResponse,
    TriggerDirection,
    TWAPConfig,
    UpdateOrder,
    WithdrawalLimit,
    WithdrawRequest,
    WithdrawResponse,
    deserialize_batch_response_order,
    full_precision_string,
    numeric_to_decimal,
)

log = logging.getLogger(__name__)


def price_to_bytes(price: HibachiNumericInput, contract: FutureContract) -> bytes:
    return int(
        numeric_to_decimal(price)
        * pow(Decimal("2"), 32)
        * pow(Decimal("10"), contract.settlementDecimals - contract.underlyingDecimals)
    ).to_bytes(8, "big")


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

    _account_id: int | None = None

    _private_key: eth_keys.datatypes.PrivateKey | None = (
        None  # ECDSA for wallet account
    )
    _private_key_hmac: str | None = None  # HMAC for web account

    _future_contracts: dict[str, FutureContract] | None = None

    _rest_executor: HttpExecutor

    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        data_api_url: str = DEFAULT_DATA_API_URL,
        account_id: int | None = None,
        api_key: str | None = None,
        private_key: str | None = None,
        executor: HttpExecutor | None = None,
    ):
        if private_key is not None:
            self.set_private_key(private_key)

        self._rest_executor = executor or RequestsHttpExecutor(
            api_url=api_url,
            data_api_url=data_api_url,
            api_key=api_key,
        )
        self.set_api_key(api_key)
        self.set_account_id(account_id)

    @property
    def future_contracts(self) -> dict[str, FutureContract]:
        if self._future_contracts is None:
            raise ValidationError("future_contracts not yet loaded")
        return self._future_contracts

    @property
    def account_id(self) -> int:
        if self._account_id is None:
            raise ValidationError("account_id has not been set")
        return self._account_id

    @property
    def api_key(self) -> str:
        if self._rest_executor.api_key is None:
            raise ValidationError("api_key has not been set")
        return self._rest_executor.api_key

    def set_account_id(self, account_id: int | None) -> None:
        _account_id = cast(Any, account_id)
        if isinstance(_account_id, str):
            if not _account_id.isdigit():
                raise ValidationError(f"Invalid {account_id=}")
            self._account_id = int(_account_id)
        elif isinstance(_account_id, (int, NoneType)):
            self._account_id = _account_id
        else:
            raise ValidationError from TypeError(
                f"Unexpected type for account_id {type(account_id)}"
            )

    def set_api_key(self, api_key: str | None) -> None:
        _api_key = cast(Any, api_key)
        if not isinstance(_api_key, (str, NoneType)):
            raise ValidationError from TypeError(
                f"Unexpected type for api_key {type(api_key)}"
            )

        self._rest_executor.api_key = api_key

    def set_private_key(self, private_key: str) -> None:
        if private_key.startswith("0x"):
            private_key = private_key[2:]
            private_key_bytes = bytes.fromhex(private_key)
            self._private_key = eth_keys.datatypes.PrivateKey(private_key_bytes)

        if private_key.startswith("0x") is False:
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
        check_maintenance_window(exchange_info)  # type: ignore

        try:
            self._future_contracts = {}
            for contract in exchange_info["futureContracts"]:  # type: ignore
                self.future_contracts[contract["symbol"]] = create_with(  # type: ignore
                    FutureContract,
                    contract,  # type: ignore
                )

            fee_config = create_with(FeeConfig, exchange_info["feeConfig"])  # type: ignore

            # Parse future contracts
            future_contracts = [
                create_with(FutureContract, contract)  # type: ignore
                for contract in exchange_info["futureContracts"]  # type: ignore
            ]

            # Parse withdrawal limit
            withdrawal_limit = create_with(
                WithdrawalLimit,
                exchange_info["instantWithdrawalLimit"],  # type: ignore
            )

            # Parse maintenance windows
            maintenance_windows = [
                create_with(MaintenanceWindow, window)  # type: ignore
                for window in exchange_info["maintenanceWindow"]  # type: ignore
            ]
            status = str(exchange_info["status"])  # type: ignore
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(
                f"Received invalid response {exchange_info=}"
            ) from e

        # Create exchange info object
        return ExchangeInfo(
            feeConfig=fee_config,
            futureContracts=future_contracts,
            instantWithdrawalLimit=withdrawal_limit,
            maintenanceWindow=maintenance_windows,
            status=status,
        )

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
                    marketCloseTimestamp: str | None
                    marketOpenTimestamp: str | None
                    minNotional: str
                    minOrderSize: str
                    orderbookGranularities: List[str]
                    initialMarginRate: str
                    maintenanceMarginRate: str
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

        try:
            self._future_contracts = {}
            for market in market_inventory["markets"]:  # type: ignore
                contract = create_with(FutureContract, market["contract"])  # type: ignore
                self.future_contracts[contract.symbol] = contract

            markets = [
                Market(
                    contract=create_with(FutureContract, m["contract"]),  # type: ignore
                    info=create_with(MarketInfo, m["info"]),  # type: ignore
                )
                for m in market_inventory["markets"]  # type: ignore
            ]

            output = InventoryResponse(
                crossChainAssets=[
                    create_with(CrossChainAsset, cca)  # type: ignore
                    for cca in market_inventory["crossChainAssets"]  # type: ignore
                ],
                feeConfig=create_with(FeeConfig, market_inventory["feeConfig"]),  # type: ignore
                markets=markets,
                tradingTiers=[
                    create_with(TradingTier, tt)  # type: ignore
                    for tt in market_inventory["tradingTiers"]  # type: ignore
                ],
            )
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(
                f"Received invalid response {market_inventory=}"
            ) from e

        return output

    def get_prices(self, symbol: str) -> PriceResponse:
        response = self.__send_simple_request(f"/market/data/prices?symbol={symbol}")
        try:
            response["fundingRateEstimation"] = create_with(  # type: ignore
                FundingRateEstimation,
                response["fundingRateEstimation"],  # type: ignore
            )
            result = create_with(PriceResponse, response)  # type: ignore
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e
        return result

    def get_stats(self, symbol: str) -> StatsResponse:
        response = self.__send_simple_request(f"/market/data/stats?symbol={symbol}")
        try:
            result = create_with(StatsResponse, response)  # type: ignore
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e
        return result

    def get_trades(self, symbol: str) -> TradesResponse:
        response = self.__send_simple_request(f"/market/data/trades?symbol={symbol}")
        try:
            result = TradesResponse(
                trades=[
                    Trade(
                        price=t["price"],  # type: ignore
                        quantity=t["quantity"],  # type: ignore
                        takerSide=TakerSide(t["takerSide"]),  # type: ignore
                        timestamp=t["timestamp"],  # type: ignore
                    )
                    for t in response["trades"]  # type: ignore
                ]
            )
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e
        return result

    def get_klines(self, symbol: str, interval: Interval) -> KlinesResponse:
        response = self.__send_simple_request(
            f"/market/data/klines?symbol={symbol}&interval={interval.value}"
        )
        try:
            result = KlinesResponse(
                klines=[create_with(Kline, kline) for kline in response["klines"]]  # type: ignore
            )
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e
        return result

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
        try:
            result = create_with(OpenInterestResponse, response)  # type: ignore
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e
        return result

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

        contract = self.__get_contract(symbol)
        granularities = contract.orderbookGranularities
        if str(granularity) not in granularities:
            raise ValueError(
                f"Granularity for symbol {symbol} must be one of {granularities}"
            )

        response = self.__send_simple_request(
            f"/market/data/orderbook?symbol={symbol}&depth={depth}&granularity={granularity}"
        )

        try:
            ask_levels = [
                OrderBookLevel(price=level["price"], quantity=level["quantity"])  # type: ignore
                for level in response["ask"]["levels"]  # type: ignore
            ]
            bid_levels = [
                OrderBookLevel(price=level["price"], quantity=level["quantity"])  # type: ignore
                for level in response["bid"]["levels"]  # type: ignore
            ]

            result = OrderBook(ask=ask_levels, bid=bid_levels)
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e

        return result

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

        response = self.__send_authorized_request(
            "GET", f"/capital/balance?accountId={self.account_id}"
        )
        try:
            result = create_with(CapitalBalance, response)  # type: ignore
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e
        return result

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
            chain: str | None
            etaTsSec: int
            id: int
            quantity: str
            status: str
            timestampSec: int
            token: str | None
            transactionHash: Union[str,str]
            transactionType: str
        }

        CapitalHistory {
            transactions: List[Transaction]
        }
        ```
        -----------------------------------------------------------------------
        """

        response = self.__send_authorized_request(
            "GET", f"/capital/history?accountId={self.account_id}"
        )

        try:
            result = CapitalHistory(
                transactions=[
                    create_with(Transaction, tx)  # type: ignore
                    for tx in response["transactions"]  # type: ignore
                ]
            )
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e

        return result

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
        try:
            result = create_with(WithdrawResponse, response)  # type: ignore
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e
        return result

    def transfer(
        self,
        coin: str,
        quantity: HibachiNumericInput,
        dstPublicKey: str,
        max_fees: HibachiNumericInput,
    ) -> TransferResponse:
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

        try:
            result = create_with(TransferResponse, response)  # type: ignore
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e
        return result

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
        try:
            result = create_with(DepositInfo, response)  # type: ignore
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e
        return result

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
        asset_id = self.__get_asset_id(coin)
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
        quantity: HibachiNumericInput,
        dst_account_public_key: str,
        max_fees_percent: HibachiNumericInput,
    ) -> str:
        quantity = numeric_to_decimal(quantity)
        max_fees_percent = numeric_to_decimal(max_fees_percent)
        asset_id = self.__get_asset_id(coin)
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

        response = self.__send_authorized_request(
            "GET", f"/trade/account/info?accountId={self.account_id}"
        )

        try:
            assets = [create_with(Asset, asset) for asset in response["assets"]]  # type: ignore
            positions = [
                create_with(Position, position)  # type: ignore
                for position in response["positions"]  # type: ignore
            ]

            result = AccountInfo(
                assets=assets,
                balance=response["balance"],  # type: ignore
                maximalWithdraw=response["maximalWithdraw"],  # type: ignore
                numFreeTransfersRemaining=response["numFreeTransfersRemaining"],  # type: ignore
                positions=positions,
                totalOrderNotional=response["totalOrderNotional"],  # type: ignore
                totalPositionNotional=response["totalPositionNotional"],  # type: ignore
                totalUnrealizedFundingPnl=response["totalUnrealizedFundingPnl"],  # type: ignore
                totalUnrealizedPnl=response["totalUnrealizedPnl"],  # type: ignore
                totalUnrealizedTradingPnl=response["totalUnrealizedTradingPnl"],  # type: ignore
                tradeMakerFeeRate=response["tradeMakerFeeRate"],  # type: ignore
                tradeTakerFeeRate=response["tradeTakerFeeRate"],  # type: ignore
            )
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e

        return result

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

        response = self.__send_authorized_request(
            "GET", f"/trade/account/trades?accountId={self.account_id}"
        )
        try:
            trades = [create_with(AccountTrade, trade) for trade in response["trades"]]  # type: ignore
            result = AccountTradesResponse(trades=trades)
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e
        return result

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

        response = self.__send_authorized_request(
            "GET", f"/trade/account/settlements_history?accountId={self.account_id}"
        )
        try:
            settlements = [
                create_with(Settlement, settlement)  # type: ignore
                for settlement in response["settlements"]  # type: ignore
            ]
            result = SettlementsResponse(settlements=settlements)
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e
        return result

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
                contractId: int | None
                creationTime: int | None
                finishTime: int | None
                numOrdersRemaining: int | None
                numOrdersTotal: int | None
                orderId: str
                orderType: OrderType
                price: str | None
                quantityMode: str | None
                side: Side
                status: OrderStatus
                symbol: str
                totalQuantity: str | None
                triggerPrice: str | None
            }[]
        }
        ```
        -----------------------------------------------------------------------
        """

        response = self.__send_authorized_request(
            "GET", f"/trade/orders?accountId={self.account_id}"
        )
        try:
            orders = [create_with(Order, order_data) for order_data in response]  # type: ignore
            result = PendingOrdersResponse(orders=orders)
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e
        return result

    def get_order_details(
        self, order_id: int | None = None, nonce: int | None = None
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
            contractId: int | None
            creationTime: int | None
            finishTime: int | None
            numOrdersRemaining: int | None
            numOrdersTotal: int | None
            orderId: str
            orderType: OrderType
            price: str | None
            quantityMode: str | None
            side: Side
            status: OrderStatus
            symbol: str
            totalQuantity: str | None
            triggerPrice: str | None
        }
        ```
        -----------------------------------------------------------------------
        """
        self.__check_order_selector(order_id, nonce)

        order_selector = (
            f"orderId={order_id}" if order_id is not None else f"nonce={nonce}"
        )
        response = self.__send_authorized_request(
            "GET", f"/trade/order?accountId={self.account_id}&{order_selector}"
        )

        try:
            response["numOrdersTotal"] = response.get("numOrdersTotal")  # type: ignore
            response["numOrdersRemaining"] = response.get("numOrdersRemaining")  # type: ignore
            response["totalQuantity"] = response.get("totalQuantity")  # type: ignore
            response["quantityMode"] = response.get("quantityMode")  # type: ignore
            response["price"] = response.get("price")  # type: ignore
            response["triggerPrice"] = response.get("triggerPrice")  # type: ignore
            response["finishTime"] = response.get("finishTime")  # type: ignore
            response["orderFlags"] = response.get("orderFlags")  # type: ignore

            result = create_with(Order, response)  # type: ignore
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e

        return result

    # Order API endpoints require the private key to be set

    def place_market_order(
        self,
        symbol: str,
        quantity: HibachiNumericInput,
        side: Side,
        max_fees_percent: HibachiNumericInput,
        trigger_price: HibachiNumericInput | None = None,
        twap_config: TWAPConfig | None = None,
        creation_deadline: HibachiNumericInput | None = None,
        order_flags: OrderFlags | None = None,
        tpsl: TPSLConfig | None = None,
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
        self.__ensure_contract_listed(symbol)

        if side == Side.BUY:
            side = Side.BID
        elif side == Side.SELL:
            side = Side.ASK

        if twap_config is not None and trigger_price is not None:
            raise ValueError("Can not set trigger price for TWAP order")

        if twap_config is not None and tpsl is not None:
            raise ValueError("Can not set tpsl for TWAP order")

        quantity = numeric_to_decimal(quantity)
        max_fees_percent = numeric_to_decimal(max_fees_percent)
        trigger_price = numeric_to_decimal(trigger_price)
        creation_deadline = numeric_to_decimal(creation_deadline)

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
            "POST", "/trade/order", json=request_data
        )
        try:
            order_id = int(response["orderId"])  # type: ignore
            return (nonce, order_id)

        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid {response=}") from e

    def place_limit_order(
        self,
        symbol: str,
        quantity: HibachiNumericInput,
        price: HibachiNumericInput,
        side: Side,
        max_fees_percent: HibachiNumericInput,
        trigger_price: HibachiNumericInput | None = None,
        creation_deadline: HibachiNumericInput | None = None,
        order_flags: OrderFlags | None = None,
        tpsl: TPSLConfig | None = None,
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

        self.__ensure_contract_listed(symbol)

        if side == Side.BUY:
            side = Side.BID
        elif side == Side.SELL:
            side = Side.ASK

        price = numeric_to_decimal(price)
        quantity = numeric_to_decimal(quantity)
        max_fees_percent = numeric_to_decimal(max_fees_percent)
        trigger_price = numeric_to_decimal(trigger_price)
        creation_deadline = numeric_to_decimal(creation_deadline)

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
            "POST", "/trade/order", json=request_data
        )
        try:
            order_id = int(response["orderId"])  # type: ignore
            return (nonce, order_id)

        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid {response=}") from e

    def _place_parent_with_tpsl(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal | None,
        side: Side,
        max_fees_percent: Decimal,
        tpsl: TPSLConfig,
        trigger_price: Decimal | None = None,
        creation_deadline: Decimal | None = None,
        order_flags: OrderFlags | None = None,
    ) -> tuple[Nonce, OrderId]:
        # TODO double conversion
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

        orders: list[CreateOrder] = tpsl._as_requests(
            parent_symbol=symbol,
            parent_quantity=quantity,
            parent_side=side,
            parent_nonce=nonce,
            max_fees_percent=max_fees_percent,
        )

        # prepend parent order request - this MUST be listed first
        orders.insert(0, parent_order_request)

        orders_data: JsonArray = [
            self.__batch_order_request_data(nonce + i, order)
            for (i, order) in enumerate(orders)
        ]
        request_data: JsonObject = {
            "accountId": int(self.account_id),
            "orders": orders_data,
        }

        result = self.__send_authorized_request(
            "POST", "/trade/orders", json=request_data
        )
        try:
            orders = [
                deserialize_batch_response_order(order)  # type: ignore
                for order in result["orders"]  # type: ignore
            ]
            result["orders"] = orders  # type: ignore
            response = create_with(BatchResponse, result)  # type: ignore
            parent_order = response.orders[0]
            if isinstance(parent_order, CreateOrderBatchResponse):
                return (parent_order.nonce, int(parent_order.orderId))
            elif isinstance(parent_order, ErrorBatchResponse):
                raise parent_order.as_exception()
            else:
                raise DeserializationError(
                    f"Received invalid response, {parent_order=} of type {type(parent_order)}"
                )
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {result=}") from e

    def update_order(
        self,
        order_id: int,
        max_fees_percent: HibachiNumericInput,
        quantity: HibachiNumericInput | None = None,
        price: HibachiNumericInput | None = None,
        trigger_price: HibachiNumericInput | None = None,
        creation_deadline: HibachiNumericInput | None = None,
    ) -> Json:
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

        order = self.get_order_details(order_id=order_id)

        price = numeric_to_decimal(price)
        trigger_price = numeric_to_decimal(trigger_price)
        quantity = numeric_to_decimal(quantity)
        max_fees_percent = numeric_to_decimal(max_fees_percent)

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
            "PUT", "/trade/order", json=request_data_two
        )

    def _update_order_generate_sig(
        self,
        order: Order,
        side: Side,
        max_fees_percent: HibachiNumericInput,
        quantity: HibachiNumericInput | None,
        price: HibachiNumericInput | None = None,
        trigger_price: HibachiNumericInput | None = None,
        creation_deadline: HibachiNumericInput | None = None,
        nonce: Nonce | None = None,
    ) -> Dict[str, Any]:
        """used to generate the signature for the update order request"""
        symbol = order.symbol
        self.__ensure_contract_listed(symbol)

        # Infer missing fields from order object
        if order.orderType == OrderType.MARKET and price is not None:
            raise ValidationError from ValueError(
                "Can not update price for a market order"
            )

        # TODO these should raise, warn short term
        if order.orderType == OrderType.LIMIT and price is None:
            price = numeric_to_decimal(order.price)

        if order.triggerPrice is None and trigger_price is not None:
            raise ValidationError from ValueError(
                "Cannot update trigger price for a non trigger order"
            )

        if order.triggerPrice is not None and trigger_price is None:
            trigger_price = order.triggerPrice

        if quantity is None:
            if order.totalQuantity is None:
                raise ValidationError from ValueError(
                    "one of `quantity` or `order.totalQuantity` must be defined"
                )
            quantity = order.totalQuantity

        price = numeric_to_decimal(price)
        trigger_price = numeric_to_decimal(trigger_price)
        quantity = numeric_to_decimal(quantity)
        max_fees_percent = numeric_to_decimal(max_fees_percent)
        creation_deadline = numeric_to_decimal(creation_deadline)

        side = Side(order.side)

        if side == Side.BUY:
            side = Side.BID
        elif side == Side.SELL:
            side = Side.ASK

        nonce = time_ns() // 1_000 if nonce is None else nonce
        request_data = self.__update_order_request_data(
            order_id=order.orderId,
            nonce=nonce,
            symbol=symbol,
            quantity=quantity,
            side=side,
            max_fees_percent=max_fees_percent,
            price=price,
            trigger_price=trigger_price,
            creation_deadline=creation_deadline,
        )
        request_data["accountId"] = self.account_id
        return request_data

    def cancel_order(
        self, order_id: int | None = None, nonce: int | None = None
    ) -> Json:
        """
        Cancel an order

        Endpoint: `DELETE /trade/order`

        ```python
        client.cancel_order(order_id=123)
        client.cancel_order(nonce=1234567)
        ```
        """
        self.__check_order_selector(order_id, nonce)

        request_data = self._cancel_order_request_data(
            order_id=order_id,
            nonce=nonce,
        )
        request_data["accountId"] = int(self.account_id)
        return self.__send_authorized_request(
            "DELETE", "/trade/order", json=request_data
        )

    def cancel_all_orders(self, contractId: int | None = None) -> Json:
        """
        Cancel all orders

        Endpoint: `DELETE /trade/orders`

        ```python
        client.cancel_all_orders()
        ```

        Note: currently there is a bug in the API where cancelling all orders is not working.
        This is a workaround to cancel all orders.
        """
        # TODO remove this
        workaround = True

        if workaround:
            orders = self.get_pending_orders().orders
            for order in orders:
                self.cancel_order(order_id=int(order.orderId))
            return {}
        else:
            nonce = time_ns() // 1_000
            request_data = self._cancel_order_request_data(order_id=None, nonce=nonce)
            request_data["accountId"] = int(self.account_id)
            return self.__send_authorized_request(
                "DELETE", "/trade/orders", json=request_data
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
        nonce = time_ns() // 1_000
        orders_data: JsonArray = [
            self.__batch_order_request_data(nonce + i, order)
            for (i, order) in enumerate(orders)
        ]
        request_data: JsonObject = {
            "accountId": int(self.account_id),
            "orders": orders_data,
        }

        result = self.__send_authorized_request(
            "POST", "/trade/orders", json=request_data
        )
        try:
            orders = [
                deserialize_batch_response_order(order)  # type: ignore
                for order in result["orders"]  # type: ignore
            ]
            result["orders"] = orders  # type: ignore
            response = create_with(BatchResponse, result)  # type: ignore
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {result=}") from e
        return response

    """ Deferred helpers """

    def __send_simple_request(self, path: str) -> Json:
        return self._rest_executor.send_simple_request(path)

    def __send_authorized_request(
        self,
        method: str,
        path: str,
        json: Json | None = None,
    ) -> Json:
        return self._rest_executor.send_authorized_request(method, path, json)

    """ Private helpers """

    def __get_asset_id(self, coin: str) -> int:
        if self._future_contracts is None:
            self.get_exchange_info()

        # Find asset ID for the coin
        asset_id: int | None = None
        for contract in self.future_contracts.values():
            if contract.settlementSymbol == coin:
                asset_id = contract.id
                break

        if asset_id is None:
            known_coins = ", ".join(
                set(
                    contract.settlementSymbol
                    for contract in self.future_contracts.values()
                )
            )
            if not known_coins:
                known_coins = "<none>"
            raise ValidationError from ValueError(
                f"{coin=} not recognized by exchange. Known coins: {known_coins}"
            )

        return asset_id

    def __get_contract(self, symbol: str) -> FutureContract:
        if self._future_contracts is None:
            self.get_exchange_info()

        contract = self.future_contracts.get(symbol)
        if contract is None:
            known_symbols = ", ".join(self.future_contracts.keys())
            if not known_symbols:
                known_symbols = "<none>"
            raise ValidationError from ValueError(
                f"{symbol=} not recognized by exchange. Known symbols: {known_symbols}"
            )

        return contract

    def __ensure_contract_listed(self, symbol: str) -> None:
        self.__get_contract(symbol)

    def __check_order_selector(self, order_id: int | None, nonce: int | None) -> None:
        if order_id is None and nonce is None:
            raise ValidationError from ValueError(
                "Either order_id or nonce must be provided"
            )

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

            return signature_hex  # type: ignore

        if self._private_key_hmac:
            return hmac.new(
                self._private_key_hmac.encode(), payload, sha256
            ).hexdigest()

        raise RuntimeError("Private key is not set")

    def __create_or_update_order_payload(
        self,
        contract: FutureContract,
        nonce: int,
        quantity: Decimal,
        side: Side,
        max_fees_percent: Decimal,
        price: Decimal | None,
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
        quantity: Decimal,
        side: Side,
        max_fees_percent: Decimal,
        trigger_price: Decimal | None,
        price: Decimal | None,
        creation_deadline: Decimal | None,
        twap_config: TWAPConfig | None = None,
        parent_order: OrderIdVariant | None = None,
        order_flags: OrderFlags | None = None,
        trigger_direction: TriggerDirection | None = None,
    ) -> Dict[str, Any]:
        contract = self.__get_contract(symbol)
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
            "quantity": full_precision_string(quantity),
            "orderType": "MARKET",
            "side": side.value,
            "maxFeesPercent": full_precision_string(max_fees_percent),
            "signature": signature,
        }
        if price is not None:
            request["orderType"] = "LIMIT"
            request["price"] = full_precision_string(price)
        if trigger_price is not None:
            request["triggerPrice"] = full_precision_string(trigger_price)
            if trigger_direction is not None:
                request["triggerDirection"] = trigger_direction.value
        if twap_config is not None:
            request = request | twap_config.to_dict()
        if creation_deadline is not None:
            request["creationDeadline"] = absolute_creation_deadline(creation_deadline)
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
        quantity: Decimal,
        side: Side,
        max_fees_percent: Decimal,
        price: Decimal | None,
        trigger_price: Decimal | None,
        creation_deadline: Decimal | None,
        order_flags: OrderFlags | None = None,
    ) -> Dict[str, Any]:
        contract = self.__get_contract(symbol)
        payload = self.__create_or_update_order_payload(
            contract, nonce, quantity, side, max_fees_percent, price
        )
        signature = self.__sign_payload(payload)
        request = {
            "nonce": nonce,
            "maxFeesPercent": full_precision_string(max_fees_percent),
            "signature": signature,
        }

        if quantity is not None:
            request["updatedQuantity"] = full_precision_string(quantity)
            request["quantity"] = full_precision_string(quantity)
        if price is not None:
            request["updatedPrice"] = full_precision_string(price)
            request["price"] = full_precision_string(price)
        if order_id is not None:
            request["orderId"] = str(order_id)
        if trigger_price is not None:
            request["updatedTriggerPrice"] = full_precision_string(trigger_price)
            request["trigger_price"] = full_precision_string(trigger_price)
        if creation_deadline is not None:
            request["creationDeadline"] = absolute_creation_deadline(creation_deadline)
        if order_flags is not None:
            request["orderFlags"] = order_flags.value
        return request

    def __cancel_order_payload(self, order_id: int | None, nonce: int | None) -> bytes:
        if order_id is not None:
            return order_id.to_bytes(8, "big")
        if nonce is None:
            raise ValidationError from ValueError(
                "either of 'order_id' or 'nonce' must be non-None"
            )
        return nonce.to_bytes(8, "big")

    def _cancel_order_request_data(
        self,
        *,
        order_id: int | None,
        nonce: int | None,
        nonce_as_str: bool = True,
    ) -> Dict[str, Any]:
        payload = self.__cancel_order_payload(order_id, nonce)
        signature = self.__sign_payload(payload)
        request = {"signature": signature}
        if order_id is not None:
            request["orderId"] = str(order_id)
        else:
            request["nonce"] = str(nonce) if nonce_as_str else nonce  # type: ignore
        return request

    def __batch_order_request_data(
        self, nonce: int, o: CreateOrder | UpdateOrder | CancelOrder
    ) -> JsonObject:
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
        elif type(o) is CancelOrder:
            payload = self._cancel_order_request_data(
                order_id=o.order_id, nonce=o.nonce
            )
        else:
            raise ValidationError from TypeError(f"Unexpected request type {type(o)}")
        payload["action"] = o.action
        return payload
