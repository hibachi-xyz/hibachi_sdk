import pytest

from hibachi_xyz.errors import ValidationError
from hibachi_xyz.executors.interface import HttpResponse
from hibachi_xyz.types import FutureContract, OrderType, Side
from tests.mock_executors import MockSuccessfulOutput
from tests.unit.conftest import load_json_all_cases


@pytest.mark.parametrize("test_data", load_json_all_cases("test.update_order"))
def test_update_order(mock_http_client, test_data):
    payload, path = test_data
    client, mock_http = mock_http_client

    # Extract payloads
    exchange_info = payload["response.exchange_info"]
    order_details = payload["response.order_details"]
    update_response = payload["response.update"]

    # Extract test parameters
    order_id = update_response["orderId"]
    max_fees_percent = update_response["maxFeesPercent"]
    quantity = update_response.get("quantity")
    price = update_response.get("price")

    # Mock get_order_details call
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=200, body=order_details),
            call_validation=lambda call: call.function_name == "send_authorized_request"
            and call.arg_pack[0] == "GET"
            and "/trade/order" in call.arg_pack[1],
        )
    )

    # Mock exchange_info call (needed for __get_contract)
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=200, body=exchange_info),
            call_validation=lambda call: call.function_name == "send_simple_request"
            and call.arg_pack == ("/market/exchange-info",),
        )
    )

    # Mock send_authorized_request call for update
    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=200, body=update_response),
            call_validation=lambda call: call.function_name == "send_authorized_request"
            and call.arg_pack[0:2] == ("PUT", "/trade/order")
            and call.arg_pack[2] is not None,
        )
    )

    response = client.update_order(
        order_id, max_fees_percent, quantity=quantity, price=price
    )

    # Assertions
    assert response["orderId"] == update_response["orderId"]


def test_update_order_market_order_with_price(mock_http_client):
    """Test that updating a market order with a price raises ValidationError."""
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

    # Mock get_order_details to return a market order
    order_details_body = {
        "accountId": 123,
        "availableQuantity": "0.001",
        "orderId": "12345",
        "orderType": OrderType.MARKET.value,
        "side": Side.BID.value,
        "status": "PENDING",
        "symbol": symbol,
        "price": None,
        "totalQuantity": "0.001",
        "triggerPrice": None,
    }

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=200, body=order_details_body),
            call_validation=lambda call: call.function_name == "send_authorized_request"
            and call.arg_pack[0] == "GET",
        )
    )

    with pytest.raises(ValidationError):
        client.update_order(order_id=12345, max_fees_percent=0.001, price=50000)


def test_update_order_add_trigger_price_to_non_trigger_order(mock_http_client):
    """Test that adding trigger_price to a non-trigger order raises ValidationError."""
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

    # Create a limit order without trigger
    order_details_body = {
        "accountId": 123,
        "availableQuantity": "0.001",
        "orderId": "12345",
        "orderType": OrderType.LIMIT.value,
        "side": Side.BID.value,
        "status": "PENDING",
        "symbol": symbol,
        "price": "50000",
        "totalQuantity": "0.001",
        "triggerPrice": None,
    }

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=200, body=order_details_body),
            call_validation=lambda call: call.function_name == "send_authorized_request"
            and call.arg_pack[0] == "GET",
        )
    )

    with pytest.raises(ValidationError):
        client.update_order(order_id=12345, max_fees_percent=0.001, trigger_price=51000)
