"""HTTP executor implementation using httpx.

This module provides HTTP request handling using the httpx library,
supporting both sync and async operations for the Hibachi SDK.
"""

from typing import override

import httpx

from hibachi_xyz.errors import (
    BaseError,
    ExchangeError,
    HttpConnectionError,
    TransportError,
    TransportTimeoutError,
    ValidationError,
)
from hibachi_xyz.executors.interface import HttpExecutor, HttpResponse
from hibachi_xyz.helpers import (
    DEFAULT_API_URL,
    DEFAULT_DATA_API_URL,
    deserialize_response,
    get_hibachi_client,
    serialize_request,
)
from hibachi_xyz.types import Json


class HttpxHttpExecutor(HttpExecutor):
    """HTTP executor implementation using httpx.

    Provides synchronous HTTP request execution using the httpx library.
    """

    @override
    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        data_api_url: str = DEFAULT_DATA_API_URL,
        api_key: str | None = None,
    ):
        """Initialize the HTTPX HTTP executor.

        Args:
            api_url: The base URL for the Hibachi API. Defaults to DEFAULT_API_URL.
            data_api_url: The base URL for the Hibachi Data API. Defaults to DEFAULT_DATA_API_URL.
            api_key: Optional API key for authenticated requests. If not provided,
                authorized requests will fail with a ValidationError.

        """
        self.api_url = api_url
        self.data_api_url = data_api_url
        self.api_key = api_key
        self.client = httpx.Client()

    @override
    def send_simple_request(self, path: str) -> HttpResponse:
        """Send a simple unauthenticated GET request to the Data API.

        Args:
            path: The API endpoint path to request (will be appended to data_api_url).

        Returns:
            HttpResponse containing the status code and deserialized response body.

        Raises:
            TransportTimeoutError: If the request times out.
            HttpConnectionError: If there is a connection or network error.
            TransportError: If any other transport-level error occurs.

        """
        url = f"{self.data_api_url}{path}"
        try:
            response = self.client.get(
                url,
                headers={"Hibachi-Client": get_hibachi_client()},
            )
        except BaseError:
            raise
        except httpx.TimeoutException as e:
            # TODO better timeout
            raise TransportTimeoutError(
                f"Request to {url} timed out", timeout_seconds=None
            ) from e
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            raise HttpConnectionError(f"Failed to connect to {url}", url=url) from e
        except httpx.NetworkError as e:
            raise HttpConnectionError(
                f"Network error during request to {url}", url=url
            ) from e
        except Exception as e:
            raise TransportError(f"Request to {url} failed: {e}") from e
        return HttpResponse(
            status=response.status_code,
            body=deserialize_response(response.content, url),
        )

    @override
    def send_authorized_request(
        self,
        method: str,
        path: str,
        json: Json | None = None,
    ) -> HttpResponse:
        """Send an authenticated request to the API.

        Args:
            method: The HTTP method to use (e.g., 'GET', 'POST', 'PUT', 'DELETE').
            path: The API endpoint path to request (will be appended to api_url).
            json: Optional JSON data to include in the request body. Defaults to None.

        Returns:
            HttpResponse containing the status code and deserialized response body.

        Raises:
            ValidationError: If the api_key is not set.
            TransportTimeoutError: If the request times out.
            HttpConnectionError: If there is a connection or network error.
            TransportError: If any other transport-level error occurs.
            ExchangeError: If an exchange-specific error occurs (re-raised).

        """
        if self.api_key is None:
            raise ValidationError("api_key is not set")

        url = f"{self.api_url}{path}"
        request_body = serialize_request(json)
        try:
            headers = {
                "Authorization": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Hibachi-Client": get_hibachi_client(),
            }

            response = self.client.request(
                method, url, headers=headers, content=request_body
            )

        except ExchangeError:
            raise
        except httpx.TimeoutException as e:
            raise TransportTimeoutError(
                f"{method} request to {url} timed out", timeout_seconds=None
            ) from e
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            raise HttpConnectionError(f"Failed to connect to {url}", url=url) from e
        except httpx.NetworkError as e:
            raise HttpConnectionError(
                f"Network error during {method} request to {url}", url=url
            ) from e
        except Exception as e:
            raise TransportError(f"{method} request to {url} failed: {e}") from e
        return HttpResponse(
            status=response.status_code,
            body=deserialize_response(response.content, url),
        )

    def __del__(self) -> None:
        """Cleanup the httpx client when the executor is destroyed."""
        self.client.close()
