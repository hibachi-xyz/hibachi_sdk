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
    Side,
)


def example_auth_rest_api():
    # load environment variables from .env file
    # make sure to create a .env file with the required variables
    # or set them in your environment
    api_endpoint, data_api_endpoint, api_key, account_id, private_key, _, _ = (
        setup_environment()
    )

    hibachi = HibachiApiClient(
        api_url=api_endpoint,
        data_api_url=data_api_endpoint,
        api_key=api_key,
        account_id=account_id,
        private_key=private_key,
    )

    # Get Account Info
    #
    # AccountInfo(
    #   assets=[Asset(quantity='400.566542', symbol='USDT')],
    #   balance='404.256286',
    #   maximalWithdraw='386.117897',
    #   numFreeTransfersRemaining=91,
    #   positions=[
    #       Position(direction='Long',
    #           entryNotional='290.181588',
    #           markPrice='145.3309591',
    #           notionalValue='290.661918',
    #           openPrice='145.0907940',
    #           quantity='2.00000000',
    #           symbol='SOL/USDT-P',
    #           unrealizedFundingPnl='-0.040593',
    #           unrealizedTradingPnl='0.480330'
    #        ),
    #       Position(direction='Long',
    #           entryNotional='1497.639739',
    #           markPrice='107977.67957',
    #           notionalValue='1500.889746',
    #           openPrice='107743.86612',
    #           quantity='0.0139000000',
    #           symbol='BTC/USDT-P',
    #           unrealizedFundingPnl='0.000000',
    #           unrealizedTradingPnl='3.250007')
    #   ],
    #   totalOrderNotional='9.831627',
    #   totalPositionNotional='1791.551664',
    #   totalUnrealizedFundingPnl='-0.040593',
    #   totalUnrealizedPnl='3.689744',
    #   totalUnrealizedTradingPnl='3.730337',
    #   tradeMakerFeeRate='0.00015000',
    #   tradeTakerFeeRate='0.00045000')
    #
    print("\nAccount Info:\n-------------------")
    account_info = hibachi.get_account_info()
    print(account_info)

    print(f"Account Balance: {account_info.balance}")
    print(f"total Position Notional: {account_info.totalPositionNotional}")
    for asset in account_info.assets:
        print(f"Asset: \t\t{asset.symbol} \t\t{asset.quantity}")

    for position in account_info.positions:
        print(f"Position: \t{position.symbol} \t{position.quantity}")

    # Get Account Trades
    #
    # AccountTradesResponse(
    #     trades=[
    #         AccountTrade(
    #             askAccountId=126,
    #             askOrderId=588733852838789120,
    #             bidAccountId=273,
    #             bidOrderId=588744753406280705,
    #             fee='0.048618',
    #             id=159729044,
    #             orderType='MARKET',
    #             price='108040.01266',
    #             quantity='0.0010000000',
    #             realizedPnl='0.000000',
    #             side='Buy',
    #             symbol='BTC/USDT-P',
    #             timestamp=1750926945
    #         ),
    #         AccountTrade(
    #             askAccountId=126,
    #             askOrderId=588733852838789120,
    #             bidAccountId=273,
    #             bidOrderId=588744750475772928,
    #             fee='0.004861',
    #             id=159728906,
    #             orderType='MARKET',
    #             price='108040.01266',
    #             quantity='0.0001000000',
    #             realizedPnl='0.000001',
    #             side='Buy',
    #             symbol='BTC/USDT-P',
    #             timestamp=1750926934
    #         ),
    #         # ... more trades
    #     ]
    # )
    print("\nAccount Trades:\n-------------------")
    trades_response = hibachi.get_account_trades()
    print(trades_response)

    # Get Settlements History
    #
    # SettlementsResponse(
    #     settlements=[
    #         Settlement(
    #             direction='Long',
    #             indexPrice='107370.46250',
    #             quantity='0.0047000000',
    #             settledAmount='-0.021688691085131433',
    #             symbol='BTC/USDT-P',
    #             timestamp=1750896000
    #             ),
    #         Settlement(
    #             direction='Long',
    #             indexPrice='107065.07459',
    #             quantity='0.0025000000',
    #             settledAmount='0.0030837219795575247',
    #             symbol='BTC/USDT-P',
    #             timestamp=1750867200
    #         ),
    #         # ... more settlements
    #     ]
    # )
    print("\nSettlements History:\n-------------------")
    settlements_response = hibachi.get_settlements_history()
    print(settlements_response)

    # Get Pending Orders
    #
    # PendingOrdersResponse(
    #     orders=[
    #         Order(
    #             accountId=273,
    #             availableQuantity='0.0001000000',
    #             contractId=2,
    #             creationTime=1750926967,
    #             finishTime=None,
    #             numOrdersRemaining=None,
    #             numOrdersTotal=None,
    #             orderFlags=None,
    #             orderId='588744759140156416',
    #             orderType=<OrderType.LIMIT: 'LIMIT'>,
    #             price='98316.27279',
    #             quantityMode=None,
    #             side=<Side.BID: 'BID'>,
    #             status=<OrderStatus.PLACED: 'PLACED'>,
    #             symbol='BTC/USDT-P',
    #             totalQuantity='0.0001000000',
    #             triggerPrice=None
    #             ),
    #             # ... more orders
    #         ]
    # )
    #
    print("\nPending Orders:\n-------------------")
    pending_orders_response = hibachi.get_pending_orders()
    print(pending_orders_response)
    # example:
    # print(pending_orders_response.orders[0].symbol,pending_orders_response.orders[0].orderId)

    # Get Capital Balance
    #
    print("\nCapital Balance:\n-------------------")
    capital_balance = hibachi.get_capital_balance()
    print(capital_balance.balance)

    # Get Capital History
    # CapitalHistory(
    #     transactions=[
    #         Transaction(id=67925,
    #             assetId=1,
    #             quantity='5.000000',
    #             status='completed',
    #             timestamp=1750926950,
    #             transactionType='transfer-out',
    #             transactionHash=None,
    #             token=None,
    #             etaTsSec=None,
    #             blockNumber=None,
    #             chain=None,
    #             instantWithdrawalChain=None,
    #             instantWithdrawalToken=None,
    #             isInstantWithdrawal=None,
    #             withdrawalAddress=None,
    #             receivingAccountId=365,
    #             receivingAddress='0xfea558a78c1aaf0f1b1469cb6d1819aa9a0c5b6a',
    #             srcAccountId=None,
    #             srcAddress=None
    #         ),
    #         # ... more transactions
    #     ]
    # )
    print("\nCapital History:\n-------------------")
    history = hibachi.get_capital_history()
    print(history)

    exch_info = hibachi.get_exchange_info()
    prices = hibachi.get_prices("BTC/USDT-P")

    # Place a Market Order
    # For more information please see the README documentation
    print("\nPlacing a Market Order:\n-------------------")
    print(hibachi.account_id)
    (nonce, order_id) = hibachi.place_market_order(
        symbol="BTC/USDT-P",
        quantity=0.0001,
        side=Side.BUY,
        max_fees_percent=float(exch_info.feeConfig.tradeTakerFeeRate) * 2.0,
    )

    # Market Order Placed: Nonce: 1750928720123123, Order ID: 588745218831456123
    print(f"Market Order Placed: Nonce: {nonce}, Order ID: {order_id}")

    # Advanced Order
    (nonce, order_id) = hibachi.place_limit_order(
        symbol="BTC/USDT-P",
        quantity=0.0001,
        price=float(prices.markPrice),
        side=Side.BID,
        max_fees_percent=float(exch_info.feeConfig.tradeTakerFeeRate) * 2.0,
        trigger_price=float(prices.markPrice) * 0.95,
    )
    print(f"Market Order Placed: Nonce: {nonce}, Order ID: {order_id}")

    # Get Order Details
    # Order(
    #   accountId=273,
    #   availableQuantity='0.0001000000',
    #   contractId=2,
    #   creationTime=None,
    #   finishTime=None,
    #   numOrdersRemaining=None,
    #   numOrdersTotal=None,
    #   orderFlags=None,
    #   orderId='588745309326672896',
    #   orderType=<OrderType.LIMIT: 'LIMIT'>,
    #   price='107499.38358',
    #   quantityMode=None,
    #   side=<Side.BID: 'BID'>,
    #   status=<OrderStatus.PENDING: 'PENDING'>,
    #   symbol='BTC/USDT-P',
    #   totalQuantity='0.0001000000',
    #   triggerPrice='102124.41440'
    # )
    print("\nGet Order Details:\n-------------------")
    order_details = hibachi.get_order_details(order_id=order_id)
    print(order_details.status, order_details.symbol, order_details.price)

    # Cancel an Order
    # must succeed else it raises error.
    # see documentation for more details on nonce and order_id
    hibachi.cancel_order(order_id=order_id, nonce=nonce)

    # Cancel All Orders
    hibachi.cancel_all_orders()

    exch_info = hibachi.get_exchange_info()
    prices = hibachi.get_prices("BTC/USDT-P")

    max_fees_percent = float(exch_info.feeConfig.tradeTakerFeeRate) * 2.0

    # Or all at once
    hibachi.cancel_all_orders()

    # buy some to sell
    (nonce, limit_order_id) = hibachi.place_market_order(
        "BTC/USDT-P", quantity=0.005, side=Side.BUY, max_fees_percent=max_fees_percent
    )

    print(f"Limit order ID: {limit_order_id}, Nonce: {nonce}")

    # ensure we have some BTC/USDT-P position to sell
    account_info = hibachi.get_account_info()

    check = False
    for position in account_info.positions:
        print(f"Position: \t{position.symbol} \t{position.quantity}")
        if position.symbol == "BTC/USDT-P" and float(position.quantity) > 0:
            check = True

    assert check, "Not enough BTC/USDT-P position to sell"

    # place some test orders to update and cancel in batch
    (nonce, limit_order_id) = hibachi.place_limit_order(
        symbol="BTC/USDT-P",
        quantity=0.001,
        price=float(prices.bidPrice) * 0.975,
        side=Side.BID,
        max_fees_percent=max_fees_percent,
    )

    (nonce, trigger_limit_order_id) = hibachi.place_limit_order(
        symbol="BTC/USDT-P",
        quantity=0.001,
        price=float(prices.askPrice) * 1.05,
        side=Side.ASK,
        max_fees_percent=max_fees_percent,
        trigger_price=float(prices.askPrice) * 1.025,
    )

    (nonce, trigger_market_order_id) = hibachi.place_market_order(
        symbol="BTC/USDT-P",
        quantity=0.001,
        side=Side.ASK,
        max_fees_percent=max_fees_percent,
        trigger_price=float(prices.askPrice) * 1.025,
    )

    # Creating, updating and cancelling orders can be done in a batch
    # This requires knowing all details of the existing orders, there is no shortcut for update order details
    response = hibachi.batch_orders(
        [
            # Simple market order
            CreateOrder("BTC/USDT-P", Side.SELL, 0.001, max_fees_percent),
            # Simple limit order
            CreateOrder(
                "BTC/USDT-P",
                Side.SELL,
                0.001,
                max_fees_percent,
                price=float(prices.spotPrice),
            ),
            # Trigger market order
            CreateOrder(
                "BTC/USDT-P",
                Side.SELL,
                0.001,
                max_fees_percent,
                trigger_price=float(prices.spotPrice),
            ),
            # Trigger limit order
            CreateOrder(
                "BTC/USDT-P",
                Side.SELL,
                0.001,
                max_fees_percent,
                price=float(prices.askPrice),
                trigger_price=float(prices.askPrice) * 1.05,
            ),
            # TWAP order
            CreateOrder(
                "BTC/USDT-P",
                Side.SELL,
                0.001,
                max_fees_percent,
                twap_config=TWAPConfig(5, TWAPQuantityMode.FIXED),
            ),
            # Market order, only valid if placed within two seconds
            CreateOrder(
                "BTC/USDT-P", Side.BUY, 0.001, max_fees_percent, creation_deadline=2
            ),
            # Limit order, only valid if placed within one seconds
            CreateOrder(
                "BTC/USDT-P",
                Side.BUY,
                0.001,
                max_fees_percent,
                price=float(prices.spotPrice),
                creation_deadline=1,
            ),
            # Trigger market order, only valid if placed within three seconds
            CreateOrder(
                "BTC/USDT-P",
                Side.BUY,
                0.001,
                max_fees_percent,
                trigger_price=float(prices.askPrice),
                creation_deadline=3,
            ),
            # Trigger limit order, only valid if placed within five seconds
            CreateOrder(
                "BTC/USDT-P",
                Side.BUY,
                0.001,
                max_fees_percent,
                price=float(prices.askPrice),
                trigger_price=float(prices.askPrice),
                creation_deadline=5,
            ),
            # TWAP order only valid if placed within two seconds
            CreateOrder(
                "BTC/USDT-P",
                Side.SELL,
                0.001,
                max_fees_percent,
                twap_config=TWAPConfig(5, TWAPQuantityMode.FIXED),
            ),
            # Update limit order
            # Need to fill all relevant optional parameters
            UpdateOrder(
                limit_order_id,
                "BTC/USDT-P",
                Side.BUY,
                0.001,
                max_fees_percent,
                price=float(prices.askPrice),
            ),
            # update trigger limit order
            # Need to fill all relevant optional parameters
            UpdateOrder(
                trigger_limit_order_id,
                "BTC/USDT-P",
                Side.ASK,
                0.002,
                max_fees_percent,
                price=float(prices.askPrice),
                trigger_price=float(prices.askPrice),
            ),
            # update trigger market order
            # Need to fill all relevant optional parameters
            UpdateOrder(
                trigger_market_order_id,
                "BTC/USDT-P",
                Side.ASK,
                0.001,
                max_fees_percent,
                trigger_price=float(prices.askPrice),
            ),
            # Cancel order
            CancelOrder(order_id=limit_order_id),
            CancelOrder(nonce=nonce),
        ]
    )

    print("\nBatch Order Response:\n-------------------")
    # assert all batch orders were successful
    for order in response.orders:
        print(f"Batch Order result: nonce({order.nonce}) orderId({order.orderId})")

    # Test withdraw request
    # uncomment the following lines to test withdrawal
    # --------------------------------------------------------------------
    # withdrawal_fees = exch_info.feeConfig.withdrawalFees
    # response = hibachi.withdraw(
    #     coin="USDT",
    #     withdraw_address="0x0000000000000000000000000000000000000000",
    #     quantity="1.0",
    #     max_fees=withdrawal_fees
    # )


if __name__ == "__main__":
    # This code only runs when the file is executed directly
    example_auth_rest_api()
