"""HTTP API client for Hibachi XYZ exchange.

This module provides the main HibachiApiClient class for interacting with the
Hibachi exchange REST API, including market data queries, account management,
and order operations.
"""

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
    BadGateway,
    BadHttpStatus,
    BadRequest,
    DeserializationError,
    Forbidden,
    GatewayTimeout,
    InternalServerError,
    NotFound,
    RateLimited,
    ServiceUnavailable,
    Unauthorized,
    ValidationError,
)
from hibachi_xyz.executors import DEFAULT_HTTP_EXECUTOR, HttpExecutor
from hibachi_xyz.executors.interface import HttpResponse
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


def raise_response_errors(response: HttpResponse) -> None:
    """Check HTTP response status and raise appropriate errors.

    Validates the response status code and raises pre-defined exceptions for non-2XX
    status codes with detailed error messages extracted from the response body.

    Args:
        response: The HTTP response to validate

    Raises:
        BadRequest: For 400 status codes
        Unauthorized: For 401 status codes
        Forbidden: For 403 status codes
        NotFound: For 404 status codes
        RateLimited: For 429 status codes with rate limit details
        BadHttpStatus: For other 4XX status codes
        InternalServerError: For 500 status codes
        BadGateway: For 502 status codes
        ServiceUnavailable: For 503 status codes
        GatewayTimeout: For 504 status codes

    """
    status = response.status

    # Success status codes (2xx)
    if 200 <= status < 300:
        return

    # Extract error message from response body if available
    body = response.body if isinstance(response.body, dict) else {}

    # Try to extract common Hibachi error fields
    code = body.get("errorCode")
    app_status = body.get("status")
    message = body.get("message")

    # Construct error message based on available fields
    if code is not None and app_status is not None and message is not None:
        error_message = f"[{code}] {app_status}: {message}"
    else:
        error_message = str(body) if body else "<no error message>"

    # 4xx Client Errors
    if status == 400:
        raise BadRequest(status, f"Bad request: {error_message}")

    if status == 401:
        raise Unauthorized(status, f"Unauthorized: {error_message}")

    if status == 403:
        raise Forbidden(status, f"Forbidden: {error_message}")

    if status == 404:
        # TODO potentially coalesce into MaintenanceWindow with additional query
        raise NotFound(status, f"Not found: {error_message}")

    if status == 429:
        # Extract rate limit specific fields
        name = body.get("name")  # name of the limit hit
        count = body.get("count")  # current count of the action
        limit = body.get("limit")  # maximum count before limit is reached
        window_duration = body.get(
            "windowDuration"
        )  # optional (duration after which count is reset)

        # Construct detailed rate limit message
        if name is not None and count is not None and limit is not None:
            rate_limit_msg = f"Rate limit '{name}' exceeded: {count}/{limit}"
            if window_duration is not None:
                rate_limit_msg += f" (resets after {window_duration})"
        else:
            rate_limit_msg = f"Rate limit exceeded: {error_message}"

        raise RateLimited(status, rate_limit_msg)

    # Other 4xx errors
    if 400 <= status < 500:
        raise BadHttpStatus(status, f"Client error ({status}): {error_message}")

    # 5xx Server Errors
    if status == 500:
        raise InternalServerError(status, f"Internal server error: {error_message}")

    if status == 502:
        raise BadGateway(status, f"Bad gateway: {error_message}")

    if status == 503:
        raise ServiceUnavailable(status, f"Service unavailable: {error_message}")

    if status == 504:
        raise GatewayTimeout(status, f"Gateway timeout: {error_message}")

    # Other 5xx errors
    if 500 <= status < 600:
        raise InternalServerError(status, f"Server error ({status}): {error_message}")

    # 3xx Redirects or other unexpected status codes
    # This shouldn't normally happen in an API context, but handle it just in case
    raise BadHttpStatus(status, f"Unexpected status code ({status}): {error_message}")


