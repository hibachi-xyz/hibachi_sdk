from typing import Any, override

import requests

from hibachi_xyz.errors import (
    BaseError,
    DeserializationError,
    ExchangeError,
    HttpConnectionError,
    MissingCredentialsError,
    TransportError,
    TransportTimeoutError,
)
from hibachi_xyz.executors.interface import HttpExecutor
from hibachi_xyz.helpers import (
    DEFAULT_API_URL,
    DEFAULT_DATA_API_URL,
    get_hibachi_client,
)
from hibachi_xyz.types import Json


def _get_http_error(response: requests.Response) -> ExchangeError | None:
    """Check if the response is an error and return an exception if it is
    The builtin response.raise_for_status() does not show the server's response
    """

    if response.status_code > 299:
        return ExchangeError(f"HTTP {response.status_code}: {response.text}")
    return None


class RequestsHttpExecutor(HttpExecutor):
    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        data_api_url: str = DEFAULT_DATA_API_URL,
        api_key: str | None = None,
    ):
        self.api_url = api_url
        self.data_api_url = data_api_url
        self.api_key = api_key

    @override
    def send_simple_request(self, path: str) -> Json:
        url = f"{self.data_api_url}{path}"
        try:
            response = requests.get(
                url,
                headers={"Hibachi-Client": get_hibachi_client()},
            )
            error = _get_http_error(response)
            if error is not None:
                raise error
            return response.json()
        except BaseError:
            raise
        except requests.Timeout as e:
            raise TransportTimeoutError(
                f"Request to {url} timed out", timeout_seconds=None
            ) from e
        except requests.ConnectionError as e:
            raise HttpConnectionError(f"Failed to connect to {url}", url=url) from e
        except (ValueError, TypeError) as e:
            raise DeserializationError(
                f"Failed to parse JSON response from {url}: {e}"
            ) from e
        except Exception as e:
            raise TransportError(f"Request to {url} failed: {e}") from e

    @override
    def send_authorized_request(
        self, method: str, path: str, json: Json | None = None
    ) -> Any:
        url = f"{self.api_url}{path}"
        try:
            headers = {
                "Authorization": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Hibachi-Client": get_hibachi_client(),
            }

            response = requests.request(method, url, headers=headers, json=json)
            error = _get_http_error(response)
            if error is not None:
                raise error

            return response.json()
        except BaseError:
            raise
        except requests.Timeout as e:
            raise TransportTimeoutError(
                f"{method} request to {url} timed out", timeout_seconds=None
            ) from e
        except requests.ConnectionError as e:
            raise HttpConnectionError(f"Failed to connect to {url}", url=url) from e
        except (ValueError, TypeError) as e:
            raise DeserializationError(
                f"Failed to parse JSON response from {url}: {e}"
            ) from e
        except Exception as e:
            raise TransportError(f"{method} request to {url} failed: {e}") from e

    @override
    def check_auth_data(self) -> None:
        if self.api_key is None:
            raise MissingCredentialsError("API key")
