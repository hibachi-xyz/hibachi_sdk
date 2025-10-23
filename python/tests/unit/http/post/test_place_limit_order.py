import pytest

from hibachi_xyz.errors import DeserializationError
from hibachi_xyz.executors.interface import HttpResponse
from hibachi_xyz.types import FutureContract, Side
from tests.mock_executors import MockSuccessfulOutput
from tests.unit.conftest import load_json_all_cases


@pytest.mark.parametrize("test_data", load_json_all_cases("test.place_limit_order"))
def test_place_limit_order(mock_http_client, test_data):
    payload, path = test_data
    client, mock_http = mock_http_client

    # Extract payloads
    exchange_info = payload["response.exchange_info"]
    order_response = payload["response.order"]

    # Extract test parameters from order response
    symbol = order_response["symbol"]
    quantity = order_response["quantity"]
    price = order_response["price"]
    side = Side(order_response["side"])
    max_fees_percent = order_response["maxFeesPercent"]

    # Mock exchange_info call (needed for __get_contract in place_limit_order)
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=200, body=exchange_info),
            call_validation=lambda call: call.function_name == "send_simple_request"
            and call.arg_pack == ("/market/exchange-info",),
        )
    )

    # Mock send_authorized_request call for order placement
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=200, body=order_response),
            call_validation=lambda call: call.function_name == "send_authorized_request"
            and call.arg_pack[0:2] == ("POST", "/trade/order")
            and call.arg_pack[2] is not None,
        )
    )

    nonce, order_id = client.place_limit_order(
        symbol, quantity, price, side, max_fees_percent
    )

    # Assertions
    assert order_id == order_response["orderId"]


def test_place_limit_order_deserialization_error(mock_http_client):
    """Test that malformed response raises DeserializationError."""
    client, mock_http = mock_http_client

    symbol = "BTC/USDT-P"
    client._future_contracts = {
        symbol: FutureContract(
            displayName="BTC/USDT Perps",
            id=1,
            initialMarginRate="0.066667",
            maintenanceMarginRate="0.046667",
            marketCloseTimestamp=None,
            marketCreationTimestamp="1727701319.73488",
            marketOpenTimestamp=None,
            minNotional="1",
            minOrderSize="0.000000001",
            orderbookGranularities=["0.01", "0.1", "1"],
            settlementDecimals=6,
            settlementSymbol="USDT",
            status="LIVE",
            stepSize="0.000000001",
            symbol=symbol,
            tickSize="0.000001",
            underlyingDecimals=8,
            underlyingSymbol="BTC",
        )
    }

    # Malformed response with orderId as a non-numeric string
    malformed_payload = {
        "orderId": "not_a_number",
    }

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=200, body=malformed_payload),
            call_validation=lambda call: call.function_name == "send_authorized_request"
            and call.arg_pack[0:2] == ("POST", "/trade/order"),
        )
    )

    with pytest.raises(DeserializationError) as exc_info:
        client.place_limit_order(
            symbol=symbol,
            quantity=0.001,
            price=50000,
            side=Side.BUY,
            max_fees_percent=0.001,
        )

    assert "Received invalid" in str(exc_info.value)
