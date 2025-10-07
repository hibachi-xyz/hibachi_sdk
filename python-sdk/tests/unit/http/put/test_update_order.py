import pytest

from tests.mock_executors import MockSuccessfulOutput
from tests.unit.conftest import load_json_all_cases


@pytest.mark.parametrize("test_data", load_json_all_cases("test.update_order"))
def test_update_order(mock_http_client, test_data):
    payload, path = test_data
    client, mock_http = mock_http_client

    # Extract payloads
    exchange_info = payload["response.exchange_info"]
    order_details = payload["response.order_details"]
    update_response = payload["response.update"]

    # Extract test parameters
    order_id = update_response["orderId"]
    max_fees_percent = update_response["maxFeesPercent"]
    quantity = update_response.get("quantity")
    price = update_response.get("price")

    # Mock get_order_details call
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=order_details,
            call_validation=lambda call: call.function_name == "send_authorized_request"
            and call.arg_pack[0] == "GET"
            and "/trade/order" in call.arg_pack[1],
        )
    )

    # Mock exchange_info call (needed for __get_contract)
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=exchange_info,
            call_validation=lambda call: call.function_name == "send_simple_request"
            and call.arg_pack == ("/market/exchange-info",),
        )
    )

    # Mock send_authorized_request call for update
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=update_response,
            call_validation=lambda call: call.function_name == "send_authorized_request"
            and call.arg_pack[0:2] == ("PUT", "/trade/order")
            and call.arg_pack[2] is not None,
        )
    )

    response = client.update_order(
        order_id, max_fees_percent, quantity=quantity, price=price
    )

    # Assertions
    assert response["orderId"] == update_response["orderId"]
