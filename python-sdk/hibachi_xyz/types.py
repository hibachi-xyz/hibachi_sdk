from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Self, TypeAlias, Union


class Interval(Enum):
    ONE_MINUTE = "1min"
    FIVE_MINUTES = "5min"
    FIFTEEN_MINUTES = "15min"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"


Nonce: TypeAlias = int
OrderId: TypeAlias = int

# Recursive type for any valid JSON value
JsonValue: TypeAlias = (
    None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
)

# A JSON document (must be object or array at the top level)
Json: TypeAlias = dict[str, JsonValue] | list[JsonValue]


@dataclass
class OrderIdVariant:
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


class HibachiApiError(Exception):
    status_code: int
    message: str

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message


class TWAPQuantityMode(Enum):
    FIXED = "FIXED"
    RANDOM = "RANDOM"


class TWAPConfig:
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
    class Type(Enum):
        TP = "TP"
        SL = "SL"

    @dataclass
    class Leg:
        order_type: "TPSLConfig.Type"
        price: float
        quantity: float | None

    def __init__(self):
        self.legs: List[TPSLConfig.Leg] = []

    def add_take_profit(self, price: float, quantity: float | None = None) -> Self:
        self.legs.append(
            TPSLConfig.Leg(
                order_type=TPSLConfig.Type.TP,
                price=price,
                quantity=quantity,
            )
        )
        return self

    def add_stop_loss(self, price: float, quantity: float | None = None) -> Self:
        self.legs.append(
            TPSLConfig.Leg(
                order_type=TPSLConfig.Type.SL,
                price=price,
                quantity=quantity,
            )
        )
        return self

    def _as_requests(
        self,
        *,
        parent_symbol: str,
        parent_quantity: float,
        parent_side: "Side",
        parent_nonce: Nonce,
        max_fees_percent: float,
    ) -> List["CreateOrder"]:
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
                    quantity=leg.quantity or parent_quantity,
                    max_fees_percent=max_fees_percent,
                    trigger_price=leg.price,
                    trigger_direction=trigger_direction,
                    parent_order=OrderIdVariant.from_nonce(parent_nonce),
                    order_flags=OrderFlags.ReduceOnly,
                )
            )
        return order_requests


class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    # SCHEDULED_TWAP = "SCHEDULED_TWAP"


class TriggerDirection(Enum):
    HIGH = "HIGH"
    LOW = "LOW"


class Side(Enum):
    BID = "BID"
    ASK = "ASK"
    SELL = "SELL"
    BUY = "BUY"


class OrderStatus(Enum):
    PENDING = "PENDING"
    CHILD_PENDING = "CHILD_PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    SCHEDULED_TWAP = "SCHEDULED_TWAP"
    PLACED = "PLACED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"


class OrderFlags(Enum):
    PostOnly = "POST_ONLY"
    Ioc = "IOC"
    ReduceOnly = "REDUCE_ONLY"


@dataclass
class Order:
    accountId: int
    availableQuantity: str
    contractId: int | None
    creationTime: int | None
    finishTime: int | None
    numOrdersRemaining: int | None
    numOrdersTotal: int | None
    orderFlags: OrderFlags | None
    orderId: str
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
        orderId: str,
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
        self.orderId = orderId
        self.orderType = OrderType(orderType)
        self.price = price
        self.quantityMode = quantityMode
        self.side = Side(side)
        self.status = OrderStatus(status)
        self.symbol = symbol
        self.totalQuantity = totalQuantity
        self.triggerPrice = triggerPrice
        self.orderFlags = OrderFlags(orderFlags) if orderFlags else None


@dataclass
class FeeConfig:
    depositFees: str
    instantWithdrawDstPublicKey: str
    instantWithdrawalFees: List[List[Union[int, float]]]
    tradeMakerFeeRate: str
    tradeTakerFeeRate: str
    transferFeeRate: str
    withdrawalFees: str


@dataclass
class FutureContract:
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
    lowerLimit: str
    upperLimit: str


@dataclass
class MaintenanceWindow:
    begin: float
    end: float
    note: str


@dataclass
class ExchangeInfo:
    feeConfig: FeeConfig
    futureContracts: List[FutureContract]
    instantWithdrawalLimit: WithdrawalLimit
    maintenanceWindow: List[MaintenanceWindow]
    # can be NORMAL, MAINTENANCE
    status: str


@dataclass
class FundingRateEstimation:
    estimatedFundingRate: str
    nextFundingTimestamp: int


