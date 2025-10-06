import pytest

from tests.mock_executors import MockSuccessfulOutput
from tests.unit.conftest import load_json_all_cases


@pytest.mark.parametrize("test_data", load_json_all_cases("response.deposit_info"))
def test_get_deposit_info(mock_http_client, test_data):
    payload, path = test_data
    client, mock_http = mock_http_client

    public_key = "test_public_key_123"

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=payload,
            call_validation=lambda call: call.function_name == "send_authorized_request"
            and call.arg_pack
            == (
                "GET",
                f"/capital/deposit-info?accountId={client.account_id}&publicKey={public_key}",
                None,
            ),
        )
    )

    deposit_info = client.get_deposit_info(public_key)

    # DepositInfo assertions
    assert deposit_info.depositAddressEvm == payload["depositAddressEvm"]
