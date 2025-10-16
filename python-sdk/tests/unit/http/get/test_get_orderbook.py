import copy

import pytest

from hibachi_xyz.errors import DeserializationError, ValidationError
from hibachi_xyz.executors.interface import HttpResponse
from hibachi_xyz.types import FutureContract
from tests.mock_executors import MockSuccessfulOutput
from tests.unit.conftest import load_json_all_cases


@pytest.mark.parametrize("test_data", load_json_all_cases("response.orderbook"))
def test_get_orderbook(mock_http_client, test_data):
    payload, path = test_data
    client, mock_http = mock_http_client

    # Save original nested structures before they get mutated
    original_ask = copy.deepcopy(payload["ask"])
    original_bid = copy.deepcopy(payload["bid"])

    symbol = "ETH/USDT-P"
    depth = 10
    granularity = 0.1

    # Pre-populate future_contracts to avoid get_exchange_info call
    client._future_contracts = {
        symbol: FutureContract(
            displayName="ETH/USDT Perps",
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
            underlyingDecimals=9,
            underlyingSymbol="ETH",
        )
    }

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=200, body=payload),
            call_validation=lambda call: call.function_name == "send_simple_request"
            and call.arg_pack
            == (
                f"/market/data/orderbook?symbol={symbol}&depth={depth}&granularity={granularity}",
            ),
        )
    )

    orderbook = client.get_orderbook(symbol, depth, granularity)

    # Ask levels assertions
    assert len(orderbook.ask) == len(original_ask["levels"])
    for level, orig_level in zip(orderbook.ask, original_ask["levels"]):
        assert level.price == orig_level["price"]
        assert level.quantity == orig_level["quantity"]

    # Bid levels assertions
    assert len(orderbook.bid) == len(original_bid["levels"])
    for level, orig_level in zip(orderbook.bid, original_bid["levels"]):
        assert level.price == orig_level["price"]
        assert level.quantity == orig_level["quantity"]


def test_get_orderbook_invalid_depth_too_small(mock_http_client):
    """Test that depth < 1 raises ValidationError."""
    client, mock_http = mock_http_client

    symbol = "ETH/USDT-P"
    client._future_contracts = {
        symbol: FutureContract(
            displayName="ETH/USDT Perps",
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
            underlyingDecimals=9,
            underlyingSymbol="ETH",
        )
    }

    with pytest.raises(ValidationError) as exc_info:
        client.get_orderbook(symbol, depth=0, granularity=0.1)

    assert "must be a positive integer between 1 and 100" in str(exc_info.value)


def test_get_orderbook_invalid_depth_too_large(mock_http_client):
    """Test that depth > 100 raises ValidationError."""
    client, mock_http = mock_http_client

    symbol = "ETH/USDT-P"
    client._future_contracts = {
        symbol: FutureContract(
            displayName="ETH/USDT Perps",
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
            underlyingDecimals=9,
            underlyingSymbol="ETH",
        )
    }

    with pytest.raises(ValidationError) as exc_info:
        client.get_orderbook(symbol, depth=101, granularity=0.1)

    assert "must be a positive integer between 1 and 100" in str(exc_info.value)


def test_get_orderbook_invalid_granularity(mock_http_client):
    """Test that invalid granularity raises ValidationError."""
    client, mock_http = mock_http_client

    symbol = "ETH/USDT-P"
    client._future_contracts = {
        symbol: FutureContract(
            displayName="ETH/USDT Perps",
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
            underlyingDecimals=9,
            underlyingSymbol="ETH",
        )
    }

    with pytest.raises(ValidationError) as exc_info:
        client.get_orderbook(symbol, depth=10, granularity=0.5)

    assert "Granularity for symbol ETH/USDT-P must be one of" in str(exc_info.value)


def test_get_orderbook_deserialization_error(mock_http_client):
    """Test that malformed response raises DeserializationError."""
    client, mock_http = mock_http_client

    symbol = "ETH/USDT-P"
    client._future_contracts = {
        symbol: FutureContract(
            displayName="ETH/USDT Perps",
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
            underlyingDecimals=9,
            underlyingSymbol="ETH",
        )
    }

    # Malformed response missing required fields
    malformed_payload = {"ask": "not a dict", "bid": {}}

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=200, body=malformed_payload),
            call_validation=lambda call: call.function_name == "send_simple_request",
        )
    )

    with pytest.raises(DeserializationError) as exc_info:
        client.get_orderbook(symbol, depth=10, granularity=0.1)

    assert "Received invalid response" in str(exc_info.value)
