"""
Type definitions for the Hibachi Python SDK.

This module contains type definitions, enums, and dataclasses used throughout
the SDK, organized into logical sections for clarity.
"""

import re
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Self,
    TypeAlias,
    Union,
    overload,
)

from hibachi_xyz.errors import (
    ExchangeError,
    HibachiApiError,  # noqa: F401
    ValidationError,
)

# ============================================================================
# TYPE ALIASES
# ============================================================================

# Core ID types
Nonce: TypeAlias = int
OrderId: TypeAlias = int

# JSON type hierarchy
JsonObject: TypeAlias = dict[str, "JsonValue"]
JsonArray: TypeAlias = list["JsonValue"]
JsonValue: TypeAlias = None | bool | int | float | str | JsonObject | JsonArray
# Although JsonArray is technically first class json and can be root, for the purposes of this SDK we decode responses as dict only
Json: TypeAlias = JsonObject

# Hibachi input types
HibachiIntegralInput: TypeAlias = str | int
HibachiNumericInput: TypeAlias = Decimal | str | float | int

# WebSocket event handler
WsEventHandler: TypeAlias = Callable[[Json], Coroutine[None, None, None]]


# ============================================================================
# NUMERIC CONVERSION UTILITIES
# ============================================================================

DECIMAL_PATTERN = re.compile(r"^\d+(\.\d+)?$")


def full_precision_string(n: HibachiNumericInput) -> str:
    """Convert a numeric input to a full precision string representation."""
    if isinstance(n, str):
        if not DECIMAL_PATTERN.match(n):
            raise ValidationError(f"Invalid numeric input {n}")
        return n
    if isinstance(n, (int, float)):
        n = Decimal(str(n))
    if not isinstance(n, Decimal):
        raise ValidationError(f"Invalid numeric input type {n} - {type(n)}")
    return format(n, "f")


@overload
def numeric_to_decimal(n: HibachiNumericInput) -> Decimal: ...


@overload
def numeric_to_decimal(n: None) -> None: ...


def numeric_to_decimal(n: HibachiNumericInput | None) -> Decimal | None:
    """Convert various numeric input types to Decimal, or None if input is None."""
    if n is None:
        return n
    if isinstance(n, str):
        if not DECIMAL_PATTERN.match(n):
            raise ValidationError(f"Invalid numeric input {n}")
        return Decimal(n)
    if isinstance(n, (int, float)):
        n = Decimal(str(n))
    if not isinstance(n, Decimal):
        raise ValidationError(f"Invalid numeric input type {n} - {type(n)}")
    return n


# ============================================================================
# CORE ENUMS
# ============================================================================


class Interval(Enum):
    """Time intervals for klines/candlestick data."""

    ONE_MINUTE = "1min"
    FIVE_MINUTES = "5min"
    FIFTEEN_MINUTES = "15min"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"


class Side(Enum):
    """Order side (buy/sell)."""

    BID = "BID"
    ASK = "ASK"
    SELL = "SELL"
    BUY = "BUY"


class OrderType(Enum):
    """Order type."""

    LIMIT = "LIMIT"
    MARKET = "MARKET"
    # SCHEDULED_TWAP = "SCHEDULED_TWAP"


class OrderStatus(Enum):
    """Order status."""

    PENDING = "PENDING"
    CHILD_PENDING = "CHILD_PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    SCHEDULED_TWAP = "SCHEDULED_TWAP"
    PLACED = "PLACED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"


class OrderFlags(Enum):
    """Order execution flags."""

    PostOnly = "POST_ONLY"
    Ioc = "IOC"
    ReduceOnly = "REDUCE_ONLY"


class TriggerDirection(Enum):
    """Trigger direction for conditional orders."""

    HIGH = "HIGH"
    LOW = "LOW"


class TakerSide(Enum):
    """Taker side in a trade."""

    Buy = "Buy"
    Sell = "Sell"


