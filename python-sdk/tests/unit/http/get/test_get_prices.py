import copy

import pytest

from tests.mock_executors import MockSuccessfulOutput
from tests.unit.conftest import load_json_all_cases


@pytest.mark.parametrize("test_data", load_json_all_cases("response.prices"))
def test_get_prices(mock_http_client, test_data):
    payload, path = test_data
    client, mock_http = mock_http_client

    # Save original funding rate estimation before it gets mutated
    original_funding = copy.deepcopy(payload["fundingRateEstimation"])
    symbol = payload["symbol"]

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=payload,
            call_validation=lambda call: call.function_name == "send_simple_request"
            and call.arg_pack == (f"/market/data/prices?symbol={symbol}",),
        )
    )

    prices = client.get_prices(symbol)

    # PriceResponse assertions
    assert prices.askPrice == payload["askPrice"]
    assert prices.bidPrice == payload["bidPrice"]
    assert prices.markPrice == payload["markPrice"]
    assert prices.spotPrice == payload["spotPrice"]
    assert prices.symbol == payload["symbol"]
    assert prices.tradePrice == payload["tradePrice"]

    # FundingRateEstimation assertions
    assert (
        prices.fundingRateEstimation.estimatedFundingRate
        == original_funding["estimatedFundingRate"]
    )
    assert (
        prices.fundingRateEstimation.nextFundingTimestamp
        == original_funding["nextFundingTimestamp"]
    )
