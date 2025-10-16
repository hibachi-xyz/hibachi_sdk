from typing import Type

from hibachi_xyz.executors.interface import HttpExecutor, WsExecutor
from hibachi_xyz.executors.requests import RequestsHttpExecutor
from hibachi_xyz.executors.websockets import WebsocketsWsExecutor

DEFAULT_WS_EXECUTOR: Type[WsExecutor] = WebsocketsWsExecutor
DEFAULT_HTTP_EXECUTOR: Type[HttpExecutor] = RequestsHttpExecutor
