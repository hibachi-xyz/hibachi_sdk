import pytest

from tests.mock_executors import MockSuccessfulOutput
from tests.unit.conftest import load_json_all_cases


@pytest.mark.parametrize("test_data", load_json_all_cases("response.trades"))
def test_get_trades(mock_http_client, test_data):
    payload, path = test_data
    client, mock_http = mock_http_client

    # Extract symbol from first trade or use a test symbol
    symbol = "ETH/USDT-P"

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=payload,
            call_validation=lambda call: call.function_name == "send_simple_request"
            and call.arg_pack == (f"/market/data/trades?symbol={symbol}",),
        )
    )

    trades_response = client.get_trades(symbol)

    # TradesResponse assertions
    assert len(trades_response.trades) == len(payload["trades"])

    for trade, payload_trade in zip(trades_response.trades, payload["trades"]):
        assert trade.price == payload_trade["price"]
        assert trade.quantity == payload_trade["quantity"]
        assert trade.takerSide.value == payload_trade["takerSide"]
        assert trade.timestamp == payload_trade["timestamp"]
