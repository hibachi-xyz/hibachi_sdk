import copy

import pytest

from tests.mock_executors import MockSuccessfulOutput
from tests.unit.conftest import load_json_all_cases


@pytest.mark.parametrize("test_data", load_json_all_cases("response.capital_history"))
def test_get_capital_history(mock_http_client, test_data):
    payload, path = test_data
    client, mock_http = mock_http_client

    # Save original transactions before they get mutated
    original_transactions = copy.deepcopy(payload["transactions"])

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=payload,
            call_validation=lambda call: call.function_name == "send_authorized_request"
            and call.arg_pack[0] == "GET"
            and call.arg_pack[1] == f"/capital/history?accountId={client.account_id}",
        )
    )

    history = client.get_capital_history()

    # CapitalHistory assertions
    assert len(history.transactions) == len(original_transactions)

    for tx, orig_tx in zip(history.transactions, original_transactions):
        assert tx.id == orig_tx["id"]
        assert tx.assetId == orig_tx["assetId"]
        assert tx.quantity == orig_tx["quantity"]
        assert tx.status == orig_tx["status"]
        assert tx.timestampSec == orig_tx["timestampSec"]
        assert tx.transactionType == orig_tx["transactionType"]
