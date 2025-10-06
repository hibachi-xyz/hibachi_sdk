import copy

import pytest

from tests.mock_executors import MockSuccessfulOutput
from tests.unit.conftest import load_json_all_cases


@pytest.mark.parametrize("test_data", load_json_all_cases("response.inventory"))
def test_get_inventory(mock_http_client, test_data):
    payload, path = test_data
    client, mock_http = mock_http_client

    # Save original nested structures before they get mutated
    original_markets = copy.deepcopy(payload["markets"])
    original_cca = copy.deepcopy(payload["crossChainAssets"])
    original_fee = copy.deepcopy(payload["feeConfig"])
    original_tiers = copy.deepcopy(payload["tradingTiers"])

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=payload,
            call_validation=lambda call: call.function_name == "send_simple_request"
            and call.arg_pack == ("/market/inventory",),
        )
    )

    inventory = client.get_inventory()

    # CrossChainAssets assertions
    assert len(inventory.crossChainAssets) == len(original_cca)
    for asset, orig_asset in zip(inventory.crossChainAssets, original_cca):
        assert asset.chain == orig_asset["chain"]
        assert asset.token == orig_asset["token"]
        assert asset.exchangeRateFromUSDT == orig_asset["exchangeRateFromUSDT"]
        assert asset.exchangeRateToUSDT == orig_asset["exchangeRateToUSDT"]

    # FeeConfig assertions
    assert inventory.feeConfig.depositFees == original_fee["depositFees"]
    assert inventory.feeConfig.withdrawalFees == original_fee["withdrawalFees"]

    # Markets assertions
    assert len(inventory.markets) == len(original_markets)
    for market, orig_market in zip(inventory.markets, original_markets):
        assert market.contract.symbol == orig_market["contract"]["symbol"]
        assert market.contract.id == orig_market["contract"]["id"]
        assert market.info.markPrice == orig_market["info"]["markPrice"]
        assert market.info.priceLatest == orig_market["info"]["priceLatest"]

    # TradingTiers assertions
    assert len(inventory.tradingTiers) == len(original_tiers)
    for tier, orig_tier in zip(inventory.tradingTiers, original_tiers):
        assert tier.level == orig_tier["level"]
        assert tier.title == orig_tier["title"]
