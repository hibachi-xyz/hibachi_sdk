from hibachi_xyz import (
    HibachiApiClient,
    Interval,
    get_version,
)
from hibachi_xyz.helpers import (
    format_maintenance_window,
    get_next_maintenance_window,
)


def example_public_api():
    # get current SDK version
    ver = get_version()
    print(f"Hibachi Python SDK Version: {ver}")

    # no authentication is required for public endpoints
    # HibachiApiClient can be initialized without env variables
    hibachi = HibachiApiClient()
    exch_info = hibachi.get_exchange_info()
    print("\nExchange Info:\n-------------------")

    print(exch_info)
    # feeConfig: FeeConfig
    # futureContracts: List[FutureContract]
    # instantWithdrawalLimit: WithdrawalLimit
    # maintenanceWindow: List[MaintenanceWindow]

    # status: "NORMAL" | "MAINTENANCE"
    print("\nExchange status:\n----------------------------------")
    print(exch_info.status)

    # Maintenance Window
    #
    # Next Maintenance Window: The next maintenance window starts
    # in 0d6h0m on 26 June 2025 at 16:00 for a duration of 2 hours.
    # Reason: Updating system.
    #
    next_maintainance_window = get_next_maintenance_window(exch_info)
    print(
        f"\nNext Maintenance Window: {format_maintenance_window(next_maintainance_window)}"
    )

    # Get Prices
    #
    # PriceResponse(
    #   symbol='BTC/USDT-P',
    #   askPrice='107904.30670',
    #   bidPrice='107873.17160',
    #   markPrice='107878.27927',
    #   spotPrice='107876.11891',
    #   tradePrice='107899.38000',
    #   fundingRateEstimation=FundingRateEstimation(
    #       estimatedFundingRate='0.000035',
    #       nextFundingTimestamp=1750953600
    #   ),
    # )
    #
    print("\nPrices for BTC/USDT-P:\n----------------------------------")
    prices = hibachi.get_prices("BTC/USDT-P")
    print(
        prices.symbol,
        prices.askPrice,
        prices.bidPrice,
        prices.markPrice,
        prices.spotPrice,
        prices.tradePrice,
    )
    print(
        f"Estimated Funding Rate: {prices.fundingRateEstimation.estimatedFundingRate}"
    )
    print(
        f"Next Funding Timestamp: {prices.fundingRateEstimation.nextFundingTimestamp}"
    )

    # Get Stats
    #
    # StatsResponse(
    #   high24h='108296.80000',
    #   low24h='106365.66000',
    #   symbol='BTC/USDT-P',
    #   volume24h='1485054.567011'
    # )
    #
    print("\nStats for BTC/USDT-P:\n----------------------------------")
    stats = hibachi.get_stats("BTC/USDT-P")
    print(stats.symbol, stats.high24h, stats.low24h, stats.volume24h)

    # Get Trades
    #
    # TradesResponse(trades=[
    #     Trade(price='107936.33000', quantity='0.0000100000', takerSide=<TakerSide.Buy: 'Buy'>, timestamp=1750924982),
    #     Trade(price='107931.72000', quantity='0.0000100000', takerSide=<TakerSide.Buy: 'Buy'>, timestamp=1750924978),
    #     Trade(price='107923.20000', quantity='0.0001000000', takerSide=<TakerSide.Buy: 'Buy'>, timestamp=1750924944),
    #     # ... continues with more trades
    # ])
    #
    print("\nTrades for BTC/USDT-P:\n----------------------------------")
    gettrades = hibachi.get_trades("BTC/USDT-P")
    print(gettrades.trades)

    # Get Klines (Candlesticks)
    #
    # KlinesResponse(klines=[
    #     Kline(close='108064.30000', high='108296.80000', low='107120.20000', open='107365.15000', interval='1w', timestamp=1750896000, volumeNotional='730616.812011'),
    #     Kline(close='107365.15000', high='108152.93000', low='98223.39000', open='104933.30000', interval='1w', timestamp=1750291200, volumeNotional='14974552.640433'),
    #     Kline(close='104933.30000', high='109000.00000', low='102748.05000', open='108668.65000', interval='1w', timestamp=1749686400, volumeNotional='6909969.252194'),
    #     # ... continues with more klines
    # ])
    #

    print("\nKlines (Candlesticks) for BTC/USDT-P:\n----------------------------------")
    candlesticks = hibachi.get_klines("BTC/USDT-P", Interval.ONE_WEEK)
    print(candlesticks.klines)

    # Get Open Interest
    # OpenInterestResponse(totalQuantity='2.1586388558')
    open_interest = hibachi.get_open_interest("BTC/USDT-P")
    print("\nOpen Interest for BTC/USDT-P:\n----------------------------------")
    print(open_interest.totalQuantity)

    # Get Order Book
    # OrderBook(
    # ask=[
    #     OrderBookLevel(price='145.37', quantity='20.60000000'),
    #     OrderBookLevel(price='145.38', quantity='7.69659323'),
    #     OrderBookLevel(price='145.39', quantity='104.88930005'),
    #     # ... continues with more ask levels
    # ],
    # bid=[
    #     OrderBookLevel(price='145.30', quantity='20.60000000'),
    #     OrderBookLevel(price='145.29', quantity='68.40075907'),
    #     OrderBookLevel(price='145.27', quantity='34.30000000'),
    #     # ... continues with more bid levels
    # ]
    # )
    print("\nOrder Book for SOL/USDT-P:\n----------------------------------")
    orderbook = hibachi.get_orderbook("SOL/USDT-P", depth=5, granularity=0.01)
    print(orderbook.ask[0].price, orderbook.ask[0].quantity)
    print(orderbook.bid[0].price, orderbook.bid[0].quantity)

    # Get Inventory
    #
    # InventoryResponse(
    #     crossChainAssets=[
    #         CrossChainAsset(
    #             chain='Base',
    #             exchangeRateFromUSDT='0.999500',
    #             exchangeRateToUSDT='0.999500',
    #             instantWithdrawalLowerLimitInUSDT='0.03706631921747851',
    #             instantWithdrawalUpperLimitInUSDT='26210.91431555778',
    #             token='USDC'
    #         ),
    #         CrossChainAsset(
    #             chain='Arbitrum',
    #             exchangeRateFromUSDT='0.999500',
    #             exchangeRateToUSDT='0.999500',
    #             instantWithdrawalLowerLimitInUSDT='0.09813976420680001',
    #             instantWithdrawalUpperLimitInUSDT='27737.8571853927',
    #             token='USDC')
    #     ],
    #     feeConfig=FeeConfig(
    #         depositFees='0.009813',
    #         instantWithdrawDstPublicKey='a4fff986badd3b58ead09cc617a82ff1b5b77b98d560baa27fbcffa4c08610b6372f362f3e8e530291f24251f2c332d958bf776c88ae4370380eee943cddf859',
    #         instantWithdrawalFees=[[1000, 0.002], [100, 0.004], [50, 0.005], [20, 0.01], [5, 0.02]],
    #         tradeMakerFeeRate='0.00015000',
    #         tradeTakerFeeRate='0.00045000',
    #         transferFeeRate='0.00010000',
    #         withdrawalFees='0.009813'
    #     ),
    #     markets=[
    #         Market(
    #             contract=FutureContract(
    #                 displayName='SUI/USDT Perps',
    #                 id=23,
    #                 marketCloseTimestamp=None,
    #                 marketOpenTimestamp='1741701600',
    #                 minNotional='1',
    #                 minOrderSize='0.000001',
    #                 orderbookGranularities=['0.00001', '0.0001', '0.001', '0.01'],
    #                 initialMarginRate='0.500000',
    #                 maintenanceMarginRate='0.400000',
    #                 settlementDecimals=6,
    #                 settlementSymbol='USDT',
    #                 status='LIVE',
    #                 stepSize='0.000001',
    #                 symbol='SUI/USDT-P',
    #                 tickSize='0.000000001',
    #                 underlyingDecimals=6,
    #                 underlyingSymbol='SUI'
    #             ),
    #             info=MarketInfo(category='Flash',
    #                 markPrice='2.674250000',
    #                 price24hAgo='2.776700000',
    #                 priceLatest='2.674250000',
    #                 tags=['flash']
    #             )
    #         ),
    #         # ... more markets
    #     ],
    #     tradingTiers=[
    #         TradingTier(level=0, lowerThreshold='0.000000', title='Flicker', upperThreshold='0.000000'),
    #         TradingTier(level=1, lowerThreshold='0.000001', title='Spark', upperThreshold='99.999999'),
    #         TradingTier(level=2, lowerThreshold='100.000000', title='Smolder', upperThreshold='499.999999'),
    #         TradingTier(level=3, lowerThreshold='500.000000', title='Ember', upperThreshold='999.999999'),
    #         # ... more tiers
    #     ]
    # )

    inventory = hibachi.get_inventory()
    print("\nInventory:\n----------------------------------")
    print(inventory)

    # commented for safety, uncomment to use
    # see documentation for more details

    # transfer = hibachi.transfer(
    #     coin="USDT",
    #     quantity="5",
    #     dstPublicKey="0x049c8f81dd7c8001a400a9dd7df7a28ac4a11dd91a6f8ec9ee2c94cf6083116da034f8cd466799f65b11e3416aab95166b8d9e403ec2f268c93cbe150e50500b",
    #     max_fees="0"
    # )


if __name__ == "__main__":
    # This code only runs when the file is executed directly
    example_public_api()
