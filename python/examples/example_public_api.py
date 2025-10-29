"""
Public API Example

This example demonstrates how to use Hibachi's public API endpoints.
No authentication is required for these endpoints - they provide market data
and exchange information available to everyone.

Endpoints covered:
- Exchange information and status
- Market prices (bid, ask, mark, spot)
- 24h statistics (high, low, volume)
- Recent trades
- Candlestick data (klines)
- Open interest
- Order book
- Asset inventory and markets
"""

from hibachi_xyz import (
    HibachiApiClient,
    Interval,
    get_version,
)
from hibachi_xyz.helpers import (
    format_maintenance_window,
    get_next_maintenance_window,
)


def example_public_api() -> None:
    """Demonstrate all public API endpoints without authentication."""

    print("=" * 70)
    print("Hibachi Public API Example")
    print("=" * 70)

    # Display SDK version
    ver = get_version()
    print(f"\n[Info] Hibachi Python SDK Version: {ver}\n")

    # Initialize client without authentication (for public endpoints only)
    print("[Setup] Initializing API client (no authentication needed)...")
    hibachi = HibachiApiClient()

    # ==================================================================
    # EXCHANGE INFORMATION
    # ==================================================================
    print("\n" + "=" * 70)
    print("1. EXCHANGE INFORMATION")
    print("=" * 70)

    exch_info = hibachi.get_exchange_info()
    print("\n[Exchange Info] Full response:")

    print(exch_info)

    print(f"\n[Exchange Status] {exch_info.status}")

    # Check next maintenance window
    next_maintenance_window = get_next_maintenance_window(exch_info)
    if next_maintenance_window:
        formatted = format_maintenance_window(next_maintenance_window)
        print(f"\n[Maintenance] {formatted}")
    else:
        print("\n[Maintenance] No scheduled maintenance windows")

    # ==================================================================
    # MARKET PRICES
    # ==================================================================
    print("\n" + "=" * 70)
    print("2. MARKET PRICES")
    print("=" * 70)

    # Get current prices for a symbol
    print("\n[Fetching] Current prices for BTC/USDT-P...")
    prices = hibachi.get_prices("BTC/USDT-P")

    print(f"\n[Symbol] {prices.symbol}")
    print(f"  Ask Price:   ${prices.askPrice}")
    print(f"  Bid Price:   ${prices.bidPrice}")
    print(f"  Mark Price:  ${prices.markPrice}")
    print(f"  Spot Price:  ${prices.spotPrice}")
    print(f"  Trade Price: ${prices.tradePrice}")

    print("\n[Funding Rate]")
    print(f"  Estimated Rate: {prices.fundingRateEstimation.estimatedFundingRate}")
    print(f"  Next Funding:   {prices.fundingRateEstimation.nextFundingTimestamp}")

    # ==================================================================
    # 24-HOUR STATISTICS
    # ==================================================================
    print("\n" + "=" * 70)
    print("3. 24-HOUR STATISTICS")
    print("=" * 70)

    print("\n[Fetching] 24h statistics for BTC/USDT-P...")
    stats = hibachi.get_stats("BTC/USDT-P")

    print(f"\n[24h Stats] {stats.symbol}")
    print(f"  High:   ${stats.high24h}")
    print(f"  Low:    ${stats.low24h}")
    print(f"  Volume: {stats.volume24h} (notional)")

    # ==================================================================
    # RECENT TRADES
    # ==================================================================
    print("\n" + "=" * 70)
    print("4. RECENT TRADES")
    print("=" * 70)

    print("\n[Fetching] Recent trades for BTC/USDT-P...")
    gettrades = hibachi.get_trades("BTC/USDT-P")

    print(f"\n[Trades] Found {len(gettrades.trades)} recent trades")
    print("[Sample] First 3 trades:")
    for i, trade in enumerate(gettrades.trades[:3], 1):
        print(
            f"  {i}. Price: ${trade.price}, Qty: {trade.quantity}, Side: {trade.takerSide}"
        )

    # ==================================================================
    # CANDLESTICK DATA (KLINES)
    # ==================================================================
    print("\n" + "=" * 70)
    print("5. CANDLESTICK DATA (KLINES)")
    print("=" * 70)

    print("\n[Fetching] Weekly candlesticks for BTC/USDT-P...")
    candlesticks = hibachi.get_klines("BTC/USDT-P", Interval.ONE_WEEK)

    print(f"\n[Klines] Found {len(candlesticks.klines)} weekly candles")
    print("[Sample] Most recent candle:")
    if candlesticks.klines:
        latest = candlesticks.klines[0]
        print(f"  Open:   ${latest.open}")
        print(f"  High:   ${latest.high}")
        print(f"  Low:    ${latest.low}")
        print(f"  Close:  ${latest.close}")
        print(f"  Volume: {latest.volumeNotional}")

    # ==================================================================
    # OPEN INTEREST
    # ==================================================================
    print("\n" + "=" * 70)
    print("6. OPEN INTEREST")
    print("=" * 70)

    print("\n[Fetching] Open interest for BTC/USDT-P...")
    open_interest = hibachi.get_open_interest("BTC/USDT-P")

    print(
        f"\n[Open Interest] Total open position quantity: {open_interest.totalQuantity} BTC"
    )

    # ==================================================================
    # ORDER BOOK
    # ==================================================================
    print("\n" + "=" * 70)
    print("7. ORDER BOOK")
    print("=" * 70)

    print("\n[Fetching] Order book for SOL/USDT-P (depth=5, granularity=0.01)...")
    orderbook = hibachi.get_orderbook("SOL/USDT-P", depth=5, granularity=0.01)

    print("\n[Order Book] SOL/USDT-P")
    print(f"  Best Ask: ${orderbook.ask[0].price} (qty: {orderbook.ask[0].quantity})")
    print(f"  Best Bid: ${orderbook.bid[0].price} (qty: {orderbook.bid[0].quantity})")
    print(f"\n  Ask side has {len(orderbook.ask)} levels")
    print(f"  Bid side has {len(orderbook.bid)} levels")

    # ==================================================================
    # INVENTORY & MARKETS
    # ==================================================================
    print("\n" + "=" * 70)
    print("8. INVENTORY & MARKETS")
    print("=" * 70)

    print("\n[Fetching] Complete inventory and market information...")
    inventory = hibachi.get_inventory()

    print(f"\n[Cross-Chain Assets] {len(inventory.crossChainAssets)} assets available")
    for asset in inventory.crossChainAssets[:3]:  # Show first 3
        print(f"  {asset.token} on {asset.chain}")
        print(f"    Exchange rate: {asset.exchangeRateToUSDT} USDT")
        print(
            f"    Instant withdrawal range: ${asset.instantWithdrawalLowerLimitInUSDT} - ${asset.instantWithdrawalUpperLimitInUSDT}"
        )

    print(f"\n[Markets] {len(inventory.markets)} trading pairs available")
    for market in inventory.markets[:3]:  # Show first 3
        print(f"  {market.contract.displayName}")
        print(f"    Symbol: {market.contract.symbol}")
        print(f"    Status: {market.contract.status}")
        print(f"    Min Order: {market.contract.minOrderSize}")

    print(f"\n[Trading Tiers] {len(inventory.tradingTiers)} tiers")
    for tier in inventory.tradingTiers[:3]:  # Show first 3
        print(f"  Level {tier.level}: {tier.title}")
        print(f"    Range: ${tier.lowerThreshold} - ${tier.upperThreshold}")

    print("\n[Fee Config]")
    print(f"  Maker Fee:    {inventory.feeConfig.tradeMakerFeeRate}")
    print(f"  Taker Fee:    {inventory.feeConfig.tradeTakerFeeRate}")
    print(f"  Deposit Fee:  {inventory.feeConfig.depositFees}")
    print(f"  Withdrawal:   {inventory.feeConfig.withdrawalFees}")

    # ==================================================================
    # SUMMARY
    # ==================================================================
    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)
    print("\n[Note] All public endpoints can be called without authentication.")
    print(
        "[Note] For authenticated endpoints (trading, account info), see example_rest_api.py\n"
    )


if __name__ == "__main__":
    """
    Run the public API example.

    Usage:
        python example_public_api.py

    No authentication required - this example only uses public endpoints.
    """
    example_public_api()
