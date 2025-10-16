"""Default executor configurations.

This module defines the default HTTP and WebSocket executor implementations
used by the Hibachi SDK when no custom executor is provided.
"""

from typing import Type

from hibachi_xyz.executors.aiohttp import AiohttpWsExecutor
from hibachi_xyz.executors.httpx import HttpxHttpExecutor
from hibachi_xyz.executors.interface import HttpExecutor, WsExecutor

DEFAULT_WS_EXECUTOR: Type[WsExecutor] = AiohttpWsExecutor
DEFAULT_HTTP_EXECUTOR: Type[HttpExecutor] = HttpxHttpExecutor
