from hibachi_xyz import (
    TPSLConfig,
    HibachiApiClient,
)
from hibachi_xyz.types import (
    OrderFlags,
    Side,
)

import asyncio
from hibachi_xyz import HibachiWSTradeClient
from hibachi_xyz.env_setup import setup_environment



def example_tpsl_rest():
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

    exch_info = hibachi.get_exchange_info()
    prices = hibachi.get_prices("SOL/USDT-P")

    max_fees_percent = float(exch_info.feeConfig.tradeTakerFeeRate) * 2.0

    position_quantity = 0.02

    # place limit order at current mark price with attached tpsls
    (nonce, order_id) = hibachi.place_limit_order(
        symbol="SOL/USDT-P",
        quantity=position_quantity,
        price=float(prices.markPrice),
        side=Side.BID,
        max_fees_percent=max_fees_percent,
        tpsl=TPSLConfig()
        # sell any remaining quantity when price hits 1.1 * current mark price
        .add_take_profit(
            price=float(prices.markPrice) * 1.10
        )  # quantity defaults to full quantity of limit order
        # sell any remaining quantity when price hits 0.9 * current mark price
        .add_stop_loss(
            price=float(prices.markPrice) * 0.9
        ),  # quantity defaults to full quantity of limit order
    )

    # place market order with multiple attached tpsls
    (nonce, order_id) = hibachi.place_market_order(
        symbol="SOL/USDT-P",
        quantity=position_quantity,
        side=Side.BID,
        max_fees_percent=max_fees_percent,
        tpsl=TPSLConfig()
        # sell up to 25% quantity when price hits 1.2 * current mark price
        .add_take_profit(
            price=float(prices.markPrice) * 1.20, quantity=position_quantity * 0.25
        )
        # sell up to 75% quantity when price hits 1.1 * current mark price
        .add_take_profit(
            price=float(prices.markPrice) * 1.10, quantity=position_quantity * 0.75
        )
        # sell up to 75% quantity when price hits 0.9 * current mark price
        .add_stop_loss(
            price=float(prices.markPrice) * 0.9, quantity=position_quantity * 0.75
        )
        # sell any remaining quantity when price hits 0.85 * current mark price
        .add_stop_loss(
            price=float(prices.markPrice) * 0.85
        ),  # quantity defaults to full quantity of market order
    )

    # place tpsl on existing position
    # a tpsl order is a trigger order with the reduce only flag set
    # assuming our current posiiton is 0.02 long sol entered at prices.markPrice,
    # this is a take profit order for 75% qty at 10% profit
    (nonce, order_id) = hibachi.place_market_order(
        symbol="SOL/USDT-P",
        quantity=position_quantity * 0.75,
        side=Side.ASK,
        max_fees_percent=max_fees_percent,
        trigger_price=float(prices.markPrice) * 1.10,
        order_flags=OrderFlags.ReduceOnly,
        # This code only runs when the file is executed directly
    )

    # assuming our current posiiton is 0.02 long sol entered at prices.markPrice,
    # this is a stop loss order for 50% qty at 10% loss
    (nonce, order_id) = hibachi.place_market_order(
        symbol="SOL/USDT-P",
        quantity=position_quantity * 0.5,
        side=Side.ASK,
        max_fees_percent=max_fees_percent,
        trigger_price=float(prices.markPrice) * 0.9,
        order_flags=OrderFlags.ReduceOnly,
    )


async def example_tpsl_ws_client():
    # load environment variables from .env file
    # make sure to create a .env file with the required variables
    # or set them in your environment
    api_endpoint, data_api_endpoint, api_key, account_id, private_key, public_key, _ = (
        setup_environment()
    )

    client = HibachiWSTradeClient(
        api_url=api_endpoint,
        data_api_url=data_api_endpoint,
        api_key=api_key,
        account_id=account_id,
        private_key=private_key,
        account_public_key=public_key,
    )

    await client.connect()

    # Still REST under the hood
    exch_info = client.api.get_exchange_info()
    prices = client.api.get_prices("SOL/USDT-P")

    max_fees_percent = float(exch_info.feeConfig.tradeTakerFeeRate) * 2.0

    position_quantity = 0.02

    # place limit order at current mark price with attached tpsls
    (nonce, order_id) = client.api.place_limit_order(
        symbol="SOL/USDT-P",
        quantity=position_quantity,
        price=float(prices.markPrice),
        side=Side.BID,
        max_fees_percent=max_fees_percent,
        tpsl=TPSLConfig()
        # sell any remaining quantity when price hits 1.1 * current mark price
        .add_take_profit(
            price=float(prices.markPrice) * 1.10
        )  # quantity defaults to full quantity of limit order
        # sell any remaining quantity when price hits 0.9 * current mark price
        .add_stop_loss(
            price=float(prices.markPrice) * 0.9
        ),  # quantity defaults to full quantity of limit order
    )

    # place market order with multiple attached tpsls
    (nonce, order_id) = client.api.place_market_order(
        symbol="SOL/USDT-P",
        quantity=position_quantity,
        side=Side.BID,
        max_fees_percent=max_fees_percent,
        tpsl=TPSLConfig()
        # sell up to 25% quantity when price hits 1.2 * current mark price
        .add_take_profit(
            price=float(prices.markPrice) * 1.20, quantity=position_quantity * 0.25
        )
        # sell up to 75% quantity when price hits 1.1 * current mark price
        .add_take_profit(
            price=float(prices.markPrice) * 1.10, quantity=position_quantity * 0.75
        )
        # sell up to 75% quantity when price hits 0.9 * current mark price
        .add_stop_loss(
            price=float(prices.markPrice) * 0.9, quantity=position_quantity * 0.75
        )
        # sell any remaining quantity when price hits 0.85 * current mark price
        .add_stop_loss(
            price=float(prices.markPrice) * 0.85
        ),  # quantity defaults to full quantity of market order
    )

    # place tpsl on existing position
    # a tpsl order is a trigger order with the reduce only flag set
    # assuming our current posiiton is 0.02 long sol entered at prices.markPrice,
    # this is a take profit order for 75% qty at 10% profit
    (nonce, order_id) = client.api.place_market_order(
        symbol="SOL/USDT-P",
        quantity=position_quantity * 0.75,
        side=Side.ASK,
        max_fees_percent=max_fees_percent,
        trigger_price=float(prices.markPrice) * 1.10,
        order_flags=OrderFlags.ReduceOnly,
        # This code only runs when the file is executed directly
    )

    # assuming our current posiiton is 0.02 long sol entered at prices.markPrice,
    # this is a stop loss order for 50% qty at 10% loss
    (nonce, order_id) = client.api.place_market_order(
        symbol="SOL/USDT-P",
        quantity=position_quantity * 0.5,
        side=Side.ASK,
        max_fees_percent=max_fees_percent,
        trigger_price=float(prices.markPrice) * 0.9,
        order_flags=OrderFlags.ReduceOnly,
    )


if __name__ == "__main__":
    # example_tpsl_rest()
    asyncio.run(example_tpsl_ws_client())
