"""HTTP and WebSocket executor implementations.

This package provides pluggable HTTP and WebSocket client implementations
for the Hibachi SDK, supporting multiple underlying libraries like requests,
httpx, websockets, and aiohttp.
"""

from hibachi_xyz.executors.aiohttp import AiohttpWsExecutor
from hibachi_xyz.executors.defaults import DEFAULT_HTTP_EXECUTOR, DEFAULT_WS_EXECUTOR
from hibachi_xyz.executors.httpx import HttpxHttpExecutor
from hibachi_xyz.executors.interface import HttpExecutor, WsConnection, WsExecutor
from hibachi_xyz.executors.requests import RequestsHttpExecutor
from hibachi_xyz.executors.websockets import WebsocketsWsExecutor

__all__ = [
    "HttpExecutor",
    "HttpxHttpExecutor",
    "RequestsHttpExecutor",
    "WsConnection",
    "WsExecutor",
    "WebsocketsWsExecutor",
    "AiohttpWsExecutor",
    "DEFAULT_HTTP_EXECUTOR",
    "DEFAULT_WS_EXECUTOR",
]
