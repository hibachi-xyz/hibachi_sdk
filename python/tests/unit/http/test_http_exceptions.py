"""Tests for HTTP exception handling in the API client."""

import pytest

from hibachi_xyz.errors import (
    BadGateway,
    BadHttpStatus,
    BadRequest,
    Forbidden,
    GatewayTimeout,
    InternalServerError,
    NotFound,
    RateLimited,
    ServiceUnavailable,
    Unauthorized,
)
from hibachi_xyz.executors.interface import HttpResponse
from tests.mock_executors import MockSuccessfulOutput


def test_400_bad_request(mock_http_client):
    """Test that 400 status raises BadRequest exception."""
    client, mock_http = mock_http_client

    error_body = {
        "errorCode": "INVALID_PARAM",
        "status": "error",
        "message": "Invalid parameter value",
    }

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=400, body=error_body),
            call_validation=lambda call: call.function_name == "send_simple_request",
        )
    )

    with pytest.raises(BadRequest) as exc_info:
        client.get_exchange_info()

    assert exc_info.value.status_code == 400
    assert "INVALID_PARAM" in exc_info.value.message
    assert "Invalid parameter value" in exc_info.value.message


def test_401_unauthorized(mock_http_client):
    """Test that 401 status raises Unauthorized exception."""
    client, mock_http = mock_http_client

    error_body = {
        "errorCode": "AUTH_FAILED",
        "status": "error",
        "message": "Invalid API key",
    }

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=401, body=error_body),
            call_validation=lambda call: call.function_name
            == "send_authorized_request",
        )
    )

    with pytest.raises(Unauthorized) as exc_info:
        client.get_account_info()

    assert exc_info.value.status_code == 401
    assert "AUTH_FAILED" in exc_info.value.message
    assert "Invalid API key" in exc_info.value.message


def test_403_forbidden(mock_http_client):
    """Test that 403 status raises Forbidden exception."""
    client, mock_http = mock_http_client

    error_body = {
        "errorCode": "FORBIDDEN",
        "status": "error",
        "message": "Insufficient permissions",
    }

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=403, body=error_body),
            call_validation=lambda call: call.function_name
            == "send_authorized_request",
        )
    )

    with pytest.raises(Forbidden) as exc_info:
        client.get_account_info()

    assert exc_info.value.status_code == 403
    assert "FORBIDDEN" in exc_info.value.message
    assert "Insufficient permissions" in exc_info.value.message


def test_404_not_found(mock_http_client):
    """Test that 404 status raises NotFound exception."""
    client, mock_http = mock_http_client

    error_body = {
        "errorCode": "NOT_FOUND",
        "status": "error",
        "message": "Resource not found",
    }

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=404, body=error_body),
            call_validation=lambda call: call.function_name == "send_simple_request",
        )
    )

    with pytest.raises(NotFound) as exc_info:
        client.get_exchange_info()

    assert exc_info.value.status_code == 404
    assert "NOT_FOUND" in exc_info.value.message
    assert "Resource not found" in exc_info.value.message


def test_429_rate_limited_with_details(mock_http_client):
    """Test that 429 status raises RateLimited with detailed info."""
    client, mock_http = mock_http_client

    error_body = {
        "name": "order_placement",
        "count": 150,
        "limit": 100,
        "windowDuration": "60s",
    }

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=429, body=error_body),
            call_validation=lambda call: call.function_name
            == "send_authorized_request",
        )
    )

    with pytest.raises(RateLimited) as exc_info:
        client.get_account_info()

    assert exc_info.value.status_code == 429
    assert "order_placement" in exc_info.value.message
    assert "150/100" in exc_info.value.message
    assert "60s" in exc_info.value.message


def test_429_rate_limited_without_details(mock_http_client):
    """Test that 429 status raises RateLimited with generic message."""
    client, mock_http = mock_http_client

    error_body = {
        "errorCode": "RATE_LIMIT",
        "status": "error",
        "message": "Too many requests",
    }

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=429, body=error_body),
            call_validation=lambda call: call.function_name
            == "send_authorized_request",
        )
    )

    with pytest.raises(RateLimited) as exc_info:
        client.get_account_info()

    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.message


def test_4xx_generic_client_error(mock_http_client):
    """Test that other 4XX status raises BadHttpStatus exception."""
    client, mock_http = mock_http_client

    error_body = {
        "errorCode": "CLIENT_ERROR",
        "status": "error",
        "message": "Generic client error",
    }

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=418, body=error_body),
            call_validation=lambda call: call.function_name == "send_simple_request",
        )
    )

    with pytest.raises(BadHttpStatus) as exc_info:
        client.get_exchange_info()

    assert exc_info.value.status_code == 418
    assert "Client error (418)" in exc_info.value.message
    assert "CLIENT_ERROR" in exc_info.value.message