class WebSocketSubscriptionTopic(Enum):
    """WebSocket subscription topics."""

    MARK_PRICE = "mark_price"
    SPOT_PRICE = "spot_price"
    FUNDING_RATE_ESTIMATION = "funding_rate_estimation"
    TRADES = "trades"
    KLINES = "klines"
    ORDERBOOK = "orderbook"
    ASK_BID_PRICE = "ask_bid_price"


# ============================================================================
# ORDER CONFIGURATION TYPES
# ============================================================================


@dataclass
class OrderIdVariant:
    """Represents either a nonce or order_id for order identification."""

    nonce: Nonce | None
    order_id: OrderId | None

    @classmethod
    def from_nonce(cls, nonce: Nonce) -> Self:
        if nonce is None:
            raise ValueError("nonce cannot be None")
        return cls(nonce=nonce, order_id=None)

    @classmethod
    def from_order_id(cls, order_id: OrderId) -> Self:
        if order_id is None:
            raise ValueError("order_id cannot be None")
        return cls(nonce=None, order_id=order_id)

    def to_dict(self) -> Dict[str, Any]:
        if self.nonce is not None:
            return {"nonce": str(self.nonce)}
        elif self.order_id is not None:
            return {"orderId": str(self.order_id)}
        raise ValueError("Empty OrderIdVariant: no nonce or order_id set")


class TWAPQuantityMode(Enum):
    """TWAP quantity distribution mode."""

    FIXED = "FIXED"
    RANDOM = "RANDOM"


class TWAPConfig:
    """Configuration for TWAP (Time-Weighted Average Price) orders."""

    duration_minutes: int
    quantity_mode: TWAPQuantityMode

    def __init__(self, duration_minutes: int, quantity_mode: TWAPQuantityMode):
        self.duration_minutes = duration_minutes
        self.quantity_mode = quantity_mode

    def to_dict(self) -> Dict[str, Any]:
        return {
            "twapDurationMinutes": self.duration_minutes,
            "twapQuantityMode": self.quantity_mode.value,
        }


class TPSLConfig:
    """Configuration for Take-Profit/Stop-Loss orders."""

    class Type(Enum):
        """TP/SL order type."""

        TP = "TP"
        SL = "SL"

    @dataclass
    class Leg:
        """Individual TP/SL leg configuration."""

        order_type: "TPSLConfig.Type"
        price: Decimal
        quantity: Decimal | None

    def __init__(self) -> None:
        self.legs: List[TPSLConfig.Leg] = []

    def add_take_profit(
        self, price: HibachiNumericInput, quantity: HibachiNumericInput | None = None
    ) -> Self:
        """Add a take-profit leg to the configuration."""
        self.legs.append(
            TPSLConfig.Leg(
                order_type=TPSLConfig.Type.TP,
                price=numeric_to_decimal(price),
                quantity=numeric_to_decimal(quantity),
            )
        )
        return self

    def add_stop_loss(
        self, price: HibachiNumericInput, quantity: HibachiNumericInput | None = None
    ) -> Self:
        """Add a stop-loss leg to the configuration."""
        self.legs.append(
            TPSLConfig.Leg(
                order_type=TPSLConfig.Type.SL,
                price=numeric_to_decimal(price),
                quantity=numeric_to_decimal(quantity),
            )
        )
        return self

    def _as_requests(
        self,
        *,
        parent_symbol: str,
        parent_quantity: HibachiNumericInput,
        parent_side: "Side",
        parent_nonce: Nonce,
        max_fees_percent: HibachiNumericInput,
    ) -> List["CreateOrder"]:
        """Convert TP/SL configuration to a list of order requests."""
        order_requests = []
        for leg in self.legs:
            side = Side.BID if parent_side == Side.ASK else Side.ASK
            trigger_direction = TriggerDirection.HIGH
            if (leg.order_type == TPSLConfig.Type.TP and parent_side == Side.ASK) or (
                leg.order_type == TPSLConfig.Type.SL and parent_side == Side.BID
            ):
                trigger_direction = TriggerDirection.LOW

            order_requests.append(
                CreateOrder(
                    symbol=parent_symbol,
                    side=side,
                    quantity=leg.quantity or numeric_to_decimal(parent_quantity),
                    max_fees_percent=numeric_to_decimal(max_fees_percent),
                    trigger_price=numeric_to_decimal(max_fees_percent),
                    trigger_direction=trigger_direction,
                    parent_order=OrderIdVariant.from_nonce(parent_nonce),
                    order_flags=OrderFlags.ReduceOnly,
                )
            )
        return order_requests