@dataclass
class PriceResponse:
    askPrice: str
    bidPrice: str
    fundingRateEstimation: FundingRateEstimation
    markPrice: str
    spotPrice: str
    symbol: str
    tradePrice: str


@dataclass
class BatchResponseOrder:
    nonce: Nonce | None
    orderId: OrderId | None

    def __init__(self, nonce: Nonce | None = None, orderId: OrderId | None = None):
        self.nonce = int(nonce) if isinstance(nonce, str) else nonce
        self.orderId = int(orderId) if isinstance(orderId, str) else orderId


@dataclass
class BatchResponse:
    orders: List[BatchResponseOrder]


@dataclass
class StatsResponse:
    high24h: str
    low24h: str
    symbol: str
    volume24h: str


class TakerSide(Enum):
    Buy = "Buy"
    Sell = "Sell"


@dataclass
class Trade:
    price: str
    quantity: str
    takerSide: TakerSide
    timestamp: int


@dataclass
class TradesResponse:
    trades: List[Trade]


@dataclass
class Kline:
    close: str
    high: str
    low: str
    open: str
    interval: str
    timestamp: int
    volumeNotional: str


@dataclass
class KlinesResponse:
    klines: List[Kline]


@dataclass
class OpenInterestResponse:
    totalQuantity: str


@dataclass
class OrderBookLevel:
    price: str
    quantity: str


@dataclass
class OrderBook:
    ask: List[OrderBookLevel]
    bid: List[OrderBookLevel]


@dataclass
class Asset:
    quantity: str
    symbol: str


@dataclass
class Position:
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
class AccountTrade:
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
    trades: List[AccountTrade]


@dataclass
class Settlement:
    direction: str
    indexPrice: str
    quantity: str
    settledAmount: str
    symbol: str
    timestamp: int


@dataclass
class SettlementsResponse:
    settlements: List[Settlement]


@dataclass
class PendingOrdersResponse:
    orders: List[Order]


@dataclass
class CapitalBalance:
    balance: str


@dataclass
class Transaction:
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
    transactions: List[Transaction]


@dataclass
class WithdrawRequest:
    accountId: int
    coin: str
    withdrawAddress: str
    network: str
    quantity: str
    maxFees: str
    signature: str


@dataclass
class WithdrawResponse:
    orderId: str


@dataclass
class TransferRequest:
    accountId: int
    coin: str
    fees: str
    nonce: int
    quantity: str
    dstPublicKey: str
    signature: str


@dataclass
class TransferResponse:
    status: str


@dataclass
class DepositInfo:
    depositAddressEvm: str


class WebSocketSubscriptionTopic(Enum):
    MARK_PRICE = "mark_price"
    SPOT_PRICE = "spot_price"
    FUNDING_RATE_ESTIMATION = "funding_rate_estimation"
    TRADES = "trades"
    KLINES = "klines"
    ORDERBOOK = "orderbook"
    ASK_BID_PRICE = "ask_bid_price"


@dataclass
class WebSocketSubscription:
    symbol: str
    topic: WebSocketSubscriptionTopic


@dataclass
class WebSocketMarketSubscriptionListResponse:
    subscriptions: List[WebSocketSubscription]


# AUTOGEN BELOW


@dataclass
class WebSocketResponse:
    id: int | None
    result: Dict[str, Any] | None
    status: int | None
    subscriptions: List[WebSocketSubscription] | None


@dataclass
class WebSocketEvent:
    account: str
    event: str
    data: Dict[str, Any]


@dataclass
class WebSocketOrderCancelParams:
    orderId: str
    accountId: str
    nonce: int


@dataclass
class WebSocketOrderModifyParams:
    orderId: str
    accountId: str
    symbol: str
    quantity: str
    price: str
    maxFeesPercent: str


@dataclass
class WebSocketOrderStatusParams:
    orderId: str
    accountId: str


@dataclass
class WebSocketOrdersStatusParams:
    accountId: str


@dataclass
class WebSocketOrdersCancelParams:
    accountId: str
    nonce: str
    contractId: int | None = None


@dataclass
class WebSocketBatchOrder:
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
    accountId: str
    orders: List[WebSocketBatchOrder]


@dataclass
class WebSocketStreamStartParams:
    accountId: str


@dataclass
class WebSocketStreamPingParams:
    accountId: str
    listenKey: str
    timestamp: int


@dataclass
class WebSocketStreamStopParams:
    accountId: str
    listenKey: str
    timestamp: int


