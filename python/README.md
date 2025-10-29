# Hibachi Python SDK

The official Python SDK for interacting with the Hibachi cryptocurrency exchange API.

[Official API Docs](https://api-doc.hibachi.xyz/)

# Get Started with PyPI

```bash
pip install hibachi-xyz==<x.x.x>
python3 -m venv myapp
source myapp/bin/activate
```

Create `main.py`

```python
from hibachi_xyz import HibachiApiClient
from dotenv import load_dotenv
import os

load_dotenv()

hibachi = HibachiApiClient()
exchange_info = hibachi.get_exchange_info()
print(exchange_info)
```

## Authentication

Create a `.env` file and enter your values from hibachi. Please see [Authentication](https://api-doc.hibachi.xyz/#f1e55d83-5587-4c31-bff2-e972590a16ad) for more information. Before start running this SDK, you want to make 10 USDT deposit into the account you will be using below to ensure successful runs. 

```
ENVIRONMENT=production
HIBACHI_API_ENDPOINT_PRODUCTION="https://api.hibachi.xyz"
HIBACHI_DATA_API_ENDPOINT_PRODUCTION="https://data-api.hibachi.xyz"
HIBACHI_API_KEY_PRODUCTION="your_api_key_here"
HIBACHI_PRIVATE_KEY_PRODUCTION="your_private_key_here"
HIBACHI_PUBLIC_KEY_PRODUCTION="your_public_key_here"
HIBACHI_ACCOUNT_ID_PRODUCTION="your_account_id_here"
HIBACHI_TRANSFER_DST_ACCOUNT_PUBLIC_KEY_PRODUCTION="transfer_destination_account_public_key_here"
```

```python
# ensure .env has the values set.
from hibachi_xyz.env_setup import setup_environment
api_endpoint, data_api_endpoint, api_key, account_id, private_key, public_key, _ = setup_environment()

hibachi = HibachiApiClient(
        api_url= api_endpoint,
        data_api_url= data_api_endpoint,
        api_key = api_key,
        account_id = account_id,
        private_key = private_key,
    )

account_info = hibachi.get_account_info()
print(f"Account Balance: {account_info.balance}")
print(f"total Position Notional: {account_info.totalPositionNotional}")
```

Once you can see your account balance you can proceed with the below examples or specific documentation. Let us know if you need any help!

# Examples

See how to use the Python SDK from working code:

[REST Example - Trade and Account](https://github.com/hibachi-xyz/hibachi_sdk/blob/main/python/examples/example_rest_api.py)
[REST Example - Market](https://github.com/hibachi-xyz/hibachi_sdk/blob/main/python/examples/example_public_api.py)
[Websocket Examples - Trade](https://github.com/hibachi-xyz/hibachi_sdk/blob/main/python/examples/example_ws_trade.py)
[Websocket Examples - Account](https://github.com/hibachi-xyz/hibachi_sdk/blob/main/python/examples/example_ws_account.py)
[Websocket Examples - Market](https://github.com/hibachi-xyz/hibachi_sdk/blob/main/python/examples/example_ws_Market.py)

## Environment Variables

The SDK supports the following environment variables. You can create a `.env` file and update values. Keep your keys safe.

```sh
# Default API endpoint
HIBACHI_API_ENDPOINT_PRODUCTION="https://api.hibachi.xyz"
# Default data API endpoint
HIBACHI_DATA_API_ENDPOINT_PRODUCTION="https://data-api.hibachi.xyz"
# Your API key
HIBACHI_API_KEY_PRODUCTION=""
# Your account ID
HIBACHI_ACCOUNT_ID_PRODUCTION=""
# Your private key
HIBACHI_PRIVATE_KEY_PRODUCTION=""
```

# API Reference

| Method                   | API Endpoint                                                                            | Description                                                    |
|--------------------------|-----------------------------------------------------------------------------------------|----------------------------------------------------------------|
| [get_exchange_info](#api.HibachiApiClient.get_exchange_info)              | /market/exchange-info                  | Return Exchange information, contracts and maintenance status. |
| [get_inventory](#api.HibachiApiClient.get_inventory)                      | /market/inventory                      | Similar to exchange info, includes price data                  |
| [get_prices](#api.HibachiApiClient.get_prices)                            | /market/data/prices                    | Get the price and funding information for a future contract.   |
| [get_stats](#api.HibachiApiClient.get_stats)                              | /market/data/stats                     | Get 24h high/low/volume for a future contract.                 |
| [get_trades](#api.HibachiApiClient.get_trades)                            | /market/data/trades                    | Get recent trades from all users for one future contract.      |
| [get_klines](#api.HibachiApiClient.get_klines)                            | /market/data/klines                    | Get the candlesticks for a future contract.                    |
| [get_open_interest](#api.HibachiApiClient.get_open_interest)              | /market/data/open-interest             | Get the open interest for one future contract.                 |
| [get_orderbook](#api.HibachiApiClient.get_orderbook)                      | /market/data/orderbook                 | Get the orderbook price levels.                                |
| [get_capital_balance](#api.HibachiApiClient.get_capital_balance)          | /capital/balance                       | Get the balance of your account.                               | 
| [get_capital_history](#api.HibachiApiClient.get_capital_history)          | /capital/history                       | Get the deposit and withdraw history of your account.          |
| [withdraw](#api.HibachiApiClient.withdraw)                                | /capital/withdraw                      | Submit a withdraw request.                                     |  
| [transfer](#api.HibachiApiClient.transfer)                                | /capital/transfer                      | Submit a transfer request.                                     |
| [get_deposit_info](#api.HibachiApiClient.get_deposit_info)                | /capital/deposit-info                  | Get deposit address                                            |   
| [get_account_info](#api.HibachiApiClient.get_account_info)                | /trade/account/info                    | Get account information/details                                |
| [get_account_trades](#api.HibachiApiClient.get_account_trades)            | /trade/account/trades                  | Get the trades history of your account.                        |
| [get_settlements_history](#api.HibachiApiClient.get_settlements_history)  | /trade/account/settlements_history     | You can obtain the history of settled trades                   |
| [get_pending_orders](#api.HibachiApiClient.get_pending_orders)            | /trade/orders                          | Get the pending orders of your account.                        |
| [get_order_details](#api.HibachiApiClient.get_order_details)              | /trade/order                           | Get the details about your one particular order.               |
| [place_limit_order](#api.HibachiApiClient.place_limit_order)              | /trade/order                           | Submit a new limit order.                                      |
| [place_market_order](#api.HibachiApiClient.place_market_order)            | /trade/order                           | Submit a new market order.                                     |
| [batch_orders](#api.HibachiApiClient.batch_orders)                        | /trade/orders                          | Submit multiple order requests for an account. Place or Modify |
| [update_order](#api.HibachiApiClient.update_order)                        | /trade/order                           | Modify an existing order.                                      |
| [cancel_order](#api.HibachiApiClient.cancel_order)                        | /trade/order                           | Remove an existing order.                                      |
| [cancel_all_orders](#api.HibachiApiClient.cancel_all_orders)              | /trade/orders                          | Allows you to batch cancel all open orders for an account.     |

# Websocket API

[Market Websocket](#api_ws_market.HibachiWSMarketClient)
[Trade Websocket](#api_ws_trade.HibachiWSTradeClient)
[Account Websocket](#api_ws_account.HibachiWSAccountClient)
# Table of Contents

* [api](#api)
  * [HibachiApiClient](#api.HibachiApiClient)
    * [get\_exchange\_info](#api.HibachiApiClient.get_exchange_info)
    * [get\_inventory](#api.HibachiApiClient.get_inventory)
    * [get\_open\_interest](#api.HibachiApiClient.get_open_interest)
    * [get\_orderbook](#api.HibachiApiClient.get_orderbook)
    * [get\_capital\_balance](#api.HibachiApiClient.get_capital_balance)
    * [get\_capital\_history](#api.HibachiApiClient.get_capital_history)
    * [withdraw](#api.HibachiApiClient.withdraw)
    * [transfer](#api.HibachiApiClient.transfer)
    * [get\_deposit\_info](#api.HibachiApiClient.get_deposit_info)
    * [get\_account\_info](#api.HibachiApiClient.get_account_info)
    * [get\_account\_trades](#api.HibachiApiClient.get_account_trades)
    * [get\_settlements\_history](#api.HibachiApiClient.get_settlements_history)
    * [get\_pending\_orders](#api.HibachiApiClient.get_pending_orders)
    * [get\_order\_details](#api.HibachiApiClient.get_order_details)
    * [place\_market\_order](#api.HibachiApiClient.place_market_order)
    * [place\_limit\_order](#api.HibachiApiClient.place_limit_order)
    * [update\_order](#api.HibachiApiClient.update_order)
    * [cancel\_order](#api.HibachiApiClient.cancel_order)
    * [cancel\_all\_orders](#api.HibachiApiClient.cancel_all_orders)
    * [batch\_orders](#api.HibachiApiClient.batch_orders)
* [api\_ws\_account](#api_ws_account)
  * [HibachiWSAccountClient](#api_ws_account.HibachiWSAccountClient)
    * [connect](#api_ws_account.HibachiWSAccountClient.connect)
    * [stream\_start](#api_ws_account.HibachiWSAccountClient.stream_start)
    * [listen](#api_ws_account.HibachiWSAccountClient.listen)
    * [disconnect](#api_ws_account.HibachiWSAccountClient.disconnect)
* [api\_ws\_trade](#api_ws_trade)
  * [HibachiWSTradeClient](#api_ws_trade.HibachiWSTradeClient)
    * [connect](#api_ws_trade.HibachiWSTradeClient.connect)
    * [place\_order](#api_ws_trade.HibachiWSTradeClient.place_order)
    * [cancel\_order](#api_ws_trade.HibachiWSTradeClient.cancel_order)
    * [modify\_order](#api_ws_trade.HibachiWSTradeClient.modify_order)
    * [get\_order\_status](#api_ws_trade.HibachiWSTradeClient.get_order_status)
    * [get\_orders\_status](#api_ws_trade.HibachiWSTradeClient.get_orders_status)
    * [cancel\_all\_orders](#api_ws_trade.HibachiWSTradeClient.cancel_all_orders)
    * [batch\_orders](#api_ws_trade.HibachiWSTradeClient.batch_orders)
    * [enable\_cancel\_on\_disconnect](#api_ws_trade.HibachiWSTradeClient.enable_cancel_on_disconnect)
    * [disconnect](#api_ws_trade.HibachiWSTradeClient.disconnect)
* [api\_ws\_market](#api_ws_market)
  * [HibachiWSMarketClient](#api_ws_market.HibachiWSMarketClient)
    * [connect](#api_ws_market.HibachiWSMarketClient.connect)
    * [subscribe](#api_ws_market.HibachiWSMarketClient.subscribe)
    * [unsubscribe](#api_ws_market.HibachiWSMarketClient.unsubscribe)

<a id="api.HibachiApiClient"></a>

## HibachiApiClient Objects

```python
class HibachiApiClient()
```

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

**Arguments**:

- `api_url` - The base URL of the API
- `data_api_url` - The base URL of the data API
- `account_id` - The account ID
- `api_key` - The API key
- `private_key` - The private key for the account

<a id="api.HibachiApiClient.get_exchange_info"></a>

#### get\_exchange\_info

```python
def get_exchange_info() -> ExchangeInfo
```

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

<a id="api.HibachiApiClient.get_inventory"></a>

#### get\_inventory

```python
def get_inventory() -> InventoryResponse
```

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
            marketCloseTimestamp: Optional[str]
            marketOpenTimestamp: Optional[str]
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

<a id="api.HibachiApiClient.get_open_interest"></a>

#### get\_open\_interest

```python
def get_open_interest(symbol: str) -> OpenInterestResponse
```

Get open interest for a symbol

Endpoint: `GET /market/data/open-interest`

**Arguments**:

- `symbol` - The trading symbol (e.g. "BTC/USDT-P")
  

**Returns**:

- `OpenInterestResponse` - The open interest data
  
  -----------------------------------------------------------------------

<a id="api.HibachiApiClient.get_orderbook"></a>

#### get\_orderbook

```python
def get_orderbook(symbol: str, depth: int, granularity: float) -> OrderBook
```

Get the orderbook price levels.
It will return up to depth price levels on both side. The price level will be aggregated based on granularity.

Endpoint: `GET /market/data/orderbook`

**Arguments**:

- `symbol` - The trading symbol (e.g. "BTC/USDT-P")
- `depth` - The number of price levels to return on each side
- `granularity` - The price level granularity (e.g. 0.01)
  
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

<a id="api.HibachiApiClient.get_capital_balance"></a>

#### get\_capital\_balance

```python
def get_capital_balance() -> CapitalBalance
```

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

<a id="api.HibachiApiClient.get_capital_history"></a>

#### get\_capital\_history

```python
def get_capital_history() -> CapitalHistory
```

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
    timestamp: int
    token: Optional[str]
    transactionHash: Union[str,str]
    transactionType: str
}

CapitalHistory {
    transactions: List[Transaction]
}
```
-----------------------------------------------------------------------

<a id="api.HibachiApiClient.withdraw"></a>

#### withdraw

```python
def withdraw(coin: str,
             withdraw_address: str,
             quantity: str,
             max_fees: str,
             network: str = "arbitrum") -> WithdrawResponse
```

Submit a withdraw request.

Endpoint: `POST /capital/withdraw`

**Arguments**:

- `coin` - The coin to withdraw (e.g. "USDT")
- `withdraw_address` - The address to withdraw to
- `quantity` - The amount to withdraw should be no more than maximalWithdraw returned by /trade/account/info endpoint, otherwise it will be rejected.
- `max_fees` - Maximum fees allowed for the withdrawal
- `network` - The network to withdraw on (default "arbitrum")
  

**Returns**:

- `WithdrawResponse` - The response containing the order ID
  
  -----------------------------------------------------------------------

<a id="api.HibachiApiClient.transfer"></a>

#### transfer

```python
def transfer(coin: str, quantity: str, dstPublicKey: str, max_fees: str)
```

Request fund transfer to another account.

Endpoint: `POST /capital/transfer`

**Arguments**:

- `coin` - The coin to transfer
- `fees` - The fees to transfer
- `quantity` - The quantity to transfer

<a id="api.HibachiApiClient.get_deposit_info"></a>

#### get\_deposit\_info

```python
def get_deposit_info(public_key: str) -> DepositInfo
```

Get deposit address information.

Endpoint: `GET /capital/deposit-info`

**Arguments**:

- `public_key` - The public key to get deposit info for
  

**Returns**:

- `DepositInfo` - The deposit address information
  
```python
DepositInfo { depositAddressEvm: str }
``` 
  -----------------------------------------------------------------------

<a id="api.HibachiApiClient.get_account_info"></a>

#### get\_account\_info

```python
def get_account_info() -> AccountInfo
```

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

<a id="api.HibachiApiClient.get_account_trades"></a>

#### get\_account\_trades

```python
def get_account_trades() -> AccountTradesResponse
```

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

<a id="api.HibachiApiClient.get_settlements_history"></a>

#### get\_settlements\_history

```python
def get_settlements_history() -> SettlementsResponse
```

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

<a id="api.HibachiApiClient.get_pending_orders"></a>

#### get\_pending\_orders

```python
def get_pending_orders() -> PendingOrdersResponse
```

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

<a id="api.HibachiApiClient.get_order_details"></a>

#### get\_order\_details

```python
def get_order_details(order_id: Optional[int] = None,
                      nonce: Optional[int] = None) -> Order
```

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

<a id="api.HibachiApiClient.place_market_order"></a>

#### place\_market\_order

```python
def place_market_order(
        symbol: str,
        quantity: float,
        side: Side,
        max_fees_percent: float,
        trigger_price: Optional[float] = None,
        twap_config: Optional[TWAPConfig] = None,
        creation_deadline: Optional[int] = None) -> tuple[Nonce, OrderId]
```

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

<a id="api.HibachiApiClient.place_limit_order"></a>

#### place\_limit\_order

```python
def place_limit_order(
        symbol: str,
        quantity: float,
        price: float,
        side: Side,
        max_fees_percent: float,
        trigger_price: Optional[float] = None,
        creation_deadline: Optional[int] = None) -> tuple[Nonce, OrderId]
```

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

<a id="api.HibachiApiClient.update_order"></a>

#### update\_order

```python
def update_order(order_id: int,
                 max_fees_percent: float,
                 quantity: Optional[float] = None,
                 price: Optional[float] = None,
                 trigger_price: Optional[float] = None,
                 creation_deadline: Optional[int] = None) -> Dict[str, Any]
```

Update an order

Endpoint: `PUT /trade/order`

```python
max_fees_percent = 0.0005   
client.update_order(order_id, max_fees_percent, quantity=0.002)
client.update_order(order_id, max_fees_percent, price=1_050_000)
client.update_order(order_id, max_fees_percent, trigger_price=1_100_000)
client.update_order(order_id, max_fees_percent, quantity=0.001, price=1_210_000, trigger_price=1_250_000)
```

<a id="api.HibachiApiClient.cancel_order"></a>

#### cancel\_order

```python
def cancel_order(order_id: Optional[int] = None,
                 nonce: Optional[int] = None) -> Dict[str, Any]
```

Cancel an order

Endpoint: `DELETE /trade/order`

```python
client.cancel_order(order_id=123)
client.cancel_order(nonce=1234567)
```

<a id="api.HibachiApiClient.cancel_all_orders"></a>

#### cancel\_all\_orders

```python
def cancel_all_orders(contractId: Optional[int] = None) -> Dict[str, Any]
```

Cancel all orders

Endpoint: `DELETE /trade/orders`


Note: currently there is a bug in the API where cancelling all orders is not working.
This is a workaround to cancel all orders.
```python
client.cancel_all_orders()
```

<a id="api.HibachiApiClient.batch_orders"></a>

#### batch\_orders

```python
def batch_orders(
        orders: list[CreateOrder | UpdateOrder | CancelOrder]
) -> Dict[str, Any]
```

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

<a id="api_ws_account.HibachiWSAccountClient"></a>

## HibachiWSAccountClient Objects

```python
class HibachiWSAccountClient()
```

Account Websocket Client is used to subscribe to account balance and positions.

```python
import asyncio
import os
import time
from datetime import datetime, timezone

from hibachi_xyz import HibachiWSAccountClient, print_data
from hibachi_xyz.env_setup import setup_environment


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

async def example_ws_account():
    print("Loading environment variables from .env file")
    api_endpoint, _, api_key, account_id, _, _, _ = setup_environment()
    ws_base_url = api_endpoint.replace("https://", "wss://")

    attempt = 1
    backoff = 1  # seconds

    while True:
        print(f"[{now()}] [Attempt {attempt}] Connecting to WebSocket...")
        myaccount_live = HibachiWSAccountClient(
            api_endpoint=ws_base_url,
            api_key=api_key,
            account_id=account_id
        )

        start_time = time.time()
        try:
            await myaccount_live.connect()
            result_start = await myaccount_live.stream_start()
            print(f"[Connected] stream_start result:")
            print_data(result_start)

            print("Listening for account WebSocket messages (Ctrl+C to stop)...")
            last_msg_time = time.time()

            while True:
                message = await myaccount_live.listen()
                if message is None:
                    print(f"[{now()}] No message received. (Ping sent.) "
                          f"Last message was {int(time.time() - last_msg_time)}s ago.")
                    continue
                last_msg_time = time.time()
                print_data(message)

        except asyncio.CancelledError:
            print(f"[{now()}] CancelledError caught. Cleaning up WebSocket connection.")
            await myaccount_live.disconnect()
            break

        except Exception as e:
            print(f"[Error] {e}")

        finally:
            duration = time.time() - start_time
            print(f"[{now()}] Disconnected. Connection lasted {duration:.2f} seconds.")
            await myaccount_live.disconnect()
            print(f"[{now()}] Client cleaned up.")

        print(f"Reconnecting in {backoff} seconds...\n")
        try:
            await asyncio.sleep(backoff)
        except asyncio.CancelledError:
            print(f"[{now()}] Cancelled during backoff sleep. Exiting.")
            break

        attempt += 1
        backoff = min(backoff * 2, 60)

if __name__ == "__main__":
    try:
        asyncio.run(example_ws_account())
    except KeyboardInterrupt:
        print(f"[{now()}] KeyboardInterrupt received. Exiting cleanly.")

```

<a id="api_ws_account.HibachiWSAccountClient.connect"></a>

#### connect

```python
async def connect(self):
        self.websocket = await connect_with_retry(
            web_url=self.api_endpoint + f"/ws/account?accountId={self.account_id}",
            headers=[("Authorization", self.api_key)]
        )

```


<a id="api_ws_account.HibachiWSAccountClient.stream_start"></a>

#### stream\_start

```python
async def stream_start() -> AccountStreamStartResult
```

Get account information including assets, positions, and balances

<a id="api_ws_account.HibachiWSAccountClient.listen"></a>

#### listen

```python
async def listen(self) -> Optional[dict]
```

Listen for messages with a 5-second timeout that triggers a ping

<a id="api_ws_account.HibachiWSAccountClient.disconnect"></a>

#### disconnect

```python
async def disconnect()
```

Close the WebSocket connection

<a id="api_ws_trade.HibachiWSTradeClient"></a>

## HibachiWSTradeClient Objects

```python
class HibachiWSTradeClient()
```

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

<a id="api_ws_trade.HibachiWSTradeClient.connect"></a>

#### connect

```python
async def connect()
```

Establish WebSocket connection with retry logic

<a id="api_ws_trade.HibachiWSTradeClient.place_order"></a>

#### place\_order

```python
async def place_order(params: OrderPlaceParams) -> tuple[Nonce, int]
```

Place a new order

<a id="api_ws_trade.HibachiWSTradeClient.cancel_order"></a>

#### cancel\_order

```python
async def cancel_order(orderId: int, nonce: int) -> WebSocketResponse
```

Cancel an existing order

<a id="api_ws_trade.HibachiWSTradeClient.modify_order"></a>

#### modify\_order

```python
async def modify_order(order: Order,
                       quantity: float,
                       price: str,
                       side: websockets.Side,
                       maxFeesPercent: float,
                       nonce: Optional[Nonce] = None) -> WebSocketResponse
```

Modify an existing order

<a id="api_ws_trade.HibachiWSTradeClient.get_order_status"></a>

#### get\_order\_status

```python
async def get_order_status(orderId: int) -> OrderStatusResponse
```

Get status of a specific order

<a id="api_ws_trade.HibachiWSTradeClient.get_orders_status"></a>

#### get\_orders\_status

```python
async def get_orders_status() -> OrdersStatusResponse
```

Get status of all orders

<a id="api_ws_trade.HibachiWSTradeClient.cancel_all_orders"></a>

#### cancel\_all\_orders

```python
async def cancel_all_orders() -> bool
```

Cancel all orders

<a id="api_ws_trade.HibachiWSTradeClient.batch_orders"></a>

#### batch\_orders

```python
async def batch_orders(params: OrdersBatchParams) -> WebSocketResponse
```

Execute multiple order operations in a single request

<a id="api_ws_trade.HibachiWSTradeClient.enable_cancel_on_disconnect"></a>

#### enable\_cancel\_on\_disconnect

```python
async def enable_cancel_on_disconnect(
        params: EnableCancelOnDisconnectParams) -> WebSocketResponse
```

Enable automatic order cancellation on WebSocket disconnect

<a id="api_ws_trade.HibachiWSTradeClient.disconnect"></a>

#### disconnect

```python
async def disconnect()
```

Close the WebSocket connection

<a id="api_ws_market.HibachiWSMarketClient"></a>

## HibachiWSMarketClient Objects

```python
class HibachiWSMarketClient()
```

Market Websocket Client is used to subscribe to market data like mark price, spot price, funding rate, trades, candle sticks, orderbook, ask/bid prices.

## Example usage:

```python
import asyncio

from hibachi_xyz import (HibachiWSMarketClient, WebSocketSubscription,
                         print_data)


async def example_ws_market():
    client = HibachiWSMarketClient()
    await client.connect()

    subscriptions = [
        WebSocketSubscription(symbol="BTC/USDT-P", topic="mark_price"),
        WebSocketSubscription(symbol="BTC/USDT-P", topic="trades"),
    ]

    # Async handlers for message topics
    async def handle_mark_price(msg):
        print("[Mark Price]", msg)

    async def handle_trades(msg):
        print("[Trades]", msg)

    client.on("mark_price", handle_mark_price)
    client.on("trades", handle_trades)

    await client.subscribe(subscriptions)
    print("Subscribed. Press Ctrl+C to exit.\n")

    try:
        # Wait forever (or until Ctrl+C)
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n[Shutdown] Ctrl+C detected.")
    finally:
        print("[Cleanup] Unsubscribing and disconnecting...")
        await client.unsubscribe(subscriptions)
        await client.disconnect()
        print("[Done] Gracefully exited.")

if __name__ == "__main__":
    import sys
    try:
        asyncio.run(example_ws_market())
    except KeyboardInterrupt:
        # Suppress ugly stack trace on Ctrl+C
        print("\n[Exit] Keyboard interrupt received. Shutting down cleanly.")
        sys.exit(0)

```

<a id="api_ws_market.HibachiWSMarketClient.connect"></a>

#### connect

```python
async def connect(self):
        self.websocket = await connect_with_retry(self.api_endpoint)
        self._receive_task = asyncio.create_task(self._receive_loop())
        return self
```

<a id="api_ws_market.HibachiWSMarketClient.subscribe"></a>

#### subscribe

```python
async def subscribe(self, subscriptions: List[WebSocketSubscription]):
        message = {
            "method": "subscribe",
            "parameters": {
                "subscriptions": [
                    {**asdict(sub), "topic": sub.topic} for sub in subscriptions
                ]
            }
        }
        await self.websocket.send(json.dumps(message))

```
<a id="api_ws_market.HibachiWSMarketClient.unsubscribe"></a>

#### unsubscribe

```python
async def unsubscribe(self, subscriptions: List[WebSocketSubscription]):
        message = {
            "method": "unsubscribe",
            "parameters": {
                "subscriptions": [
                    {**asdict(sub), "topic": sub.topic} for sub in subscriptions
                ]
            }
        }
        await self.websocket.send(json.dumps(message))

```

Unsubscribe from specific market subscriptions


# Development

```sh
cd hibachi_sdk
python3 -m venv python

# Run tests
./bin/pytest -v -s
```

## Generate Docs

Docs are auto generated using https://niklasrosenstein.github.io/pydoc-markdown/

Update `doc_header.md` and `doc_footer.md`

```sh
./bin/python docs.py
# updates README.md
```