# ============================================================================
# ORDER TYPES
# ============================================================================


@dataclass
class Order:
    """Represents an order in the exchange."""

    accountId: int
    availableQuantity: str
    contractId: int | None
    creationTime: int | None
    finishTime: int | None
    numOrdersRemaining: int | None
    numOrdersTotal: int | None
    orderFlags: OrderFlags | None
    orderId: int
    orderType: OrderType
    price: str | None
    quantityMode: str | None
    side: Side
    status: OrderStatus
    symbol: str
    totalQuantity: str | None
    triggerPrice: str | None

    def __init__(
        self,
        accountId: int,
        availableQuantity: str,
        orderId: str | int,
        orderType: str,
        side: str,
        status: str,
        symbol: str,
        numOrdersRemaining: int | None = None,
        numOrdersTotal: int | None = None,
        quantityMode: str | None = None,
        finishTime: int | None = None,
        price: str | None = None,
        totalQuantity: str | None = None,
        creationTime: int | None = None,
        contractId: int | None = None,
        orderFlags: str | None = None,
        triggerPrice: str | None = None,
    ):
        self.accountId = accountId
        self.availableQuantity = availableQuantity
        self.contractId = contractId
        self.creationTime = creationTime
        self.finishTime = finishTime
        self.numOrdersRemaining = numOrdersRemaining
        self.numOrdersTotal = numOrdersTotal
        self.orderId = int(orderId)
        self.orderType = OrderType(orderType)
        self.price = price
        self.quantityMode = quantityMode
        self.side = Side(side)
        self.status = OrderStatus(status)
        self.symbol = symbol
        self.totalQuantity = totalQuantity
        self.triggerPrice = triggerPrice
        self.orderFlags = OrderFlags(orderFlags) if orderFlags else None


class CreateOrder:
    """Request to create a new order."""

    action: str = "place"
    symbol: str
    side: Side
    quantity: Decimal
    max_fees_percent: Decimal
    price: Decimal | None
    trigger_price: Decimal | None
    trigger_direction: TriggerDirection | None
    twap_config: TWAPConfig | None
    creation_deadline: Decimal | None
    parent_order: OrderIdVariant | None
    order_flags: OrderFlags | None

    def __init__(
        self,
        symbol: str,
        side: Side,
        quantity: HibachiNumericInput,
        max_fees_percent: HibachiNumericInput,
        price: HibachiNumericInput | None = None,
        trigger_price: HibachiNumericInput | None = None,
        twap_config: TWAPConfig | None = None,
        creation_deadline: HibachiNumericInput | None = None,
        parent_order: OrderIdVariant | None = None,
        order_flags: OrderFlags | None = None,
        trigger_direction: TriggerDirection | None = None,
    ):
        if side == Side.BUY:
            side = Side.BID
        elif side == Side.SELL:
            side = Side.ASK

        self.symbol = symbol
        self.side = side
        self.quantity = numeric_to_decimal(quantity)
        self.max_fees_percent = numeric_to_decimal(max_fees_percent)
        self.price = numeric_to_decimal(price)
        self.trigger_price = numeric_to_decimal(trigger_price)
        self.twap_config = twap_config
        self.creation_deadline = numeric_to_decimal(creation_deadline)
        self.parent_order = parent_order
        self.order_flags = order_flags
        self.trigger_direction = trigger_direction


