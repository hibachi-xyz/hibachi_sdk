import pytest

from hibachi_xyz.types import CreateOrder, Side
from tests.mock_executors import MockSuccessfulOutput
from tests.unit.conftest import load_json_all_cases


@pytest.mark.parametrize("test_data", load_json_all_cases("test.batch_orders"))
def test_batch_orders(mock_http_client, test_data):
    payload, path = test_data
    client, mock_http = mock_http_client

    # Extract payloads
    exchange_info = payload["response.exchange_info"]
    batch_response = payload["response.batch"]
    orders_to_create = payload["input.orders"]
    expected_orders = batch_response["orders"]  # Save before it gets modified

    # Mock check_auth_data call (first call from batch_orders)
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=None,
            call_validation=lambda call: call.function_name == "check_auth_data",
        )
    )

    # For each CreateOrder, we need check_auth_data
    # Only the first order triggers exchange_info (sets self.future_contracts)
    for i, _ in enumerate(orders_to_create):
        mock_http.stage_output(
            MockSuccessfulOutput(
                output=None,
                call_validation=lambda call: call.function_name == "check_auth_data",
            )
        )

        if i == 0:
            mock_http.stage_output(
                MockSuccessfulOutput(
                    output=exchange_info,
                    call_validation=lambda call: call.function_name
                    == "send_simple_request"
                    and call.arg_pack == ("/market/exchange-info",),
                )
            )

    # Mock send_authorized_request call for batch
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=batch_response,
            call_validation=lambda call: call.function_name == "send_authorized_request"
            and call.arg_pack[0:2] == ("POST", "/trade/orders")
            and call.arg_pack[2] is not None,
        )
    )

    # Build CreateOrder objects from test data
    orders = [
        CreateOrder(
            symbol=o["symbol"],
            side=Side(o["side"]),
            quantity=o["quantity"],
            max_fees_percent=o["maxFeesPercent"],
            price=o.get("price"),
        )
        for o in orders_to_create
    ]

    response = client.batch_orders(orders)

    # Assertions
    assert len(response.orders) == len(expected_orders)
    for i, resp_order in enumerate(response.orders):
        assert resp_order.orderId == expected_orders[i]["orderId"]
