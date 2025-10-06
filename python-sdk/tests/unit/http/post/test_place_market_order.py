import pytest

from hibachi_xyz.types import Side
from tests.mock_executors import MockSuccessfulOutput
from tests.unit.conftest import load_json_all_cases


@pytest.mark.parametrize("test_data", load_json_all_cases("test.place_market_order"))
def test_place_market_order(mock_http_client, test_data):
    payload, path = test_data
    client, mock_http = mock_http_client

    # Extract payloads
    exchange_info = payload["response.exchange_info"]
    order_response = payload["response.order"]

    # Extract test parameters from order response
    symbol = order_response["symbol"]
    quantity = order_response["quantity"]
    side = Side(order_response["side"])
    max_fees_percent = order_response["maxFeesPercent"]

    # Mock check_auth_data call (first call from place_market_order)
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=None,
            call_validation=lambda call: call.function_name == "check_auth_data",
        )
    )

    # Mock exchange_info call (needed for __check_symbol in place_market_order)
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=exchange_info,
            call_validation=lambda call: call.function_name == "send_simple_request"
            and call.arg_pack == ("/market/exchange-info",),
        )
    )

    # Mock check_auth_data call (second call from _create_order_request_data)
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=None,
            call_validation=lambda call: call.function_name == "check_auth_data",
        )
    )

    # Mock send_authorized_request call for order placement
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=order_response,
            call_validation=lambda call: call.function_name == "send_authorized_request"
            and call.arg_pack[0:2] == ("POST", "/trade/order")
            and call.arg_pack[2] is not None,
        )
    )

    nonce, order_id = client.place_market_order(
        symbol, quantity, side, max_fees_percent
    )

    # Assertions
    assert order_id == order_response["orderId"]
