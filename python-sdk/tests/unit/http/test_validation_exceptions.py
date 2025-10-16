"""Tests for validation exceptions in the API client."""

import pytest

from hibachi_xyz import HibachiApiClient
from hibachi_xyz.errors import ValidationError
from tests.mock_executors import MockHttpExecutor


def test_account_id_property_not_set():
    """Test that accessing account_id when not set raises ValidationError."""
    mock_http = MockHttpExecutor()
    client = HibachiApiClient(executor=mock_http)

    with pytest.raises(ValidationError) as exc_info:
        _ = client.account_id

    assert "account_id has not been set" in str(exc_info.value)


def test_api_key_property_not_set():
    """Test that accessing api_key when not set raises ValidationError."""
    mock_http = MockHttpExecutor()
    client = HibachiApiClient(executor=mock_http)

    with pytest.raises(ValidationError) as exc_info:
        _ = client.api_key

    assert "api_key has not been set" in str(exc_info.value)


def test_future_contracts_property_not_loaded():
    """Test that accessing future_contracts when not loaded raises ValidationError."""
    mock_http = MockHttpExecutor()
    client = HibachiApiClient(executor=mock_http)

    with pytest.raises(ValidationError) as exc_info:
        _ = client.future_contracts

    assert "future_contracts not yet loaded" in str(exc_info.value)


def test_set_account_id_invalid_string():
    """Test that setting account_id with invalid string raises ValidationError."""
    mock_http = MockHttpExecutor()
    client = HibachiApiClient(executor=mock_http)

    with pytest.raises(ValidationError) as exc_info:
        client.set_account_id("not_a_number")

    assert "Invalid" in str(exc_info.value)


def test_set_account_id_invalid_type():
    """Test that setting account_id with invalid type raises ValidationError."""
    mock_http = MockHttpExecutor()
    client = HibachiApiClient(executor=mock_http)

    with pytest.raises(ValidationError):
        client.set_account_id([123])  # type: ignore


def test_set_account_id_valid_string():
    """Test that setting account_id with valid numeric string works."""
    mock_http = MockHttpExecutor()
    client = HibachiApiClient(executor=mock_http)

    client.set_account_id("12345")
    assert client.account_id == 12345


def test_set_account_id_valid_int():
    """Test that setting account_id with valid int works."""
    mock_http = MockHttpExecutor()
    client = HibachiApiClient(executor=mock_http)

    client.set_account_id(12345)
    assert client.account_id == 12345


def test_set_account_id_none():
    """Test that setting account_id to None works."""
    mock_http = MockHttpExecutor()
    client = HibachiApiClient(executor=mock_http, account_id=12345)

    client.set_account_id(None)

    with pytest.raises(ValidationError):
        _ = client.account_id


def test_set_api_key_invalid_type():
    """Test that setting api_key with invalid type raises ValidationError."""
    mock_http = MockHttpExecutor()
    client = HibachiApiClient(executor=mock_http)

    with pytest.raises(ValidationError):
        client.set_api_key(12345)  # type: ignore


def test_set_api_key_valid_string():
    """Test that setting api_key with valid string works."""
    mock_http = MockHttpExecutor()
    client = HibachiApiClient(executor=mock_http)

    client.set_api_key("test_api_key")
    assert client.api_key == "test_api_key"


def test_set_api_key_none():
    """Test that setting api_key to None works."""
    mock_http = MockHttpExecutor()
    client = HibachiApiClient(executor=mock_http, api_key="test")

    client.set_api_key(None)

    with pytest.raises(ValidationError):
        _ = client.api_key
