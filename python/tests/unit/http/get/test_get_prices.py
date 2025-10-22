import copy

import pytest

from hibachi_xyz.errors import DeserializationError
from hibachi_xyz.executors.interface import HttpResponse
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
            output=HttpResponse(status=200, body=payload),
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


def test_get_prices_deserialization_error(mock_http_client):
    """Test that malformed response raises DeserializationError."""
    client, mock_http = mock_http_client

    # Malformed response with invalid fundingRateEstimation (missing required fields)
    malformed_payload = {
        "symbol": "BTC/USDT-P",
        "markPrice": "50000",
        "fundingRateEstimation": {},  # Empty dict missing required fields
    }

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=200, body=malformed_payload),
            call_validation=lambda call: call.function_name == "send_simple_request",
        )
    )

    with pytest.raises(DeserializationError) as exc_info:
        client.get_prices("BTC/USDT-P")

    assert "Received invalid response" in str(exc_info.value)
