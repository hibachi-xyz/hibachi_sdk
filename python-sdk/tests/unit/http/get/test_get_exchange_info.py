import pytest

from tests.mock_executors import MockSuccessfulOutput
from tests.unit.conftest import load_json_all_cases


@pytest.mark.parametrize("test_data", load_json_all_cases("response.exchange_info"))
def test_get_exchange_info(mock_http_client, test_data):
    payload, path = test_data
    client, mock_http = mock_http_client

    mock_http.stage_output(
        MockSuccessfulOutput(
            output=payload,
            call_validation=lambda call: call.function_name == "send_simple_request"
            and call.arg_pack == ("/market/exchange-info",),
        )
    )

    info = client.get_exchange_info()

    # Fee Config assertions
    assert info.feeConfig.depositFees == payload["feeConfig"]["depositFees"]
    assert (
        info.feeConfig.instantWithdrawDstPublicKey
        == payload["feeConfig"]["instantWithdrawDstPublicKey"]
    )
    assert (
        info.feeConfig.instantWithdrawalFees
        == payload["feeConfig"]["instantWithdrawalFees"]
    )
    assert info.feeConfig.tradeMakerFeeRate == payload["feeConfig"]["tradeMakerFeeRate"]
    assert info.feeConfig.tradeTakerFeeRate == payload["feeConfig"]["tradeTakerFeeRate"]
    assert info.feeConfig.transferFeeRate == payload["feeConfig"]["transferFeeRate"]
    assert info.feeConfig.withdrawalFees == payload["feeConfig"]["withdrawalFees"]

    # Future Contracts assertions
    assert len(info.futureContracts) == len(payload["futureContracts"])
    for contract, payload_contract in zip(
        info.futureContracts, payload["futureContracts"]
    ):
        assert contract.displayName == payload_contract["displayName"]
        assert contract.id == payload_contract["id"]
        assert contract.initialMarginRate == payload_contract["initialMarginRate"]
        assert (
            contract.maintenanceMarginRate == payload_contract["maintenanceMarginRate"]
        )
        assert contract.marketCloseTimestamp == payload_contract["marketCloseTimestamp"]
        assert (
            contract.marketCreationTimestamp
            == payload_contract["marketCreationTimestamp"]
        )
        assert contract.marketOpenTimestamp == payload_contract["marketOpenTimestamp"]
        assert contract.minNotional == payload_contract["minNotional"]
        assert contract.minOrderSize == payload_contract["minOrderSize"]
        assert (
            contract.orderbookGranularities
            == payload_contract["orderbookGranularities"]
        )
        assert contract.settlementDecimals == payload_contract["settlementDecimals"]
        assert contract.settlementSymbol == payload_contract["settlementSymbol"]
        assert contract.status == payload_contract["status"]
        assert contract.stepSize == payload_contract["stepSize"]
        assert contract.symbol == payload_contract["symbol"]
        assert contract.tickSize == payload_contract["tickSize"]
        assert contract.underlyingDecimals == payload_contract["underlyingDecimals"]
        assert contract.underlyingSymbol == payload_contract["underlyingSymbol"]

    # Maintenance Window assertions
    assert len(info.maintenanceWindow) == len(payload["maintenanceWindow"])
    for window, payload_window in zip(
        info.maintenanceWindow, payload["maintenanceWindow"]
    ):
        assert window.begin == payload_window["begin"]
        assert window.end == payload_window["end"]
        assert window.note == payload_window["note"]

    # Instant Withdrawal Limit assertions
    assert (
        info.instantWithdrawalLimit.lowerLimit
        == payload["instantWithdrawalLimit"]["lowerLimit"]
    )
    assert (
        info.instantWithdrawalLimit.upperLimit
        == payload["instantWithdrawalLimit"]["upperLimit"]
    )

    # Status assertion
    assert info.status == payload["status"]