def price_to_bytes(price: HibachiNumericInput, contract: FutureContract) -> bytes:
    """Convert price to bytes representation for signing.

    Converts a price value to an 8-byte representation adjusted for contract
    decimals and scaled by 2^32 for fixed-point representation.

    Args:
        price: The price value to convert
        contract: The future contract containing decimal precision info

    Returns:
        bytes: 8-byte big-endian representation of the scaled price

    """
    return int(
        numeric_to_decimal(price)
        * pow(Decimal("2"), 32)
        * pow(Decimal("10"), contract.settlementDecimals - contract.underlyingDecimals)
    ).to_bytes(8, "big")


class HibachiApiClient:
    """Hibachi API client for trading operations.

    Examples:
        .. code-block:: python

            from hibachi_xyz import HibachiApiClient
            from dotenv import load_dotenv
            import os

            load_dotenv()

            hibachi = HibachiApiClient(
                api_key=os.environ.get('HIBACHI_API_KEY', "your-api-key"),
                account_id=os.environ.get('HIBACHI_ACCOUNT_ID', "your-account-id"),
                private_key=os.environ.get('HIBACHI_PRIVATE_KEY', "your-private"),
            )

            account_info = hibachi.get_account_info()
            print(f"Account Balance: {account_info.balance}")
            print(f"Total Position Notional: {account_info.totalPositionNotional}")

            exchange_info = hibachi.get_exchange_info()
            print(exchange_info)
    """

    _account_id: int | None = None

    _private_key: eth_keys.datatypes.PrivateKey | None = (
        None  # ECDSA for wallet account
    )
    _private_key_hmac: str | None = None  # HMAC for web account

    _future_contracts: dict[str, FutureContract] | None = None

    _http_executor: HttpExecutor

    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        data_api_url: str = DEFAULT_DATA_API_URL,
        account_id: int | None = None,
        api_key: str | None = None,
        private_key: str | None = None,
        executor: HttpExecutor | None = None,
    ):
        """Initialize the Hibachi API client.

        Args:
            api_url: Base URL for the Hibachi API (default: production URL)
            data_api_url: Base URL for the data API (default: production data URL)
            account_id: Your Hibachi account ID (optional, can be set later)
            api_key: Your API key for authentication (optional, can be set later)
            private_key: Private key for signing requests (hex string with or without 0x prefix,
                or HMAC key for web accounts)
            executor: Custom HTTP executor (optional, uses default if not provided)

        """
        if private_key is not None:
            self.set_private_key(private_key)

        self._http_executor = (
            executor
            if executor is not None
            else DEFAULT_HTTP_EXECUTOR(
                api_url=api_url,
                data_api_url=data_api_url,
                api_key=api_key,
            )
        )
        self.set_api_key(api_key)
        self.set_account_id(account_id)

    @property
    def future_contracts(self) -> dict[str, FutureContract]:
        """Get the cached future contracts metadata.

        Returns:
            dict[str, FutureContract]: Dictionary mapping contract symbols to their metadata

        Raises:
            ValidationError: If contracts have not been loaded yet (call get_exchange_info() first)

        """
        if self._future_contracts is None:
            raise ValidationError("future_contracts not yet loaded")
        return self._future_contracts

    @property
    def account_id(self) -> int:
        """Get the current account ID.

        Returns:
            int: The account ID

        Raises:
            ValidationError: If account_id has not been set

        """
        if self._account_id is None:
            raise ValidationError("account_id has not been set")
        return self._account_id

    @property
    def api_key(self) -> str:
        """Get the current API key.

        Returns:
            str: The API key

        Raises:
            ValidationError: If api_key has not been set

        """
        if self._http_executor.api_key is None:
            raise ValidationError("api_key has not been set")
        return self._http_executor.api_key

    def set_account_id(self, account_id: int | None) -> None:
        """Set the account ID for API requests.

        Args:
            account_id: The account ID (int, numeric string, or None)

        Raises:
            ValidationError: If the account_id is an invalid type or format

        """
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
        """Set the API key for authenticated requests.

        Args:
            api_key: The API key string (or None to clear)

        Raises:
            ValidationError: If the api_key is an invalid type

        """
        _api_key = cast(Any, api_key)
        if not isinstance(_api_key, (str, NoneType)):
            raise ValidationError from TypeError(
                f"Unexpected type for api_key {type(api_key)}"
            )

        self._http_executor.api_key = api_key

    def set_private_key(self, private_key: str) -> None:
        """Set the private key for signing requests.

        Supports two formats:
            - Ethereum private key (hex string with or without 0x prefix) for wallet accounts
            - HMAC key (non-hex string) for web accounts

        Args:
            private_key: The private key as a hex string (with/without 0x) or HMAC key

        """
        if private_key.startswith("0x"):
            private_key = private_key[2:]
            private_key_bytes = bytes.fromhex(private_key)
            self._private_key = eth_keys.datatypes.PrivateKey(private_key_bytes)

        if private_key.startswith("0x") is False:
            self._private_key_hmac = private_key

    """ Market API endpoints, can be called without having an account """

    def get_exchange_info(self) -> ExchangeInfo:
        """Get exchange metadata and maintenance information.

        Retrieves all available future contracts, fee configuration, withdrawal limits,
        and maintenance windows. The maintenance status can be "NORMAL", "UNSCHEDULED_MAINTENANCE",
        or "SCHEDULED_MAINTENANCE".

        Returns:
            ExchangeInfo: Exchange metadata including fee config, future contracts,
                withdrawal limits, maintenance windows, and current status

        Raises:
            DeserializationError: If the API response cannot be parsed

        Example:
            .. code-block:: python

                exchange_info = client.get_exchange_info()
                print(exchange_info)

        Endpoint:
            GET /market/exchange-info

        """
        exchange_info = self.__send_simple_request("/market/exchange-info")
        check_maintenance_window(exchange_info)

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
            status = str(exchange_info["status"])
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
        """Get market inventory with contract metadata and latest price information.

        Similar to get_exchange_info, but includes current price data for all contracts,
        cross-chain assets, fee configuration, and trading tiers.

        Returns:
            InventoryResponse: Market inventory including cross-chain assets, fee config,
                markets with contract and price info, and trading tiers

        Raises:
            DeserializationError: If the API response cannot be parsed

        Endpoint:
            GET /market/inventory

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
        """Get current price information for a trading symbol.

        Retrieves mark price, index price, and funding rate estimation for the specified symbol.

        Args:
            symbol: The trading symbol (e.g., "BTC/USDT-P")

        Returns:
            PriceResponse: Price information including mark price, index price, and funding rates

        Raises:
            DeserializationError: If the API response cannot be parsed
            HttpConnectionError: If the API request fails

        Endpoint:
            GET /market/data/prices

        """
        response = self.__send_simple_request(f"/market/data/prices?symbol={symbol}")
        try:
            response["fundingRateEstimation"] = create_with(  # type: ignore
                FundingRateEstimation,
                response["fundingRateEstimation"],  # type: ignore
            )
            result = create_with(PriceResponse, response)
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e
        return result

    def get_stats(self, symbol: str) -> StatsResponse:
        """Get 24-hour statistics for a trading symbol.

        Retrieves 24-hour trading statistics including volume, high/low prices, and price changes.

        Args:
            symbol: The trading symbol (e.g., "BTC/USDT-P")

        Returns:
            StatsResponse: 24-hour trading statistics

        Raises:
            DeserializationError: If the API response cannot be parsed
            HttpConnectionError: If the API request fails

        Endpoint:
            GET /market/data/stats

        """
        response = self.__send_simple_request(f"/market/data/stats?symbol={symbol}")
        try:
            result = create_with(StatsResponse, response)
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e
        return result

    def get_trades(self, symbol: str) -> TradesResponse:
        """Get recent trades for a trading symbol.

        Retrieves the most recent executed trades for the specified symbol.

        Args:
            symbol: The trading symbol (e.g., "BTC/USDT-P")

        Returns:
            TradesResponse: List of recent trades with price, quantity, taker side, and timestamp

        Raises:
            DeserializationError: If the API response cannot be parsed
            HttpConnectionError: If the API request fails

        Endpoint:
            GET /market/data/trades

        """
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
        """Get candlestick (K-line) data for a trading symbol.

        Retrieves historical candlestick data at the specified time interval.

        Args:
            symbol: The trading symbol (e.g., "BTC/USDT-P")
            interval: The time interval for candlesticks (e.g., Interval.ONE_MINUTE)

        Returns:
            KlinesResponse: List of candlestick data with OHLCV information

        Raises:
            DeserializationError: If the API response cannot be parsed
            HttpConnectionError: If the API request fails

        Endpoint:
            GET /market/data/klines

        """
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
        """Get open interest for a trading symbol.

        Retrieves the current open interest (total outstanding contracts) for the specified symbol.

        Args:
            symbol: The trading symbol (e.g., "BTC/USDT-P")

        Returns:
            OpenInterestResponse: The open interest data

        Raises:
            DeserializationError: If the API response cannot be parsed
            HttpConnectionError: If the API request fails

        Endpoint:
            GET /market/data/open-interest

        """
        response = self.__send_simple_request(
            f"/market/data/open-interest?symbol={symbol}"
        )
        try:
            result = create_with(OpenInterestResponse, response)
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e
        return result

    def get_orderbook(self, symbol: str, depth: int, granularity: float) -> OrderBook:
        """Get orderbook price levels for a trading symbol.

        Retrieves aggregated bid and ask price levels from the orderbook. Price levels
        are aggregated based on the specified granularity.

        Args:
            symbol: The trading symbol (e.g., "BTC/USDT-P")
            depth: Number of price levels to return on each side (1-100)
            granularity: Price level granularity for aggregation (e.g., 0.01)

        Returns:
            OrderBook: Orderbook with bid and ask price levels containing price and quantity

        Raises:
            ValueError: If depth is not between 1 and 100, or granularity is not valid
            DeserializationError: If the API response cannot be parsed
            HttpConnectionError: If the API request fails

        Endpoint:
            GET /market/data/orderbook

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
        """Get account balance including unrealized PnL.

        Retrieves the net equity balance for your account, which includes
        unrealized profit and loss from open positions.

        Returns:
            CapitalBalance: Account balance as a string

        Raises:
            DeserializationError: If the API response cannot be parsed

        Example:
            .. code-block:: python

                capital_balance = client.get_capital_balance()
                print(capital_balance.balance)

        Endpoint:
            GET /capital/balance

        """
        response = self.__send_authorized_request(
            "GET", f"/capital/balance?accountId={self.account_id}"
        )
        try:
            result = create_with(CapitalBalance, response)
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e
        return result

    def get_capital_history(self) -> CapitalHistory:
        """Get deposit and withdrawal history for your account.

        Retrieves the most recent deposit and withdrawal transactions, up to
        100 of each transaction type.

        Returns:
            CapitalHistory: List of transactions including deposits and withdrawals

        Raises:
            DeserializationError: If the API response cannot be parsed

        Example:
            .. code-block:: python

                capital_history = client.get_capital_history()

        Endpoint:
            GET /capital/history

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
        """Submit a withdrawal request.

        Submits a request to withdraw funds to an external address. The quantity
        must not exceed the maximalWithdraw value returned by get_account_info().

        Args:
            coin: The coin to withdraw (e.g., "USDT")
            withdraw_address: The destination withdrawal address
            quantity: Amount to withdraw (must not exceed maximalWithdraw)
            max_fees: Maximum fees allowed for the withdrawal
            network: The blockchain network to withdraw on (default: "arbitrum")

        Returns:
            WithdrawResponse: Response containing the withdrawal order ID

        Raises:
            DeserializationError: If the API response cannot be parsed

        Endpoint:
            POST /capital/withdraw

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
            result = create_with(WithdrawResponse, response)
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
        """Request fund transfer to another account.

        Transfers funds from your account to another account identified by its public key.

        Args:
            coin: The coin to transfer (e.g., "USDT")
            quantity: The amount to transfer
            dstPublicKey: Destination account's public key
            max_fees: Maximum fees as a percentage

        Returns:
            TransferResponse: Response containing the transfer details

        Raises:
            DeserializationError: If the API response cannot be parsed

        Endpoint:
            POST /capital/transfer

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
            result = create_with(TransferResponse, response)
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e
        return result

    def get_deposit_info(self, public_key: str) -> DepositInfo:
        """Get deposit address information for a public key.

        Retrieves the EVM deposit address associated with the specified public key.

        Args:
            public_key: The public key to get deposit info for

        Returns:
            DepositInfo: Deposit address information containing the EVM deposit address

        Raises:
            DeserializationError: If the API response cannot be parsed

        Endpoint:
            GET /capital/deposit-info

        """
        response = self.__send_authorized_request(
            "GET",
            f"/capital/deposit-info?accountId={self.account_id}&publicKey={public_key}",
        )
        try:
            result = create_with(DepositInfo, response)
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {response=}") from e
        return result

    def __sign_withdraw_payload(
        self, coin: str, withdraw_address: str, quantity: str, max_fees: str
    ) -> str:
        """Sign a withdrawal request payload.

        Creates a binary payload from withdrawal parameters and signs it using
        the configured private key.

        Args:
            coin: The coin to withdraw (e.g., "USDT")
            withdraw_address: The destination withdrawal address
            quantity: The withdrawal amount
            max_fees: Maximum fees allowed

        Returns:
            str: The hex-encoded signature for the withdrawal request

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
        """Create and sign the payload for a transfer request.

        Args:
            nonce: Unique nonce for this transfer (defaults to current epoch timestamp in μs)
            coin: The coin to transfer (e.g., "USDT")
            quantity: The amount to transfer
            dst_account_public_key: Destination account's public key
            max_fees_percent: Maximum fees as a percentage

        Returns:
            str: The hex-encoded signature

        """
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
        """Get detailed account information.

        Retrieves comprehensive account information including balance, positions,
        assets, fee rates, and withdrawal limits.

        Returns:
            AccountInfo: Account details including balance, positions, assets,
                order notional, unrealized PnL, and fee rates

        Raises:
            DeserializationError: If the API response cannot be parsed

        Example:
            .. code-block:: python

                account_info = client.get_account_info()
                print(account_info.balance)

        Endpoint:
            GET /trade/account/info

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
        """Get account trade history.

        Retrieves the most recent trade history for your account, up to 100 records.

        Returns:
            AccountTradesResponse: List of recent trades with details including price,
                quantity, side, fees, realized PnL, and timestamps

        Raises:
            DeserializationError: If the API response cannot be parsed

        Example:
            .. code-block:: python

                account_trades = client.get_account_trades()

        Endpoint:
            GET /trade/account/trades

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
        """Get settlement history for your account.

        Retrieves the history of settled trades, including position settlements
        and funding rate settlements.

        Returns:
            SettlementsResponse: List of settlements with direction, price, quantity,
                settled amount, symbol, and timestamp

        Raises:
            DeserializationError: If the API response cannot be parsed

        Example:
            .. code-block:: python

                settlements = client.get_settlements_history()

        Endpoint:
            GET /trade/account/settlements_history

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
        """Get all pending orders for your account.

        Retrieves all currently active orders including open, partially filled,
        and triggered orders.

        Returns:
            PendingOrdersResponse: List of pending orders with details including order ID,
                type, side, price, quantity, status, and timestamps

        Raises:
            DeserializationError: If the API response cannot be parsed

        Example:
            .. code-block:: python

                pending_orders = client.get_pending_orders()

        Endpoint:
            GET /trade/orders

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
        """Get detailed information for a specific order.

        Retrieves order details using either the order ID or the nonce used when
        creating the order. At least one identifier must be provided.

        Args:
            order_id: The order ID to query (optional)
            nonce: The nonce used when creating the order (optional)

        Returns:
            Order: Order details including ID, type, side, price, quantity, status,
                and timestamps

        Raises:
            ValidationError: If neither order_id nor nonce is provided
            DeserializationError: If the API response cannot be parsed

        Example:
            .. code-block:: python

                order_details = client.get_order_details(order_id=123)
                # or
                order_details = client.get_order_details(nonce=1234567)

        Endpoint:
            GET /trade/order

        """
        self.__check_order_selector(order_id, nonce)

        order_selector = (
            f"orderId={order_id}" if order_id is not None else f"nonce={nonce}"
        )
        response = self.__send_authorized_request(
            "GET", f"/trade/order?accountId={self.account_id}&{order_selector}"
        )

        try:
            result = create_with(Order, response, implicit_null=True)
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
        """Place a market order.

        Submits a market order that executes immediately at the current market price.
        Supports trigger prices, TWAP execution, and take-profit/stop-loss configurations.

        Args:
            symbol: The trading symbol (e.g., "BTC/USDT-P")
            quantity: The order quantity
            side: Order side (BUY, SELL, BID, or ASK)
            max_fees_percent: Maximum fees as a percentage
            trigger_price: Price to trigger order execution (optional)
            twap_config: Time-weighted average price configuration (optional)
            creation_deadline: Deadline in seconds for order creation (optional)
            order_flags: Additional order flags (optional)
            tpsl: Take-profit/stop-loss configuration (optional)

        Returns:
            tuple[Nonce, OrderId]: Tuple containing the nonce (defaults to current epoch timestamp in μs) and order ID

        Raises:
            ValueError: If both twap_config and trigger_price are set, or if twap_config and tpsl are set
            DeserializationError: If the API response cannot be parsed

        Example:
            .. code-block:: python

                (nonce, order_id) = client.place_market_order("BTC/USDT-P", 0.0001, Side.BUY, max_fees_percent)
                (nonce, order_id) = client.place_market_order("BTC/USDT-P", 0.0001, Side.SELL, max_fees_percent)
                (nonce, order_id) = client.place_market_order("BTC/USDT-P", 0.0001, Side.BID, max_fees_percent, creation_deadline=2)
                (nonce, order_id) = client.place_market_order("BTC/USDT-P", 0.0001, Side.ASK, max_fees_percent, trigger_price=1_000_000)
                (nonce, order_id) = client.place_market_order("SOL/USDT-P", 1, Side.BID, max_fees_percent, twap_config=twap_config)

        Endpoint:
            POST /trade/order

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
        """Place a limit order.

        Submits a limit order that executes only at the specified price or better.
        Supports trigger prices and take-profit/stop-loss configurations.

        Args:
            symbol: The trading symbol (e.g., "BTC/USDT-P")
            quantity: The order quantity
            price: The limit price
            side: Order side (BUY, SELL, BID, or ASK)
            max_fees_percent: Maximum fees as a percentage
            trigger_price: Price to trigger order execution (optional)
            creation_deadline: Deadline in seconds for order creation (optional)
            order_flags: Additional order flags (optional)
            tpsl: Take-profit/stop-loss configuration (optional)

        Returns:
            tuple[Nonce, OrderId]: Tuple containing the nonce (defaults to current epoch timestamp in μs) and order ID

        Raises:
            DeserializationError: If the API response cannot be parsed

        Example:
            .. code-block:: python

                (nonce, order_id) = client.place_limit_order("BTC/USDT-P", 0.0001, 80_000, Side.BUY, max_fees_percent)
                (nonce, order_id) = client.place_limit_order("BTC/USDT-P", 0.0001, 80_000, Side.SELL, max_fees_percent)
                (nonce, order_id) = client.place_limit_order("BTC/USDT-P", 0.0001, 80_000, Side.BID, max_fees_percent, creation_deadline=2)
                (nonce, order_id) = client.place_limit_order("BTC/USDT-P", 0.0001, 1_001_000, Side.ASK, max_fees_percent, trigger_price=1_000_000)
                (nonce, limit_order_id) = client.place_limit_order("BTC/USDT-P", 0.001, 6_000, Side.BID, max_fees_percent)

        Endpoint:
            POST /trade/order

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
        """Place a parent order with take-profit/stop-loss child orders.

        Creates a parent order along with its configured TP/SL child orders in a single batch.

        Args:
            symbol: Trading symbol
            quantity: Order quantity
            price: Limit price (None for market orders)
            side: Order side (BID/ASK)
            max_fees_percent: Maximum fees as percentage
            tpsl: Take-profit/stop-loss configuration
            trigger_price: Trigger price for parent order (optional)
            creation_deadline: Deadline for order creation (optional)
            order_flags: Additional order flags (optional)

        Returns:
            tuple[Nonce, OrderId]: The nonce (defaults to current epoch timestamp in μs) and order ID of the parent order

        Raises:
            DeserializationError: If the API response cannot be parsed

        """
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
            response = create_with(BatchResponse, result)
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
        """Update an existing order.

        Modifies the parameters of an existing order including quantity, price,
        and trigger price. The order is retrieved first to maintain unmodified fields.

        Args:
            order_id: The ID of the order to update
            max_fees_percent: Maximum fees as a percentage
            quantity: Updated order quantity (optional)
            price: Updated limit price (optional)
            trigger_price: Updated trigger price (optional)
            creation_deadline: Deadline in seconds for update (optional)

        Returns:
            Json: The API response

        Raises:
            ValidationError: If update parameters are invalid for the order type
            DeserializationError: If the API response cannot be parsed

        Example:
            .. code-block:: python

                max_fees_percent = 0.0005
                client.update_order(order_id, max_fees_percent, quantity=0.002)
                client.update_order(order_id, max_fees_percent, price=1_050_000)
                client.update_order(order_id, max_fees_percent, trigger_price=1_100_000)
                client.update_order(order_id, max_fees_percent, quantity=0.001, price=1_210_000, trigger_price=1_250_000)

        Endpoint:
            PUT /trade/order

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
        """Generate signature and request data for updating an order.

        Creates the signed request data needed to update an existing order. Infers
        missing fields from the existing order object.

        Args:
            order: The existing order to update
            side: Order side (BID or ASK)
            max_fees_percent: Maximum fees as a percentage
            quantity: Updated order quantity (optional)
            price: Updated limit price (optional)
            trigger_price: Updated trigger price (optional)
            creation_deadline: Deadline in seconds for update (optional)
            nonce: Custom nonce for the update (optional, defaults to current epoch timestamp in μs)

        Returns:
            Dict[str, Any]: The signed request data ready to send to the API

        Raises:
            ValidationError: If update parameters are invalid for the order type

        """
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
        """Cancel an existing order.

        Cancels an order using either the order ID or the nonce used when creating
        the order. At least one identifier must be provided.

        Args:
            order_id: The order ID to cancel (optional)
            nonce: The nonce used when creating the order (optional)

        Returns:
            Json: The API response

        Raises:
            ValidationError: If neither order_id nor nonce is provided

        Example:
            .. code-block:: python

                client.cancel_order(order_id=123)
                client.cancel_order(nonce=1234567)

        Endpoint:
            DELETE /trade/order

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
        """Cancel all pending orders.

        Cancels all currently pending orders for the account. Currently uses a
        workaround that individually cancels each order.

        Args:
            contractId: Contract ID to filter orders (optional, currently unused)

        Returns:
            Json: The API response (empty dict when using workaround)

        Example:
            .. code-block:: python

                client.cancel_all_orders()

        Endpoint:
            DELETE /trade/orders

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
        """Submit multiple order operations in a single batch request.

        Creates, updates, and cancels orders atomically in a single API call.
        All order details must be provided explicitly (no shortcuts for updates).

        Args:
            orders: List of order operations (CreateOrder, UpdateOrder, or CancelOrder)

        Returns:
            BatchResponse: Response containing results for each order operation

        Raises:
            ValidationError: If an order operation is invalid
            DeserializationError: If the API response cannot be parsed

        Example::

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
                # Update limit order (need all relevant optional parameters)
                UpdateOrder(limit_order_id, "BTC/USDT-P", Side.BUY, 0.001, max_fees_percent, price=60_000),
                # Cancel order
                CancelOrder(order_id=limit_order_id),
            ])

        Endpoint:
            POST /trade/orders

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
            response = create_with(BatchResponse, result)
        except (TypeError, IndexError, ValueError) as e:
            raise DeserializationError(f"Received invalid response {result=}") from e
        return response

    """ Deferred helpers """

    def __send_simple_request(self, path: str) -> Json:
        """Send an unauthenticated request to the API.

        Args:
            path: The API endpoint path

        Returns:
            Json: The parsed JSON response body

        """
        return self._http_executor.send_simple_request(path).body

    def __send_authorized_request(
        self,
        method: str,
        path: str,
        json: Json | None = None,
    ) -> Json:
        """Send an authenticated request to the API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: The API endpoint path
            json: Optional JSON payload for the request body

        Returns:
            Json: The parsed JSON response body

        """
        return self._http_executor.send_authorized_request(method, path, json).body

    """ Private helpers """

    def __get_asset_id(self, coin: str) -> int:
        """Get the asset ID for a coin symbol.

        Args:
            coin: The coin symbol (e.g., "USDT")

        Returns:
            int: The asset ID

        Raises:
            ValidationError: If the coin is not recognized by the exchange

        """
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
        """Get the future contract metadata for a trading symbol.

        Args:
            symbol: The trading symbol (e.g., "BTC/USDT-P")

        Returns:
            FutureContract: The contract metadata

        Raises:
            ValidationError: If the symbol is not recognized by the exchange

        """
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
        """Validate that a trading symbol is listed on the exchange.

        Args:
            symbol: The trading symbol to validate

        Raises:
            ValidationError: If the symbol is not recognized by the exchange

        """
        self.__get_contract(symbol)

    def __check_order_selector(self, order_id: int | None, nonce: int | None) -> None:
        """Validate that at least one order identifier is provided.

        Args:
            order_id: The order ID (optional)
            nonce: The order nonce (optional)

        Raises:
            ValidationError: If neither order_id nor nonce is provided

        """
        if order_id is None and nonce is None:
            raise ValidationError from ValueError(
                "Either order_id or nonce must be provided"
            )

    def __sign_payload(self, payload: bytes) -> str:
        """Sign a payload using the configured private key.

        Supports both ECDSA (for wallet accounts) and HMAC (for web accounts) signing.

        Args:
            payload: The bytes to sign

        Returns:
            str: The hex-encoded signature

        Raises:
            RuntimeError: If no private key is configured

        """
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
        """Create the binary payload for creating or updating an order.

        Args:
            contract: The future contract metadata
            nonce: The nonce for this order (defaults to current epoch timestamp in μs)
            quantity: The order quantity
            side: The order side (BID or ASK)
            max_fees_percent: Maximum fees as a percentage
            price: The limit price (None for market orders)

        Returns:
            bytes: The binary payload to be signed

        """
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
        """Create the request data for placing an order.

        Args:
            nonce: Unique nonce for this order (defaults to current epoch timestamp in μs)
            symbol: Trading symbol
            quantity: Order quantity
            side: Order side (BID/ASK)
            max_fees_percent: Maximum fees as percentage
            trigger_price: Trigger price for conditional orders (optional)
            price: Limit price (None for market orders)
            creation_deadline: Deadline for order creation in seconds (optional)
            twap_config: TWAP configuration for time-weighted orders (optional)
            parent_order: Parent order reference for child orders (optional)
            order_flags: Additional order flags (optional)
            trigger_direction: Direction for trigger activation (optional)

        Returns:
            Dict[str, Any]: The signed request data ready to send to the API

        """
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
        """Create the request data for updating an existing order.

        Args:
            order_id: The ID of the order to update
            nonce: Unique nonce for this update (defaults to current epoch timestamp in μs)
            symbol: Trading symbol
            quantity: Updated order quantity
            side: Order side (BID/ASK)
            max_fees_percent: Maximum fees as percentage
            price: Updated limit price (optional)
            trigger_price: Updated trigger price (optional)
            creation_deadline: Deadline for update in seconds (optional)
            order_flags: Additional order flags (optional)

        Returns:
            Dict[str, Any]: The signed request data ready to send to the API

        """
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
        """Create the binary payload for canceling an order.

        Args:
            order_id: The order ID to cancel (optional)
            nonce: The order nonce to cancel (optional)

        Returns:
            bytes: The binary payload to be signed

        Raises:
            ValidationError: If neither order_id nor nonce is provided

        """
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
        """Create the request data for canceling an order.

        Args:
            order_id: The order ID to cancel (optional)
            nonce: The order nonce to cancel (optional)
            nonce_as_str: Whether to format nonce as string (default True)

        Returns:
            Dict[str, Any]: The signed request data ready to send to the API

        """
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
        """Create request data for a batch order operation.

        Args:
            nonce: Base nonce for this operation
            o: The order operation (CreateOrder, UpdateOrder, or CancelOrder)

        Returns:
            JsonObject: The request data with action type included

        Raises:
            ValidationError: If the order type is not recognized

        """
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