class UpdateOrder:
    """Request to update an existing order."""

    action: str = "modify"
    order_id: int
    # needed for creating the signature
    symbol: str
    # needed for creating the signature
    side: Side
    quantity: Decimal
    max_fees_percent: Decimal
    price: Decimal | None
    trigger_price: Decimal | None
    parent_order: OrderIdVariant | None
    order_flags: OrderFlags | None
    creation_deadline: Decimal | None

    def __init__(
        self,
        order_id: int,
        symbol: str,
        side: Side,
        quantity: HibachiNumericInput,
        max_fees_percent: HibachiNumericInput,
        price: HibachiNumericInput | None = None,
        trigger_price: HibachiNumericInput | None = None,
        creation_deadline: HibachiNumericInput | None = None,
        parent_order: OrderIdVariant | None = None,
        order_flags: OrderFlags | None = None,
    ):
        if side == Side.BUY:
            side = Side.BID
        elif side == Side.SELL:
            side = Side.ASK

        self.order_id = order_id
        self.symbol = symbol
        self.side = side
        self.quantity = numeric_to_decimal(quantity)
        self.max_fees_percent = numeric_to_decimal(max_fees_percent)
        self.price = numeric_to_decimal(price)
        self.trigger_price = numeric_to_decimal(trigger_price)
        self.creation_deadline = numeric_to_decimal(creation_deadline)
        self.parent_order = parent_order
        self.order_flags = order_flags


class CancelOrder:
    """Request to cancel an order."""

    action: str = "cancel"
    order_id: int | None
    nonce: int | None

    def __init__(self, order_id: int | None = None, nonce: int | None = None):
        self.order_id = order_id
        self.nonce = nonce


# ============================================================================
# BATCH ORDER RESPONSE TYPES
# ============================================================================


@dataclass
class CreateOrderBatchResponse:
    """Success response to a create order request."""

    nonce: Nonce
    orderId: str
    creationTime: str
    creationTimeNsPartial: str


@dataclass
class UpdateOrderBatchResponse:
    """Success response to an update order request."""

    orderId: str


@dataclass
class CancelOrderBatchResponse:
    """Success response to a cancel order request."""

    nonce: str


@dataclass
class ErrorBatchResponse:
    """Error response for batch operations."""

    errorCode: int
    message: str
    status: str

    def as_exception(self) -> ExchangeError:
        return ExchangeError(
            f"Action failed: {self.errorCode=} {self.status=} {self.message=}"
        )


BatchResponseOrder: TypeAlias = (
    CreateOrderBatchResponse
    | UpdateOrderBatchResponse
    | CancelOrderBatchResponse
    | ErrorBatchResponse
)


def deserialize_batch_response_order(
    data: JsonObject,
) -> BatchResponseOrder:
    """
    Deserialize a batch response order based on which fields are present.

    Logic:
    - If 'errorCode' is present -> ErrorBatchResponse
    - If both 'nonce' and 'orderId' are present -> CreateOrderBatchResponse
    - If only 'orderId' is present -> UpdateOrderBatchResponse
    - If only 'nonce' is present -> CancelOrderBatchResponse

    Raises:
        DeserializationError: If the data cannot be deserialized into any known type
    """
    from hibachi_xyz.errors import DeserializationError
    from hibachi_xyz.helpers import create_with

    try:
        for k in list(data.keys()):  # snapshot keys once
            if data[k] is None:
                del data[k]
        if "errorCode" in data:
            return create_with(ErrorBatchResponse, data)
        elif "nonce" in data and "orderId" in data:
            return create_with(CreateOrderBatchResponse, data)
        elif "orderId" in data:
            return create_with(UpdateOrderBatchResponse, data)
        elif "nonce" in data:
            return create_with(CancelOrderBatchResponse, data)
        else:
            raise DeserializationError(
                f"Unknown batch response order format - missing required fields: {data}"
            )
    except (TypeError, KeyError, ValueError) as e:
        raise DeserializationError(
            f"Failed to deserialize batch response order: {data}"
        ) from e


@dataclass
class BatchResponse:
    """Response containing multiple order operations."""

    orders: list[BatchResponseOrder]


@dataclass
class PendingOrdersResponse:
    """Response containing pending orders."""

    orders: List[Order]


