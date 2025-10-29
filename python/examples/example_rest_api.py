"""
Authenticated REST API Example

This example demonstrates how to use Hibachi's authenticated REST API endpoints.
These endpoints require valid API credentials and allow you to:

Account Information:
- Get account info (balances, positions, PnL)
- Get account trade history
- Get settlements (funding payments)
- Get pending orders
- Get capital balance and history

Trading Operations:
- Place market orders
- Place limit orders
- Place trigger orders (stop-loss, take-profit)
- Update existing orders
- Cancel orders (single, batch, all)
- Batch order operations (create, update, cancel in one request)

Advanced Features:
- TWAP (Time-Weighted Average Price) orders
- Order deadlines (time-limited orders)
- Withdrawals (commented out for safety)

Environment Variables Required:
- HIBACHI_API_ENDPOINT: API endpoint URL
- HIBACHI_DATA_API_ENDPOINT: Data API endpoint URL
- HIBACHI_API_KEY: Your API key
- HIBACHI_ACCOUNT_ID: Your account ID
- HIBACHI_PRIVATE_KEY: Your private key for signing
"""

from hibachi_xyz import (
    CancelOrder,
    CreateOrder,
    HibachiApiClient,
    TWAPConfig,
    TWAPQuantityMode,
    UpdateOrder,
)
from hibachi_xyz.env_setup import setup_environment
from hibachi_xyz.types import (
    CancelOrderBatchResponse,
    CreateOrderBatchResponse,
    ErrorBatchResponse,
    Side,
    UpdateOrderBatchResponse,
)


