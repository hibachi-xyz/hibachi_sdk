import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Generator

import orjson
import pytest

from hibachi_xyz.api import HibachiApiClient
from tests.mock_executors import MockHttpExecutor, MockOutputNotExhausted

DATA_DIR = Path(__file__).parent.joinpath("data")

log = logging.getLogger(__name__)


@pytest.fixture
def mock_http_client() -> Generator[
    tuple[HibachiApiClient, MockHttpExecutor], None, None
]:
    mock_http = MockHttpExecutor()
    client = HibachiApiClient(
        # these don't matter as they will not be used with the mock in place
        api_url="api.gaierror.xyz",
        data_api_url="data.api.gaierror.xyz",
        account_id=1,
        api_key="FOO",
        private_key="BAR",
        # replace real network requests with our mock
        executor=mock_http,
    )

    yield (client, mock_http)

    if len(mock_http.staged_outputs) > 0:
        raise MockOutputNotExhausted(mock_http.staged_outputs)


@lru_cache(maxsize=1)
def data_files() -> list[Path]:
    return list(DATA_DIR.iterdir())


@lru_cache(maxsize=1)
def json_data_files(name: str) -> list[Path]:
    return list(
        sorted(
            path
            for path in data_files()
            if path.match(f"*/{name}.*.json", case_sensitive=True)
        )
    )


def load_json(name: str, case: int | None = None) -> dict[str, Any]:
    case_part = f"{case}." if case else ""
    path = Path(__file__).parent / "data" / f"{name}.{case_part}json"
    with open(path, "rb") as fh:
        return orjson.loads(fh.read())


def load_json_all_cases(name: str) -> list[tuple[dict[str, Any], Path]]:
    """Load all json payloads for a given base name (case0, case1, ...)."""
    results = []
    for path in json_data_files(name):
        print("Attempting to load json from", path.as_posix())
        with open(path, "rb") as fh:
            payload = orjson.loads(fh.read())
            results.append((payload, path))
    return results