def test_500_internal_server_error(mock_http_client):
    """Test that 500 status raises InternalServerError exception."""
    client, mock_http = mock_http_client

    error_body = {
        "errorCode": "SERVER_ERROR",
        "status": "error",
        "message": "Internal server error",
    }

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=500, body=error_body),
            call_validation=lambda call: call.function_name == "send_simple_request",
        )
    )

    with pytest.raises(InternalServerError) as exc_info:
        client.get_exchange_info()

    assert exc_info.value.status_code == 500
    assert "Internal server error" in exc_info.value.message


def test_502_bad_gateway(mock_http_client):
    """Test that 502 status raises BadGateway exception."""
    client, mock_http = mock_http_client

    error_body = {
        "errorCode": "BAD_GATEWAY",
        "status": "error",
        "message": "Bad gateway error",
    }

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=502, body=error_body),
            call_validation=lambda call: call.function_name == "send_simple_request",
        )
    )

    with pytest.raises(BadGateway) as exc_info:
        client.get_exchange_info()

    assert exc_info.value.status_code == 502
    assert "Bad gateway" in exc_info.value.message


def test_503_service_unavailable(mock_http_client):
    """Test that 503 status raises ServiceUnavailable exception."""
    client, mock_http = mock_http_client

    error_body = {
        "errorCode": "UNAVAILABLE",
        "status": "error",
        "message": "Service temporarily unavailable",
    }

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=503, body=error_body),
            call_validation=lambda call: call.function_name == "send_simple_request",
        )
    )

    with pytest.raises(ServiceUnavailable) as exc_info:
        client.get_exchange_info()

    assert exc_info.value.status_code == 503
    assert "Service unavailable" in exc_info.value.message


def test_504_gateway_timeout(mock_http_client):
    """Test that 504 status raises GatewayTimeout exception."""
    client, mock_http = mock_http_client

    error_body = {
        "errorCode": "TIMEOUT",
        "status": "error",
        "message": "Gateway timeout",
    }

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=504, body=error_body),
            call_validation=lambda call: call.function_name == "send_simple_request",
        )
    )

    with pytest.raises(GatewayTimeout) as exc_info:
        client.get_exchange_info()

    assert exc_info.value.status_code == 504
    assert "Gateway timeout" in exc_info.value.message


def test_5xx_generic_server_error(mock_http_client):
    """Test that other 5XX status raises InternalServerError exception."""
    client, mock_http = mock_http_client

    error_body = {
        "errorCode": "SERVER_ERROR",
        "status": "error",
        "message": "Generic server error",
    }

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=599, body=error_body),
            call_validation=lambda call: call.function_name == "send_simple_request",
        )
    )

    with pytest.raises(InternalServerError) as exc_info:
        client.get_exchange_info()

    assert exc_info.value.status_code == 599
    assert "Server error (599)" in exc_info.value.message


def test_3xx_redirect_unexpected_status(mock_http_client):
    """Test that 3XX status raises BadHttpStatus exception."""
    client, mock_http = mock_http_client

    error_body = {}

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=301, body=error_body),
            call_validation=lambda call: call.function_name == "send_simple_request",
        )
    )

    with pytest.raises(BadHttpStatus) as exc_info:
        client.get_exchange_info()

    assert exc_info.value.status_code == 301
    assert "Unexpected status code (301)" in exc_info.value.message


def test_error_message_with_empty_body(mock_http_client):
    """Test error handling with empty response body."""
    client, mock_http = mock_http_client

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=400, body={}),
            call_validation=lambda call: call.function_name == "send_simple_request",
        )
    )

    with pytest.raises(BadRequest) as exc_info:
        client.get_exchange_info()

    assert exc_info.value.status_code == 400
    assert "<no error message>" in exc_info.value.message


def test_error_message_with_non_dict_body(mock_http_client):
    """Test error handling with non-dict response body."""
    client, mock_http = mock_http_client

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=HttpResponse(status=400, body="string error"),
            call_validation=lambda call: call.function_name == "send_simple_request",
        )
    )

    with pytest.raises(BadRequest) as exc_info:
        client.get_exchange_info()

    assert exc_info.value.status_code == 400
    assert "<no error message>" in exc_info.value.message
