import pytest

from tests.mock_executors import MockSuccessfulOutput
from tests.unit.conftest import load_json_all_cases


@pytest.mark.parametrize("test_data", load_json_all_cases("test.transfer"))
def test_transfer(mock_http_client, test_data):
    payload, path = test_data
    client, mock_http = mock_http_client

    # Extract payloads
    exchange_info = payload["response.exchange_info"]
    transfer_response = payload["response.transfer"]

    # Extract test parameters from transfer response
    coin = transfer_response["coin"]
    quantity = transfer_response["quantity"]
    dstPublicKey = transfer_response["dstPublicKey"]
    max_fees = transfer_response["maxFees"]

    # Mock exchange_info call (needed for transfer to determine asset ID)
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=exchange_info,
            call_validation=lambda call: call.function_name == "send_simple_request"
            and call.arg_pack == ("/market/exchange-info",),
        )
    )

    # Mock send_authorized_request call for transfer
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=transfer_response,
            call_validation=lambda call: call.function_name == "send_authorized_request"
            and call.arg_pack[0:2] == ("POST", "/capital/transfer")
            and call.arg_pack[2] is not None,
        )
    )

    response = client.transfer(coin, quantity, dstPublicKey, max_fees)

    # TransferResponse assertions
    assert response.status == transfer_response["status"]
