import pytest
from examples.example_public_api import example_public_api
from examples.example_rest_api import example_auth_rest_api
from examples.example_ws_account import example_ws_account
from examples.example_ws_market import example_ws_market
from examples.example_ws_trade import example_ws_trade
from examples.example_tpsl import (
    example_tpsl_ws_client,
    example_tpsl_rest,
)


@pytest.mark.asyncio
async def test_example_public_api():
    example_public_api()


@pytest.mark.asyncio
async def test_example_auth_rest_api():
    example_auth_rest_api()


@pytest.mark.asyncio
async def test_example_tpsl():
    example_tpsl_rest()
    await example_tpsl_ws_client()


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_example_ws_market():
    msgs = await example_ws_market(max_messages=3)
    assert msgs


@pytest.mark.asyncio
async def test_example_ws_account():
    msgs = await example_ws_account(max_messages=3)
    assert msgs


@pytest.mark.asyncio
async def test_example_ws_trade():
    await example_ws_trade()
