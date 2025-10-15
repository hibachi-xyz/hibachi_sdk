from abc import ABC, abstractmethod
from typing import Any

from hibachi_xyz.types import JsonObject


class HttpResponse:
    status: int
    body: JsonObject
    headers: dict[str, str] | None

    __slots__ = ("status", "body", "headers")

    def __init__(
        self,
        *,
        status: int,
        body: JsonObject | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self.body = body if body is not None else {}
        self.headers = headers


class HttpExecutor(ABC):
    api_key: str | None = None

    @abstractmethod
    def send_authorized_request(
        self,
        method: str,
        path: str,
        json: Any | None = None,
    ) -> HttpResponse: ...

    @abstractmethod
    def send_simple_request(
        self,
        path: str,
    ) -> HttpResponse: ...


class WsConnection(ABC):
    @abstractmethod
    async def send(
        self,
        serialized_body: str,
    ) -> None: ...

    @abstractmethod
    async def recv(self) -> str: ...

    @abstractmethod
    async def close(self) -> None: ...


class WsExecutor(ABC):
    @abstractmethod
    async def connect(
        self,
        web_url: str,
        headers: dict[str, str] | None = None,
    ) -> WsConnection: ...
