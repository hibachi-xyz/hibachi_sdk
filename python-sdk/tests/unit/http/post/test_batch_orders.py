import pytest

from hibachi_xyz.types import (
    CancelOrderBatchResponse,
    CreateOrder,
    CreateOrderBatchResponse,
    ErrorBatchResponse,
    Side,
    UpdateOrderBatchResponse,
)
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

    # Only the first order triggers exchange_info (sets self.future_contracts)
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=exchange_info,
            call_validation=lambda call: call.function_name == "send_simple_request"
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


PARTIAL_FAILURE_BODY = {
    "orders": [
        {
            "creationTime": "1759980307",
            "creationTimeNsPartial": "428876960",
            "nonce": 1759980307080646,
            "orderId": "591118037937030144",
        },
        {
            "creationTime": "1759980307",
            "creationTimeNsPartial": "429106431",
            "nonce": 1759980307080647,
            "orderId": "591118037937030145",
        },
        {
            "creationTime": "1759980307",
            "creationTimeNsPartial": "429293390",
            "nonce": 1759980307080648,
            "orderId": "591118037937292288",
        },
        {
            "creationTime": "1759980307",
            "creationTimeNsPartial": "429479200",
            "nonce": 1759980307080649,
            "orderId": "591118037937292289",
        },
        {
            "creationTime": "1759980307",
            "creationTimeNsPartial": "429665772",
            "nonce": 1759980307080650,
            "orderId": "591118037937292290",
        },
        {
            "creationTime": "1759980307",
            "creationTimeNsPartial": "429847582",
            "nonce": 1759980307080651,
            "orderId": "591118037937292291",
        },
        {
            "creationTime": "1759980307",
            "creationTimeNsPartial": "430039963",
            "nonce": 1759980307080652,
            "orderId": "591118037937292292",
        },
        {
            "creationTime": "1759980307",
            "creationTimeNsPartial": "430220905",
            "nonce": 1759980307080653,
            "orderId": "591118037937554432",
        },
        {
            "creationTime": "1759980307",
            "creationTimeNsPartial": "430397570",
            "nonce": 1759980307080654,
            "orderId": "591118037937554433",
        },
        {
            "creationTime": "1759980307",
            "creationTimeNsPartial": "430580537",
            "nonce": 1759980307080655,
            "orderId": "591118037937554434",
        },
        {
            "errorCode": 3,
            "message": "Not found: Order ID 591118037823521792",
            "status": "failed",
        },
        {"orderId": "591118037857076224"},
        {"orderId": "591118037892203520"},
        {
            "errorCode": 4,
            "message": "Order 591118037823521792 was rejected",
            "status": "failed",
        },
        {"nonce": "1759980306943096"},
    ]
}


def test_partial_failure(mock_http_client):
    client, mock_http = mock_http_client

    # Save expected values before the API call (PARTIAL_FAILURE_BODY will be mutated)
    expected_create_orders = [
        {
            "nonce": 1759980307080646 + i,
            "orderId": PARTIAL_FAILURE_BODY["orders"][i]["orderId"],
            "creationTime": "1759980307",
            "creationTimeNsPartial": PARTIAL_FAILURE_BODY["orders"][i][
                "creationTimeNsPartial"
            ],
        }
        for i in range(10)
    ]

    # Extract payloads
    # Mock send_authorized_request call for batch
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=PARTIAL_FAILURE_BODY,
        )
    )
    response = client.batch_orders(
        []  # no need for input this is not going to a server
    )

    # Verify we have the expected number of responses
    assert len(response.orders) == 15

    # First 10 should be CreateOrderBatchResponse (indices 0-9)
    for i in range(10):
        order = response.orders[i]
        expected = expected_create_orders[i]
        assert isinstance(order, CreateOrderBatchResponse)
        assert hasattr(order, "nonce")
        assert hasattr(order, "orderId")
        assert hasattr(order, "creationTime")
        assert hasattr(order, "creationTimeNsPartial")
        assert order.nonce == expected["nonce"]
        assert order.orderId == expected["orderId"]
        assert order.creationTime == expected["creationTime"]
        assert order.creationTimeNsPartial == expected["creationTimeNsPartial"]

    # Index 10: ErrorBatchResponse
    error_order = response.orders[10]
    assert isinstance(error_order, ErrorBatchResponse)
    assert hasattr(error_order, "errorCode")
    assert hasattr(error_order, "message")
    assert hasattr(error_order, "status")
    assert error_order.errorCode == 3
    assert error_order.message == "Not found: Order ID 591118037823521792"
    assert error_order.status == "failed"

    # Indices 11-12: UpdateOrderBatchResponse
    update_order_ids = ["591118037857076224", "591118037892203520"]
    for i, expected_order_id in enumerate(update_order_ids, start=11):
        order = response.orders[i]
        assert isinstance(order, UpdateOrderBatchResponse)
        assert hasattr(order, "orderId")
        assert order.orderId == expected_order_id

    # Index 13: ErrorBatchResponse
    error_order = response.orders[13]
    assert isinstance(error_order, ErrorBatchResponse)
    assert hasattr(error_order, "errorCode")
    assert hasattr(error_order, "message")
    assert hasattr(error_order, "status")
    assert error_order.errorCode == 4
    assert error_order.message == "Order 591118037823521792 was rejected"
    assert error_order.status == "failed"

    # Index 14: CancelOrderBatchResponse
    cancel_order = response.orders[14]
    assert isinstance(cancel_order, CancelOrderBatchResponse)
    assert hasattr(cancel_order, "nonce")
    assert cancel_order.nonce == "1759980306943096"
