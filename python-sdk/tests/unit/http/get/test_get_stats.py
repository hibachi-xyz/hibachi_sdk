import pytest

from tests.mock_executors import MockSuccessfulOutput
from tests.unit.conftest import load_json_all_cases


@pytest.mark.parametrize("test_data", load_json_all_cases("response.stats"))
def test_get_stats(mock_http_client, test_data):
    payload, path = test_data
    client, mock_http = mock_http_client

    symbol = payload["symbol"]

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=payload,
            call_validation=lambda call: call.function_name == "send_simple_request"
            and call.arg_pack == (f"/market/data/stats?symbol={symbol}",),
        )
    )

    stats = client.get_stats(symbol)

    # StatsResponse assertions
    assert stats.high24h == payload["high24h"]
    assert stats.low24h == payload["low24h"]
    assert stats.symbol == payload["symbol"]
    assert stats.volume24h == payload["volume24h"]
