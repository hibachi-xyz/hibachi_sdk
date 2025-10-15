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
    def send_simple_request(self, path: str) -> HttpResponse:
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
