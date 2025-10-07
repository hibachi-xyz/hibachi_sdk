import pytest

from tests.mock_executors import MockSuccessfulOutput
from tests.unit.conftest import load_json_all_cases


@pytest.mark.parametrize("test_data", load_json_all_cases("test.cancel_all_orders"))
def test_cancel_all_orders(mock_http_client, test_data):
    payload, path = test_data
    client, mock_http = mock_http_client

    # Extract payloads
    pending_orders = payload["response.pending_orders"]

    # Mock get_pending_orders call
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=pending_orders,
            call_validation=lambda call: call.function_name == "send_authorized_request"
            and call.arg_pack[0] == "GET"
            and "/trade/orders" in call.arg_pack[1],
        )
    )

    # For each pending order, mock cancel_order sequence
    for order in pending_orders:
        # Mock send_authorized_request call for cancel
        mock_http.stage_output(
            MockSuccessfulOutput(
                output={"orderId": order["orderId"], "status": "cancelled"},
                call_validation=lambda call: call.function_name
                == "send_authorized_request"
                and call.arg_pack[0:2] == ("DELETE", "/trade/order")
                and call.arg_pack[2] is not None,
            )
        )

    client.cancel_all_orders()

    # No return value to assert, just verify all mocks were consumed
