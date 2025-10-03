from abc import ABC, abstractmethod
from typing import Any
from hibachi_xyz.types import Json


class HttpExecutor(ABC):
    @abstractmethod
    def send_authorized_request(
        self,
        method: str,
        path: str,
        json: Any | None = None,
    ) -> Any: ...

    @abstractmethod
    def send_simple_request(
        self,
        path: str,
    ) -> Json: ...

    @abstractmethod
    def check_auth_data(self) -> None: ...


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