def example_auth_rest_api() -> None:
    """Demonstrate authenticated REST API endpoints for trading and account management."""

    print("=" * 70)
    print("Hibachi Authenticated REST API Example")
    print("=" * 70)

    # Load environment variables from .env file
    print("\n[Setup] Loading credentials from environment...")
    api_endpoint, data_api_endpoint, api_key, account_id, private_key, _, _ = (
        setup_environment()
    )
    print(f"[Setup] Account ID: {account_id}")
    print(f"[Setup] API Endpoint: {api_endpoint}\n")

    # Initialize authenticated client
    print("[Setup] Initializing authenticated API client...")
    hibachi = HibachiApiClient(
        api_url=api_endpoint,
        data_api_url=data_api_endpoint,
        api_key=api_key,
        account_id=account_id,
        private_key=private_key,
    )
    print("[Setup] Client initialized successfully!\n")

    # ==================================================================
    # PART 1: ACCOUNT INFORMATION
    # ==================================================================
    print("=" * 70)
    print("PART 1: ACCOUNT INFORMATION")
    print("=" * 70)

    # Get Account Info - includes balances, positions, and PnL
    print("\n[1.1] Fetching Account Info...")
    account_info = hibachi.get_account_info()

    print("\n[Account Summary]")
    print(f"  Total Balance:           ${account_info.balance}")
    print(f"  Max Withdrawable:        ${account_info.maximalWithdraw}")
    print(f"  Total Position Notional: ${account_info.totalPositionNotional}")
    print(f"  Total Order Notional:    ${account_info.totalOrderNotional}")
    print(f"  Unrealized PnL:          ${account_info.totalUnrealizedPnl}")
    print(f"  Trading PnL:             ${account_info.totalUnrealizedTradingPnl}")
    print(f"  Funding PnL:             ${account_info.totalUnrealizedFundingPnl}")
    print(f"  Free Transfers Left:     {account_info.numFreeTransfersRemaining}")

    print(f"\n[Assets] {len(account_info.assets)} asset(s)")
    for asset in account_info.assets:
        print(f"  {asset.symbol}: {asset.quantity}")

    print(f"\n[Positions] {len(account_info.positions)} open position(s)")
    for position in account_info.positions:
        print(f"  {position.symbol} {position.direction}")
        print(f"  Quantity: {position.quantity}")
        print(f"  Entry Price: ${position.openPrice}")
        print(f"  Mark Price: ${position.markPrice}")
        print(f"  Unrealized PnL: ${position.unrealizedTradingPnl}")

    # Get Account Trade History
    print("\n[1.2] Fetching Account Trade History...")
    trades_response = hibachi.get_account_trades()

    print(f"\n[Trade History] {len(trades_response.trades)} recent trade(s)")
    for i, trade in enumerate(trades_response.trades[:5], 1):  # Show first 5
        print(f"  {i}. {trade.symbol} - {trade.side} {trade.orderType}")
        print(f"     Price: ${trade.price}, Quantity: {trade.quantity}")
        print(f"     Fee: ${trade.fee}, Realized PnL: ${trade.realizedPnl}")
        print(f"     Trade ID: {trade.id}")

    # Get Settlements History - funding payment records for perpetual positions
    print("\n[1.3] Fetching Settlements History...")
    settlements_response = hibachi.get_settlements_history()

    print(f"\n[Settlements] {len(settlements_response.settlements)} funding payment(s)")
    for i, settlement in enumerate(
        settlements_response.settlements[:5], 1
    ):  # Show first 5
        print(f"  {i}. {settlement.symbol} - {settlement.direction}")
        print(f"     Settled Amount: ${settlement.settledAmount}")
        print(f"     Index Price: ${settlement.indexPrice}")
        print(f"     Quantity: {settlement.quantity}")
        print(f"     Timestamp: {settlement.timestamp}")

    # Get Pending Orders - all active orders (placed but not filled/cancelled)
    print("\n[1.4] Fetching Pending Orders...")
    pending_orders_response = hibachi.get_pending_orders()

    print(f"\n[Pending Orders] {len(pending_orders_response.orders)} active order(s)")
    for i, order in enumerate(pending_orders_response.orders[:5], 1):  # Show first 5
        print(f"  {i}. {order.symbol} - {order.orderType.value} {order.side.value}")
        print(f"     Order ID: {order.orderId}")
        print(f"     Status: {order.status.value}")
        print(f"     Price: ${order.price}")
        print(f"     Total Quantity: {order.totalQuantity}")
        print(f"     Available: {order.availableQuantity}")
        if order.triggerPrice:
            print(f"     Trigger Price: ${order.triggerPrice}")

    # Get Capital Balance - total available capital in the account
    print("\n[1.5] Fetching Capital Balance...")
    capital_balance = hibachi.get_capital_balance()

    print("\n[Capital Balance]")
    print(f"  Total Balance: ${capital_balance.balance}")

    # Get Capital History - transaction history (deposits, withdrawals, transfers)
    print("\n[1.6] Fetching Capital History...")
    history = hibachi.get_capital_history()

    print(f"\n[Capital History] {len(history.transactions)} transaction(s)")
    for i, txn in enumerate(history.transactions[:5], 1):  # Show first 5
        print(f"  {i}. {txn.transactionType} - {txn.status}")
        print(f"     Transaction ID: {txn.id}")
        print(f"     Quantity: {txn.quantity}")
        print(f"     Asset ID: {txn.assetId}")
        print(f"     Timestamp: {txn.timestampSec}")
        if txn.receivingAccountId:
            print(f"     Receiving Account: {txn.receivingAccountId}")
        if txn.transactionHash:
            print(f"     Tx Hash: {txn.transactionHash}")

    # ==================================================================
    # PART 2: BASIC TRADING OPERATIONS
    # ==================================================================
    print("\n" + "=" * 70)
    print("PART 2: BASIC TRADING OPERATIONS")
    print("=" * 70)

    # Fetch exchange information and current prices for trading
    print("\n[2.1] Fetching Exchange Info and Market Prices...")
    exch_info = hibachi.get_exchange_info()
    prices = hibachi.get_prices("BTC/USDT-P")

    print("\n[Market Data]")
    print(f"  Mark Price:   ${prices.markPrice}")
    print(f"  Spot Price:   ${prices.spotPrice}")
    print(f"  Bid Price:    ${prices.bidPrice}")
    print(f"  Ask Price:    ${prices.askPrice}")
    print(f"  Taker Fee:    {float(exch_info.feeConfig.tradeTakerFeeRate) * 100:.4f}%")

    # Place a Market Order - executes immediately at best available price
    print("\n[2.2] Placing Market Order (BUY)...")
    (nonce, order_id) = hibachi.place_market_order(
        symbol="BTC/USDT-P",
        quantity=0.0001,
        side=Side.BUY,
        max_fees_percent=float(exch_info.feeConfig.tradeTakerFeeRate) * 2.0,
    )

    print("\n[Market Order Placed]")
    print(f"  Order ID: {order_id}")
    print(f"  Nonce:    {nonce}")
    print("  Side:     BUY")
    print("  Quantity: 0.0001 BTC")

    # Place a Limit Order with Trigger (stop-loss/take-profit)
    print("\n[2.3] Placing Limit Order with Trigger...")
    (nonce, order_id) = hibachi.place_limit_order(
        symbol="BTC/USDT-P",
        quantity=0.0001,
        price=float(prices.markPrice),
        side=Side.BID,
        max_fees_percent=float(exch_info.feeConfig.tradeTakerFeeRate) * 2.0,
        trigger_price=float(prices.markPrice) * 0.95,
    )

    print("\n[Trigger Limit Order Placed]")
    print(f"  Order ID:      {order_id}")
    print(f"  Nonce:         {nonce}")
    print(f"  Limit Price:   ${float(prices.markPrice):.2f}")
    print(f"  Trigger Price: ${float(prices.markPrice) * 0.95:.2f}")

    # Get Order Details - check status and parameters of an order
    print("\n[2.4] Fetching Order Details...")
    order_details = hibachi.get_order_details(order_id=order_id)

    print("\n[Order Details]")
    print(f"  Symbol:        {order_details.symbol}")
    print(f"  Status:        {order_details.status.value}")
    print(f"  Order Type:    {order_details.orderType.value}")
    print(f"  Side:          {order_details.side.value}")
    print(f"  Price:         ${order_details.price}")
    print(f"  Total Qty:     {order_details.totalQuantity}")
    if order_details.triggerPrice:
        print(f"  Trigger Price: ${order_details.triggerPrice}")

    # Cancel a Specific Order - using order_id or nonce
    print("\n[2.5] Cancelling Order...")
    hibachi.cancel_order(order_id=order_id, nonce=nonce)
    print(f"  Order {order_id} cancelled successfully")

    # Cancel All Orders - clears all pending orders for the account
    print("\n[2.6] Cancelling All Orders...")
    hibachi.cancel_all_orders()
    print("  All pending orders cancelled")

    # ==================================================================
    # PART 3: BATCH OPERATIONS SETUP
    # ==================================================================
    print("\n" + "=" * 70)
    print("PART 3: BATCH OPERATIONS SETUP")
    print("=" * 70)

    # Prepare for batch operations - get fresh market data and fee rates
    print("\n[3.1] Preparing for Batch Operations...")
    exch_info = hibachi.get_exchange_info()
    prices = hibachi.get_prices("BTC/USDT-P")
    max_fees_percent = float(exch_info.feeConfig.tradeTakerFeeRate) * 2.0

    print("\n[Preparation]")
    print(f"  Max Fees Percent: {max_fees_percent * 100:.4f}%")
    print(f"  Current Ask:      ${prices.askPrice}")
    print(f"  Current Bid:      ${prices.bidPrice}")

    # Clear any existing orders before batch demo
    print("\n[3.2] Clearing Existing Orders...")
    hibachi.cancel_all_orders()
    print("  All orders cancelled")

    # Create a position to work with for batch operations
    print("\n[3.3] Creating Test Position...")
    (nonce, order_id) = hibachi.place_market_order(
        "BTC/USDT-P", quantity=0.005, side=Side.BUY, max_fees_percent=max_fees_percent
    )

    print("\n[Test Position Created]")
    print(f"  Order ID: {order_id}")
    print(f"  Nonce:    {nonce}")
    print("  Quantity: 0.005 BTC (BUY)")

    # Verify we have sufficient position for batch operations
    print("\n[3.4] Verifying Position...")
    account_info = hibachi.get_account_info()

    check = False
    for position in account_info.positions:
        if position.symbol == "BTC/USDT-P":
            print(f"  {position.symbol}: {position.quantity} {position.direction}")
            if float(position.quantity) > 0:
                check = True

    assert check, "Not enough BTC/USDT-P position to sell"
    print("  Position verified successfully")

    # Place test orders that will be updated/cancelled in batch
    print("\n[3.5] Placing Test Orders for Batch Operations...")

    # Limit order below market
    (nonce, limit_order_id) = hibachi.place_limit_order(
        symbol="BTC/USDT-P",
        quantity=0.001,
        price=float(prices.bidPrice) * 0.975,
        side=Side.BID,
        max_fees_percent=max_fees_percent,
    )
    print(
        f"  [a] Limit Order: {limit_order_id} @ ${float(prices.bidPrice) * 0.975:.2f}"
    )

    # Trigger limit order above market
    (nonce, trigger_limit_order_id) = hibachi.place_limit_order(
        symbol="BTC/USDT-P",
        quantity=0.001,
        price=float(prices.askPrice) * 1.05,
        side=Side.ASK,
        max_fees_percent=max_fees_percent,
        trigger_price=float(prices.askPrice) * 1.025,
    )
    print(
        f"  [b] Trigger Limit: {trigger_limit_order_id} @ ${float(prices.askPrice) * 1.05:.2f}"
    )
    print(f"      Triggers at: ${float(prices.askPrice) * 1.025:.2f}")

    # Trigger market order
    (nonce, trigger_market_order_id) = hibachi.place_market_order(
        symbol="BTC/USDT-P",
        quantity=0.001,
        side=Side.ASK,
        max_fees_percent=max_fees_percent,
        trigger_price=float(prices.askPrice) * 1.025,
    )
    print(f"  [c] Trigger Market: {trigger_market_order_id}")
    print(f"      Triggers at: ${float(prices.askPrice) * 1.025:.2f}")

    # ==================================================================
    # PART 4: BATCH OPERATIONS EXECUTION
    # ==================================================================
    print("\n" + "=" * 70)
    print("PART 4: BATCH OPERATIONS EXECUTION")
    print("=" * 70)

    # Execute multiple order operations in a single batch request
    # This is more efficient than individual requests and ensures atomic execution
    print("\n[4.1] Executing Batch Order Operations...")
    print("  This batch includes: creates, updates, cancels, TWAP, and deadlines")

    response = hibachi.batch_orders(
        [
            # CREATE OPERATIONS - Various order types
            CreateOrder("BTC/USDT-P", Side.SELL, 0.001, max_fees_percent),
            CreateOrder(
                "BTC/USDT-P",
                Side.SELL,
                0.001,
                max_fees_percent,
                price=float(prices.spotPrice),
            ),
            CreateOrder(
                "BTC/USDT-P",
                Side.SELL,
                0.001,
                max_fees_percent,
                trigger_price=float(prices.spotPrice),
            ),
            CreateOrder(
                "BTC/USDT-P",
                Side.SELL,
                0.001,
                max_fees_percent,
                price=float(prices.askPrice),
                trigger_price=float(prices.askPrice) * 1.05,
            ),
            # TWAP order - splits order over time
            CreateOrder(
                "BTC/USDT-P",
                Side.SELL,
                0.001,
                max_fees_percent,
                twap_config=TWAPConfig(5, TWAPQuantityMode.FIXED),
            ),
            # DEADLINE ORDERS - Time-limited order placement
            CreateOrder(
                "BTC/USDT-P", Side.BUY, 0.001, max_fees_percent, creation_deadline=2
            ),
            CreateOrder(
                "BTC/USDT-P",
                Side.BUY,
                0.001,
                max_fees_percent,
                price=float(prices.spotPrice),
                creation_deadline=1,
            ),
            CreateOrder(
                "BTC/USDT-P",
                Side.BUY,
                0.001,
                max_fees_percent,
                trigger_price=float(prices.askPrice),
                creation_deadline=3,
            ),
            CreateOrder(
                "BTC/USDT-P",
                Side.BUY,
                0.001,
                max_fees_percent,
                price=float(prices.askPrice),
                trigger_price=float(prices.askPrice),
                creation_deadline=5,
            ),
            CreateOrder(
                "BTC/USDT-P",
                Side.SELL,
                0.001,
                max_fees_percent,
                twap_config=TWAPConfig(5, TWAPQuantityMode.FIXED),
            ),
            # UPDATE OPERATIONS - Modify existing orders
            UpdateOrder(
                limit_order_id,
                "BTC/USDT-P",
                Side.BUY,
                0.001,
                max_fees_percent,
                price=float(prices.askPrice),
            ),
            # Update trigger limit order
            UpdateOrder(
                trigger_limit_order_id,
                "BTC/USDT-P",
                Side.ASK,
                0.002,
                max_fees_percent,
                price=float(prices.askPrice),
                trigger_price=float(prices.askPrice),
            ),
            # Update trigger market order
            UpdateOrder(
                trigger_market_order_id,
                "BTC/USDT-P",
                Side.ASK,
                0.001,
                max_fees_percent,
                trigger_price=float(prices.askPrice),
            ),
            # CANCEL OPERATIONS - Remove orders from book
            CancelOrder(order_id=limit_order_id),
            CancelOrder(nonce=nonce),
        ]
    )

    # Process and validate batch response
    print("\n[4.2] Processing Batch Response...")

    create_count = 0
    update_count = 0
    cancel_count = 0
    error_count = 0

    for batch_order in response.orders:
        if isinstance(batch_order, CreateOrderBatchResponse):
            assert batch_order.orderId is not None
            assert batch_order.nonce is not None
            assert batch_order.creationTime is not None
            assert batch_order.creationTimeNsPartial
            create_count += 1
        elif isinstance(batch_order, UpdateOrderBatchResponse):
            assert batch_order.orderId is not None
            update_count += 1
        elif isinstance(batch_order, CancelOrderBatchResponse):
            assert batch_order.nonce is not None
            cancel_count += 1
        else:
            assert isinstance(batch_order, ErrorBatchResponse)
            error_count += 1

    print("\n[Batch Results]")
    print(f"  Created:  {create_count} order(s)")
    print(f"  Updated:  {update_count} order(s)")
    print(f"  Cancelled: {cancel_count} order(s)")
    print(f"  Errors:   {error_count} error(s)")
    print(f"  Total:    {len(response.orders)} operation(s)")

    # ==================================================================
    # PART 5: WITHDRAWALS (DISABLED FOR SAFETY)
    # ==================================================================
    print("\n" + "=" * 70)
    print("PART 5: WITHDRAWALS (DISABLED FOR SAFETY)")
    print("=" * 70)

    # Withdrawal functionality is commented out by default to prevent
    # accidental fund transfers during example execution
    print("\n[5.1] Withdrawal Demo (Commented Out)")
    print("  To enable withdrawals, uncomment the code below:")
    print("  - Set your withdrawal address")
    print("  - Set the coin type (e.g., USDT)")
    print("  - Set the quantity to withdraw")
    print("  - Ensure max_fees covers the withdrawal fee")
    print("\n  WARNING: Withdrawals are irreversible!")

    # UNCOMMENT AND CONFIGURE THE FOLLOWING TO TEST WITHDRAWALS:
    # --------------------------------------------------------------------
    # withdrawal_fees = exch_info.feeConfig.withdrawalFees
    # response = hibachi.withdraw(
    #     coin="USDT",
    #     withdraw_address="0x0000000000000000000000000000000000000000",
    #     quantity="1.0",
    #     max_fees=withdrawal_fees
    # )
    # print(f"\n[Withdrawal Submitted]")
    # print(f"  Coin:    {response.coin}")
    # print(f"  Amount:  {response.quantity}")
    # print(f"  Address: {response.withdraw_address}")
    # print(f"  Status:  {response.status}")
    # --------------------------------------------------------------------

    # Example complete
    print("\n" + "=" * 70)
    print("EXAMPLE COMPLETE")
    print("=" * 70)
    print("\nAll operations completed successfully!")
    print("Check the output above for detailed results from each operation.\n")


if __name__ == "__main__":
    # This code only runs when the file is executed directly
    example_auth_rest_api()