# ============================================================================
# EXCHANGE INFORMATION TYPES
# ============================================================================


@dataclass
class FeeConfig:
    """Fee configuration for the exchange."""

    depositFees: str
    instantWithdrawDstPublicKey: str
    instantWithdrawalFees: List[List[Union[int, float]]]
    tradeMakerFeeRate: str
    tradeTakerFeeRate: str
    transferFeeRate: str
    withdrawalFees: str


@dataclass
class FutureContract:
    """Future contract specification."""

    displayName: str
    id: int
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
    marketCloseTimestamp: str | None = field(default=None)
    marketOpenTimestamp: str | None = field(default=None)
    marketCreationTimestamp: str | None = field(default=None)


@dataclass
class WithdrawalLimit:
    """Withdrawal limits."""

    lowerLimit: str
    upperLimit: str


@dataclass
class MaintenanceWindow:
    """Scheduled maintenance window."""

    begin: float
    end: float
    note: str


@dataclass
class ExchangeInfo:
    """Exchange configuration and status information."""

    feeConfig: FeeConfig
    futureContracts: List[FutureContract]
    instantWithdrawalLimit: WithdrawalLimit
    maintenanceWindow: List[MaintenanceWindow]
    # can be NORMAL, MAINTENANCE
    status: str


@dataclass
class CrossChainAsset:
    """Cross-chain asset information."""

    chain: str
    exchangeRateFromUSDT: str
    exchangeRateToUSDT: str
    instantWithdrawalLowerLimitInUSDT: str
    instantWithdrawalUpperLimitInUSDT: str
    token: str


@dataclass
class TradingTier:
    """Trading tier information."""

    level: int
    lowerThreshold: str
    title: str
    upperThreshold: str


@dataclass
class MarketInfo:
    """Market information for a specific contract."""

    category: str
    markPrice: str
    price24hAgo: str
    priceLatest: str
    tags: List[str]


@dataclass
class Market:
    """Market combining contract and info."""

    contract: FutureContract
    info: MarketInfo


@dataclass
class InventoryResponse:
    """Complete inventory information response."""

    crossChainAssets: List[CrossChainAsset]
    feeConfig: FeeConfig
    markets: List[Market]
    tradingTiers: List[TradingTier]


# ============================================================================
# MARKET DATA TYPES
# ============================================================================


@dataclass
class FundingRateEstimation:
    """Estimated funding rate information."""

    estimatedFundingRate: str
    nextFundingTimestamp: int


@dataclass
class PriceResponse:
    """Price information for a symbol."""

    askPrice: str
    bidPrice: str
    fundingRateEstimation: FundingRateEstimation
    markPrice: str
    spotPrice: str
    symbol: str
    tradePrice: str


@dataclass
class StatsResponse:
    """24-hour statistics for a symbol."""

    high24h: str
    low24h: str
    symbol: str
    volume24h: str


@dataclass
class Trade:
    """Individual trade information."""

    price: str
    quantity: str
    takerSide: TakerSide
    timestamp: int


@dataclass
class TradesResponse:
    """Response containing recent trades."""

    trades: List[Trade]


@dataclass
class Kline:
    """Candlestick/kline data."""

    close: str
    high: str
    low: str
    open: str
    interval: str
    timestamp: int
    volumeNotional: str


@dataclass
class KlinesResponse:
    """Response containing kline data."""

    klines: List[Kline]


@dataclass
class OpenInterestResponse:
    """Open interest information."""

    totalQuantity: str


@dataclass
class OrderBookLevel:
    """Single orderbook price level."""

    price: str
    quantity: str


@dataclass
class OrderBook:
    """Orderbook containing bid and ask levels."""

    ask: List[OrderBookLevel]
    bid: List[OrderBookLevel]


# ============================================================================
# ACCOUNT TYPES
# ============================================================================


@dataclass
class Asset:
    """Asset balance information."""

    quantity: str
    symbol: str


@dataclass
class Position:
    """Position information."""

    direction: str
    entryNotional: str
    markPrice: str
    notionalValue: str
    openPrice: str
    quantity: str
    symbol: str
    unrealizedFundingPnl: str
    unrealizedTradingPnl: str


