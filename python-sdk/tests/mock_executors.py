import inspect
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
from hibachi_xyz.types import Json


class MockExecutorException(Exception):
    pass


class InputPack(NamedTuple):
    function_name: str
    arg_pack: Tuple


class MockValidationFailure(MockExecutorException):
    input_pack: InputPack
    message: str


class MockOutputExhausted(MockExecutorException):
    input_pack: InputPack


class MockOutput:
    pass


# returns false or raises MockValidationFailure on error
InputValidation: TypeAlias = Callable[[InputPack], bool]


@dataclass
class MockExceptionOutput(MockOutput):
    exception: Exception
    call_validation: InputValidation | None


@dataclass
class MockSuccessfulOutput(MockOutput):
    output: Any
    call_validation: InputValidation | None


class MockHttpExecutor(HttpExecutor):
    def __init__(self):
        self.call_log = []
        self.staged_outputs = deque()

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
        if not output.call_validation(input_pack):
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
    ) -> Any:
        input_pack = InputPack(inspect.stack()[0].function, (method, path, json))
        return self._execute_mock(input_pack)

    def send_simple_request(
        self,
        path: str,
    ) -> Json:
        input_pack = InputPack(inspect.stack()[0].function, (path,))
        return self._execute_mock(input_pack)

    def check_auth_data(self) -> None:
        input_pack = InputPack(inspect.stack()[0].function, ())
        return self._execute_mock(input_pack)
