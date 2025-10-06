import pytest

from tests.mock_executors import MockSuccessfulOutput
from tests.unit.conftest import load_json_all_cases


@pytest.mark.parametrize("test_data", load_json_all_cases("response.cancel_order"))
def test_cancel_order(mock_http_client, test_data):
    payload, path = test_data
    client, mock_http = mock_http_client

    # Extract test parameters
    order_id = payload.get("orderId")
    nonce = payload.get("nonce")

    # Mock check_auth_data call
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=None,
            call_validation=lambda call: call.function_name == "check_auth_data",
        )
    )

    # Mock send_authorized_request call for cancel
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=payload,
            call_validation=lambda call: call.function_name == "send_authorized_request"
            and call.arg_pack[0:2] == ("DELETE", "/trade/order")
            and call.arg_pack[2] is not None,
        )
    )

    response = client.cancel_order(order_id=order_id, nonce=nonce)

    # Assertions
    if order_id:
        assert response["orderId"] == payload["orderId"]
    if nonce:
        assert response["nonce"] == payload["nonce"]