@dataclass
class AccountInfo:
    """Complete account information."""

    assets: List[Asset]
    balance: str
    maximalWithdraw: str
    numFreeTransfersRemaining: int
    positions: List[Position]
    totalOrderNotional: str
    totalPositionNotional: str
    totalUnrealizedFundingPnl: str
    totalUnrealizedPnl: str
    totalUnrealizedTradingPnl: str
    tradeMakerFeeRate: str
    tradeTakerFeeRate: str


@dataclass
class AccountSnapshot:
    """Snapshot of account state."""

    account_id: int
    balance: str
    positions: List[Position]


@dataclass
class AccountTrade:
    """Individual account trade record."""

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


@dataclass
class AccountTradesResponse:
    """Response containing account trades."""

    trades: List[AccountTrade]


@dataclass
class Settlement:
    """Settlement information."""

    direction: str
    indexPrice: str
    quantity: str
    settledAmount: str
    symbol: str
    timestamp: int


@dataclass
class SettlementsResponse:
    """Response containing settlements."""

    settlements: List[Settlement]


# ============================================================================
# CAPITAL MANAGEMENT TYPES
# ============================================================================


@dataclass
class CapitalBalance:
    """Account capital balance."""

    balance: str


@dataclass
class Transaction:
    """Transaction record."""

    id: int
    assetId: int
    quantity: str
    status: str
    timestampSec: int
    transactionType: str
    transactionHash: Union[str, str] | None
    token: str | None
    etaTsSec: int | None
    blockNumber: int | None
    chain: str | None
    instantWithdrawalChain: str | None
    instantWithdrawalToken: str | None
    isInstantWithdrawal: bool | None
    withdrawalAddress: str | None
    receivingAccountId: int | None
    receivingAddress: str | None
    srcAccountId: int | None
    srcAddress: str | None

    def __init__(
        self,
        id: int,
        assetId: int,
        quantity: str,
        status: str,
        timestampSec: int,
        transactionType: str,
        transactionHash: Union[str, str] | None = None,
        token: str | None = None,
        etaTsSec: int | None = None,
        blockNumber: int | None = None,
        chain: str | None = None,
        instantWithdrawalChain: str | None = None,
        instantWithdrawalToken: str | None = None,
        isInstantWithdrawal: bool | None = None,
        withdrawalAddress: str | None = None,
        receivingAddress: str | None = None,
        receivingAccountId: int | None = None,
        srcAccountId: int | None = None,
        srcAddress: str | None = None,
    ):
        self.id = id
        self.assetId = assetId
        self.quantity = quantity
        self.status = status
        self.timestampSec = timestampSec
        self.transactionType = transactionType
        self.transactionHash = transactionHash
        self.token = token
        self.etaTsSec = etaTsSec
        self.blockNumber = blockNumber
        self.chain = chain
        self.instantWithdrawalChain = instantWithdrawalChain
        self.instantWithdrawalToken = instantWithdrawalToken
        self.isInstantWithdrawal = isInstantWithdrawal
        self.withdrawalAddress = withdrawalAddress
        self.receivingAddress = receivingAddress
        self.receivingAccountId = receivingAccountId
        self.srcAccountId = srcAccountId
        self.srcAddress = srcAddress


@dataclass
class CapitalHistory:
    """Transaction history."""

    transactions: List[Transaction]


@dataclass
class WithdrawRequest:
    """Withdrawal request."""

    accountId: int
    coin: str
    withdrawAddress: str
    network: str
    quantity: Decimal
    maxFees: Decimal
    signature: str

    def __init__(
        self,
        accountId: int,
        coin: str,
        withdrawAddress: str,
        network: str,
        quantity: HibachiNumericInput,
        maxFees: HibachiNumericInput,
        signature: str,
    ):
        self.accountId = accountId
        self.coin = coin
        self.withdrawAddress = withdrawAddress
        self.network = network
        self.quantity = numeric_to_decimal(quantity)
        self.maxFees = numeric_to_decimal(maxFees)
        self.signature = signature


