import pytest

from tests.mock_executors import MockSuccessfulOutput
from tests.unit.conftest import load_json_all_cases


@pytest.mark.parametrize("test_data", load_json_all_cases("test.withdraw"))
def test_withdraw(mock_http_client, test_data):
    payload, path = test_data
    client, mock_http = mock_http_client

    # Extract payloads
    exchange_info = payload["response.exchange_info"]
    withdraw_response = payload["response.withdraw"]

    # Extract test parameters from withdraw response
    coin = withdraw_response["coin"]
    withdraw_address = withdraw_response["withdrawAddress"]
    quantity = withdraw_response["quantity"]
    max_fees = withdraw_response["maxFees"]
    network = withdraw_response["network"]

    # Mock check_auth_data call
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=None,
            call_validation=lambda call: call.function_name == "check_auth_data",
        )
    )

    # Mock exchange_info call (needed for withdraw to determine asset ID)
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=exchange_info,
            call_validation=lambda call: call.function_name == "send_simple_request"
            and call.arg_pack == ("/market/exchange-info",),
        )
    )

    # Mock send_authorized_request call for withdraw
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=withdraw_response,
            call_validation=lambda call: call.function_name == "send_authorized_request"
            and call.arg_pack[0:2] == ("POST", "/capital/withdraw")
            and call.arg_pack[2] is not None,
        )
    )

    response = client.withdraw(coin, withdraw_address, quantity, max_fees, network)

    # WithdrawResponse assertions
    assert response.orderId == withdraw_response["orderId"]
