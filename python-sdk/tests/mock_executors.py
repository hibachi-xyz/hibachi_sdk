import asyncio
import inspect
import logging
from collections import deque
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Iterable,
    NamedTuple,
    Optional,
    Tuple,
    TypeAlias,
)

from hibachi_xyz.executors import HttpExecutor
from hibachi_xyz.executors.aiohttp import WsExecutor
from hibachi_xyz.executors.interface import HttpResponse, WsConnection

log = logging.getLogger(__name__)


class MockExecutorException(Exception):
    pass


class InputPack(NamedTuple):
    function_name: str
    arg_pack: Tuple


class MockOutput:
    pass


class MockValidationFailure(MockExecutorException):
    input_pack: InputPack
    message: str


class MockOutputExhausted(MockExecutorException):
    input_pack: InputPack


class MockOutputNotExhausted(MockExecutorException):
    remaining_staged_outputs: deque[MockOutput]


# returns false or raises MockValidationFailure on error
InputValidation: TypeAlias = Callable[[InputPack], bool]


@dataclass
class MockExceptionOutput(MockOutput):
    exception: Exception
    call_validation: InputValidation | None = None


@dataclass
class MockSuccessfulOutput(MockOutput):
    output: Any
    call_validation: InputValidation | None = None


class MockHttpExecutor(HttpExecutor):
    def __init__(self):
        self.call_log: list[InputPack] = []
        self.staged_outputs: deque[MockOutput] = deque()

    def stage_output(self, output: MockOutput | Iterable[MockOutput]) -> None:
        """Stage an output to be returned by the next request."""
        if isinstance(output, Iterable):
            self.staged_outputs.extend(output)
        else:
            self.staged_outputs.append(output)

    def _execute_mock(self, input_pack: InputPack) -> Any:
        """Execute a mock operation with the given input pack."""
        self.call_log.append(input_pack)
        if not self.staged_outputs:
            raise MockOutputExhausted(input_pack)
        output = self.staged_outputs.popleft()
        if output.call_validation is not None and not output.call_validation(
            input_pack
        ):
            raise MockValidationFailure(input_pack, "Validation failed")
        if isinstance(output, MockExceptionOutput):
            raise output.exception
        elif isinstance(output, MockSuccessfulOutput):
            return output.output
        raise MockExecutorException(f"Unexpected staged mock {output=}")

    def send_authorized_request(
        self,
        method: str,
        path: str,
        json: Optional[Any] = None,
    ) -> HttpResponse:
        input_pack = InputPack(inspect.stack()[0].function, (method, path, json))
        return self._execute_mock(input_pack)

    def send_simple_request(
        self,
        path: str,
    ) -> HttpResponse:
        input_pack = InputPack(inspect.stack()[0].function, (path,))
        return self._execute_mock(input_pack)


class MockWsHarness:
    executor: "MockWsExecutor"
    connections: list["MockWsConnection"]

    def __init__(self):
        self.executor = MockWsExecutor(self)
        self.http_executor = MockHttpExecutor()
        self.connections = []


class MockWsConnection(WsConnection):
    def __init__(self, harness: MockWsHarness):
        self.call_log: list[InputPack] = []
        self.staged_outputs: deque[MockOutput] = deque()
        self.staged_recv: asyncio.Queue[MockOutput] = asyncio.Queue()
        self._harness = harness

    def stage_output(self, output: MockOutput | Iterable[MockOutput]) -> None:
        """Stage an output to be returned by the next request."""
        if isinstance(output, Iterable):
            self.staged_outputs.extend(output)
        else:
            self.staged_outputs.append(output)

    def stage_recv(self, output: MockOutput | Iterable[MockOutput]) -> None:
        """Stage recv outputs (strings or exceptions) to be returned by subsequent recv calls."""
        if isinstance(output, Iterable):
            for item in output:
                self.staged_recv.put_nowait(item)
        else:
            self.staged_recv.put_nowait(output)

    def _execute_mock(self, input_pack: InputPack) -> Any:
        """Execute a mock operation with the given input pack."""
        self.call_log.append(input_pack)
        if not self.staged_outputs:
            raise MockOutputExhausted(input_pack)
        output = self.staged_outputs.popleft()
        if output.call_validation is not None and not output.call_validation(
            input_pack
        ):
            raise MockValidationFailure(input_pack, "Validation failed")
        if isinstance(output, MockExceptionOutput):
            raise output.exception
        elif isinstance(output, MockSuccessfulOutput):
            return output.output
        raise MockExecutorException(f"Unexpected staged mock {output=}")

    async def send(
        self,
        serialized_body: str,
    ) -> None:
        input_pack = InputPack(inspect.stack()[0].function, (serialized_body,))
        self.call_log.append(input_pack)
        return None

    async def recv(self) -> str:
        # A little different from standard _execute_mock because we want to enable waiting and we don't care about a call log
        next_output = await self.staged_recv.get()

        if isinstance(next_output, MockExceptionOutput):
            raise next_output.exception
        elif isinstance(next_output, MockSuccessfulOutput):
            return next_output.output
        raise MockExecutorException(f"Unexpected staged mock {next_output=}")

    async def close(self) -> None:
        input_pack = InputPack(inspect.stack()[0].function, ())
        self.call_log.append(input_pack)
        return None


class MockWsExecutor(WsExecutor):
    def __init__(self, harness: MockWsHarness):
        self._harness = harness
        self.call_log: list[InputPack] = []
        # no staged outputs because we always return a mockable connection

    async def connect(
        self, web_url: str, headers: dict[str, str] | None = None
    ) -> WsConnection:
        input_pack = InputPack(inspect.stack()[0].function, (web_url, headers))
        self.call_log.append(input_pack)
        connection = MockWsConnection(self._harness)
        self._harness.connections.append(connection)
        return connection