@dataclass
class WithdrawResponse:
    """Withdrawal response."""

    orderId: str


@dataclass
class TransferRequest:
    """Transfer request."""

    accountId: int
    coin: str
    fees: Decimal
    nonce: int
    quantity: Decimal
    dstPublicKey: str
    signature: str

    def __init__(
        self,
        accountId: int,
        coin: str,
        fees: HibachiNumericInput,
        nonce: int,
        quantity: HibachiNumericInput,
        dstPublicKey: str,
        signature: str,
    ):
        self.accountId = accountId
        self.coin = coin
        self.fees = numeric_to_decimal(fees)
        self.nonce = nonce
        self.quantity = numeric_to_decimal(quantity)
        self.dstPublicKey = dstPublicKey
        self.signature = signature


@dataclass
class TransferResponse:
    """Transfer response."""

    status: str


@dataclass
class DepositInfo:
    """Deposit information."""

    depositAddressEvm: str


# ============================================================================
# WEBSOCKET TYPES
# ============================================================================


@dataclass
class WebSocketSubscription:
    """WebSocket subscription configuration."""

    symbol: str
    topic: WebSocketSubscriptionTopic


@dataclass
class WebSocketMarketSubscriptionListResponse:
    """List of WebSocket subscriptions."""

    subscriptions: List[WebSocketSubscription]


@dataclass
class WebSocketResponse:
    """Generic WebSocket response."""

    id: int | None
    result: Dict[str, Any] | None
    status: int | None
    subscriptions: List[WebSocketSubscription] | None


@dataclass
class WebSocketEvent:
    """WebSocket event notification."""

    account: str
    event: str
    data: Dict[str, Any]


# WebSocket Request Parameter Types


@dataclass
class WebSocketOrderCancelParams:
    """Parameters for WebSocket order cancellation."""

    orderId: str
    accountId: str
    nonce: int


@dataclass
class WebSocketOrderModifyParams:
    """Parameters for WebSocket order modification."""

    orderId: str
    accountId: str
    symbol: str
    quantity: str
    price: str
    maxFeesPercent: str


@dataclass
class WebSocketOrderStatusParams:
    """Parameters for WebSocket order status query."""

    orderId: str
    accountId: str


@dataclass
class WebSocketOrdersStatusParams:
    """Parameters for WebSocket orders status query."""

    accountId: str


@dataclass
class WebSocketOrdersCancelParams:
    """Parameters for WebSocket bulk order cancellation."""

    accountId: str
    nonce: str
    contractId: int | None = None


@dataclass
class WebSocketBatchOrder:
    """WebSocket batch order operation."""

    action: str
    nonce: int
    symbol: str
    orderType: str
    side: str
    quantity: str
    price: str
    maxFeesPercent: str
    signature: str
    orderId: str | None = None
    updatedQuantity: str | None = None
    updatedPrice: str | None = None


@dataclass
class WebSocketOrdersBatchParams:
    """Parameters for WebSocket batch order operations."""

    accountId: str
    orders: List[WebSocketBatchOrder]


@dataclass
class WebSocketStreamStartParams:
    """Parameters to start WebSocket stream."""

    accountId: str


@dataclass
class WebSocketStreamPingParams:
    """Parameters for WebSocket stream ping."""

    accountId: str
    listenKey: str
    timestamp: int


@dataclass
class WebSocketStreamStopParams:
    """Parameters to stop WebSocket stream."""

    accountId: str
    listenKey: str
    timestamp: int


@dataclass
class AccountStreamStartResult:
    """Result from starting account stream."""

    accountSnapshot: AccountSnapshot
    listenKey: str


# ============================================================================
# REST API PARAMETER TYPES
# ============================================================================


