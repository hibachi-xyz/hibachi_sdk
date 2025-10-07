import pytest

from tests.mock_executors import MockSuccessfulOutput
from tests.unit.conftest import load_json_all_cases


@pytest.mark.parametrize("test_data", load_json_all_cases("response.capital_balance"))
def test_get_capital_balance(mock_http_client, test_data):
    payload, path = test_data
    client, mock_http = mock_http_client

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=payload,
            call_validation=lambda call: call.function_name == "send_authorized_request"
            and call.arg_pack[0] == "GET"
            and call.arg_pack[1] == f"/capital/balance?accountId={client.account_id}",
        )
    )

    balance = client.get_capital_balance()

    # CapitalBalance assertions
    assert balance.balance == payload["balance"]
