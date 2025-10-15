"""HTTP executor implementation using requests.

This module provides HTTP request handling using the popular requests library,
serving as the default HTTP executor for the Hibachi SDK.
"""

from typing import override

import requests

from hibachi_xyz.errors import (
    BaseError,
    HttpConnectionError,
    TransportError,
    TransportTimeoutError,
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


class RequestsHttpExecutor(HttpExecutor):
    """HTTP executor implementation using requests.

    Provides synchronous HTTP request execution using the requests library.
    """

    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        data_api_url: str = DEFAULT_DATA_API_URL,
        api_key: str | None = None,
    ):
        """Initialize the RequestsHttpExecutor with API configuration.

        Args:
            api_url: The base URL for authenticated API requests. Defaults to DEFAULT_API_URL.
            data_api_url: The base URL for unauthenticated data API requests. Defaults to DEFAULT_DATA_API_URL.
            api_key: The API key for authenticated requests. Optional.

        """
        self.api_url = api_url
        self.data_api_url = data_api_url
        self.api_key = api_key

    @override
    def send_simple_request(self, path: str) -> HttpResponse:
        """Send an unauthenticated GET request to the data API.

        Args:
            path: The API endpoint path to append to the data API URL.

        Returns:
            HttpResponse containing the status code and deserialized response body.

        Raises:
            TransportTimeoutError: If the request times out.
            HttpConnectionError: If the connection to the server fails.
            TransportError: If any other transport-level error occurs.

        """
        url = f"{self.data_api_url}{path}"
        try:
            response = requests.get(
                url,
                headers={"Hibachi-Client": get_hibachi_client()},
            )
        except BaseError:
            raise
        except requests.Timeout as e:
            raise TransportTimeoutError(
                f"Request to {url} timed out", timeout_seconds=None
            ) from e
        except requests.ConnectionError as e:
            raise HttpConnectionError(f"Failed to connect to {url}", url=url) from e
        except Exception as e:
            raise TransportError(f"Request to {url} failed: {e}") from e
        return HttpResponse(
            status=response.status_code,
            body=deserialize_response(response.content, url),
        )

    @override
    def send_authorized_request(
        self, method: str, path: str, json: Json | None = None
    ) -> HttpResponse:
        """Send an authenticated HTTP request to the API.

        Args:
            method: The HTTP method to use (e.g., GET, POST, PUT, DELETE).
            path: The API endpoint path to append to the API URL.
            json: Optional JSON payload to send with the request.

        Returns:
            HttpResponse containing the status code and deserialized response body.

        Raises:
            TransportTimeoutError: If the request times out.
            HttpConnectionError: If the connection to the server fails.
            TransportError: If any other transport-level error occurs.

        """
        url = f"{self.api_url}{path}"
        request_body = serialize_request(json)
        try:
            headers = {
                "Authorization": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Hibachi-Client": get_hibachi_client(),
            }

            response = requests.request(method, url, headers=headers, data=request_body)
        except BaseError:
            raise
        except requests.Timeout as e:
            raise TransportTimeoutError(
                f"{method} request to {url} timed out", timeout_seconds=None
            ) from e
        except requests.ConnectionError as e:
            raise HttpConnectionError(f"Failed to connect to {url}", url=url) from e
        except Exception as e:
            raise TransportError(f"{method} request to {url} failed: {e}") from e
        return HttpResponse(
            status=response.status_code,
            body=deserialize_response(response.content, url),
        )