@dataclass
class OrderPlaceParams:
    """Parameters for placing an order via REST."""

    symbol: str
    quantity: Decimal
    side: Side
    orderType: OrderType
    price: Decimal | None
    trigger_price: Decimal | None
    twap_config: TWAPConfig | None
    maxFeesPercent: Decimal
    orderFlags: str | None
    creation_deadline: Decimal | None
    trigger_direction: TriggerDirection | None

    def __init__(
        self,
        symbol: str,
        quantity: HibachiNumericInput,
        side: Side,
        orderType: OrderType,
        maxFeesPercent: HibachiNumericInput,
        price: HibachiNumericInput | None = None,
        trigger_price: HibachiNumericInput | None = None,
        twap_config: TWAPConfig | None = None,
        orderFlags: str | None = None,
        creation_deadline: int | None = None,
        trigger_direction: TriggerDirection | None = None,
    ):
        self.symbol = symbol
        self.quantity = numeric_to_decimal(quantity)
        self.side = side
        self.orderType = orderType
        self.price = numeric_to_decimal(price)
        self.trigger_price = numeric_to_decimal(trigger_price)
        self.twap_config = twap_config
        self.maxFeesPercent = numeric_to_decimal(maxFeesPercent)
        self.orderFlags = orderFlags
        self.creation_deadline = numeric_to_decimal(creation_deadline)
        self.trigger_direction = trigger_direction


@dataclass
class OrderCancelParams:
    """Parameters for canceling an order."""

    orderId: str
    accountId: str
    nonce: int


@dataclass
class OrderModifyParams:
    """Parameters for modifying an order."""

    orderId: str
    accountId: int
    symbol: str
    quantity: Decimal
    price: Decimal
    side: Side
    maxFeesPercent: Decimal
    nonce: int | None

    def __init__(
        self,
        orderId: str,
        accountId: int,
        symbol: str,
        quantity: HibachiNumericInput,
        price: HibachiNumericInput,
        side: Side,
        maxFeesPercent: HibachiNumericInput,
        nonce: int | None = None,
    ):
        self.orderId = orderId
        self.accountId = accountId
        self.symbol = symbol
        self.quantity = numeric_to_decimal(quantity)
        self.price = numeric_to_decimal(price)
        self.side = side
        self.maxFeesPercent = numeric_to_decimal(maxFeesPercent)
        self.nonce = nonce


@dataclass
class OrderStatusParams:
    """Parameters for querying order status."""

    orderId: str
    accountId: str


@dataclass
class OrdersStatusParams:
    """Parameters for querying all orders status."""

    accountId: int


@dataclass
class OrdersCancelParams:
    """Parameters for bulk order cancellation."""

    accountId: str
    nonce: str
    contractId: int | None = None


@dataclass
class BatchOrder:
    """Batch order operation."""

    action: str
    nonce: int
    symbol: str | None = None
    orderType: OrderType | None = None
    side: Side | None = None
    quantity: str | None = None
    price: str | None = None
    maxFeesPercent: str | None = None
    orderId: str | None = None
    updatedQuantity: str | None = None
    updatedPrice: str | None = None
    signature: str | None = None


@dataclass
class OrdersBatchParams:
    """Parameters for batch order operations."""

    accountId: str
    orders: List[BatchOrder]


@dataclass
class EnableCancelOnDisconnectParams:
    """Parameters to enable cancel-on-disconnect."""

    nonce: int


# ============================================================================
# REST API RESPONSE TYPES
# ============================================================================


@dataclass
class OrderResponse:
    """Order information in response."""

    accountId: str
    availableQuantity: str
    orderId: str
    orderType: OrderType
    price: str
    side: Side
    status: OrderStatus
    symbol: str
    totalQuantity: str


@dataclass
class OrderPlaceResponseResult:
    """Result of order placement."""

    orderId: str


@dataclass
class OrderPlaceResponse:
    """Response from placing an order."""

    id: int
    result: OrderPlaceResponseResult
    status: int


@dataclass
class OrdersStatusResponse:
    """Response containing multiple order statuses."""

    id: int
    result: List[Order]
    status: int | None


@dataclass
class OrderStatusResponse:
    """Response containing single order status."""

    id: int
    result: Order
    status: int | None