@dataclass
class AccountSnapshot:
    account_id: int
    balance: str
    positions: List[Position]


@dataclass
class AccountStreamStartResult:
    accountSnapshot: AccountSnapshot
    listenKey: str


@dataclass
class OrderPlaceParams:
    symbol: str
    quantity: float
    side: Side
    orderType: OrderType
    price: str | None
    trigger_price: float | None
    twap_config: TWAPConfig | None
    maxFeesPercent: float
    orderFlags: str | None = None
    creation_deadline: int | None = None
    trigger_direction: TriggerDirection | None = None


@dataclass
class OrderCancelParams:
    orderId: str
    accountId: str
    nonce: int


@dataclass
class OrderModifyParams:
    orderId: str
    accountId: int
    symbol: str
    quantity: str
    price: str
    side: Side
    maxFeesPercent: str
    nonce: int | None


@dataclass
class OrderStatusParams:
    orderId: str
    accountId: str


@dataclass
class OrdersStatusParams:
    accountId: int


@dataclass
class OrdersCancelParams:
    accountId: str
    nonce: str
    contractId: int | None = None


@dataclass
class BatchOrder:
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
    accountId: str
    orders: List[BatchOrder]


@dataclass
class EnableCancelOnDisconnectParams:
    nonce: int


@dataclass
class OrderResponse:
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
    orderId: str


@dataclass
class OrderPlaceResponse:
    id: int
    result: OrderPlaceResponseResult
    status: int


@dataclass
class OrdersStatusResponse:
    id: int
    result: List[Order]
    status: int | None


@dataclass
class OrderStatusResponse:
    id: int
    result: Order
    status: int | None


@dataclass
class CrossChainAsset:
    chain: str
    exchangeRateFromUSDT: str
    exchangeRateToUSDT: str
    instantWithdrawalLowerLimitInUSDT: str
    instantWithdrawalUpperLimitInUSDT: str
    token: str


@dataclass
class TradingTier:
    level: int
    lowerThreshold: str
    title: str
    upperThreshold: str


@dataclass
class MarketInfo:
    category: str
    markPrice: str
    price24hAgo: str
    priceLatest: str
    tags: List[str]


@dataclass
class Market:
    contract: FutureContract
    info: MarketInfo


@dataclass
class InventoryResponse:
    crossChainAssets: List[CrossChainAsset]
    feeConfig: FeeConfig
    markets: List[Market]
    tradingTiers: List[TradingTier]


class CreateOrder:
    action: str = "place"
    symbol: str
    side: Side
    quantity: float
    max_fees_percent: float
    price: float | None
    trigger_price: float | None
    trigger_direction: TriggerDirection | None
    twap_config: TWAPConfig | None
    creation_deadline: float | None
    parent_order: OrderIdVariant | None
    order_flags: OrderFlags | None

    def __init__(
        self,
        symbol: str,
        side: Side,
        quantity: float,
        max_fees_percent: float,
        price: float | None = None,
        trigger_price: float | None = None,
        twap_config: TWAPConfig | None = None,
        creation_deadline: float | None = None,
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
        self.quantity = quantity
        self.max_fees_percent = max_fees_percent
        self.price = price
        self.trigger_price = trigger_price
        self.trigger_price = trigger_price
        self.twap_config = twap_config
        self.creation_deadline = creation_deadline
        self.parent_order = parent_order
        self.order_flags = order_flags
        self.trigger_direction = trigger_direction


class UpdateOrder:
    action: str = "modify"
    order_id: int
    # needed for creating the signature
    symbol: str
    # needed for creating the signature
    side: Side
    quantity: float
    max_fees_percent: float
    price: float | None
    trigger_price: float | None
    parent_order: OrderIdVariant | None
    order_flags: OrderFlags | None

    def __init__(
        self,
        order_id: int,
        symbol: str,
        side: Side,
        quantity: float,
        max_fees_percent: float,
        price: float | None = None,
        trigger_price: float | None = None,
        creation_deadline: float | None = None,
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
        self.quantity = quantity
        self.max_fees_percent = max_fees_percent
        self.price = price
        self.trigger_price = trigger_price
        self.creation_deadline = creation_deadline
        self.parent_order = parent_order
        self.order_flags = order_flags


class CancelOrder:
    action: str = "cancel"
    order_id: int | None
    nonce: int | None

    def __init__(self, order_id: int | None = None, nonce: int | None = None):
        self.order_id = order_id
        self.nonce = nonce
