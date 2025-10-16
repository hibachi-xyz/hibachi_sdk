"""Connection utilities for WebSocket connections."""

import asyncio
import logging

from hibachi_xyz.errors import TransportError, WebSocketConnectionError
from hibachi_xyz.executors.interface import WsConnection, WsExecutor

log = logging.getLogger(__name__)


async def connect_with_retry(
    web_url: str,
    headers: list[tuple[str, str]] | None = None,
    executor: WsExecutor | None = None,
    max_retries: int = 10,
    retry_delay: float = 1,
    backoff_factor: float = 1.5,
) -> WsConnection:
    """Establish WebSocket connection with exponential backoff retry logic.

    Attempts to connect up to max_retries times with exponentially increasing delays
    between attempts (starting at retry_delay seconds, doubling each time).

    Args:
        web_url: WebSocket URL to connect to
        headers: Optional list of header tuples to send
        executor: Optional WebSocket executor to use for connection
        max_retries: Maximum number of connection attempts (default: 10)
        retry_delay: Initial retry delay in seconds (default: 1)
        backoff_factor: Factor to increase retry_delay with each retry

    Returns:
        Established WebSocket connection

    Raises:
        Exception: If connection fails after all retry attempts

    """
    if executor is None:
        from hibachi_xyz.executors.defaults import DEFAULT_WS_EXECUTOR

        executor = DEFAULT_WS_EXECUTOR()

    retry_count = 0
    while retry_count < max_retries:
        try:
            # Convert headers list to dict for executor
            headers_dict = dict(headers) if headers else None
            websocket = await executor.connect(web_url, headers_dict)
            return websocket
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                raise WebSocketConnectionError(
                    f"Failed to connect after {max_retries} attempts: {str(e)}"
                )

            log.warning(
                "Connection attempt %d failed: %s. Retrying in %d seconds...",
                retry_count,
                str(e),
                retry_delay,
            )
            await asyncio.sleep(retry_delay)
            retry_delay *= backoff_factor  # Exponential backoff

    raise TransportError("Unreachable. Contact Hibachi support")
