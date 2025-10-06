import pytest

from tests.mock_executors import MockSuccessfulOutput
from tests.unit.conftest import load_json_all_cases


@pytest.mark.parametrize("test_data", load_json_all_cases("response.open_interest"))
def test_get_open_interest(mock_http_client, test_data):
    payload, path = test_data
    client, mock_http = mock_http_client

    symbol = "ETH/USDT-P"

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=payload,
            call_validation=lambda call: call.function_name == "send_simple_request"
            and call.arg_pack == (f"/market/data/open-interest?symbol={symbol}",),
        )
    )

    open_interest = client.get_open_interest(symbol)

    # OpenInterestResponse assertions
    assert open_interest.totalQuantity == payload["totalQuantity"]
