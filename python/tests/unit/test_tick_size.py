"""Tests for tick size and step size rounding and validation utilities."""

from decimal import Decimal

import pytest

from hibachi_xyz.errors import ValidationError
from hibachi_xyz.types import (
    check_tick_size,
    round_price_to_tick,
    round_quantity_to_step,
)


class TestRoundPriceToTick:
    """Tests for round_price_to_tick utility."""

    def test_already_aligned(self):
        result = round_price_to_tick("100.01", "0.01")
        assert result == Decimal("100.01")

    def test_rounds_nearest(self):
        result = round_price_to_tick("100.005", "0.01")
        assert result == Decimal("100.00") or result == Decimal("100.01")

    def test_rounds_down(self):
        result = round_price_to_tick("100.004", "0.01")
        assert result == Decimal("100.00")

    def test_rounds_up(self):
        result = round_price_to_tick("100.006", "0.01")
        assert result == Decimal("100.01")

    def test_float_input(self):
        result = round_price_to_tick(100.123, "0.01")
        assert result == Decimal("100.12")

    def test_int_input(self):
        result = round_price_to_tick(100, "0.01")
        assert result == Decimal("100.00")

    def test_decimal_input(self):
        result = round_price_to_tick(Decimal("100.123"), "0.01")
        assert result == Decimal("100.12")

    def test_btc_tick_size(self):
        result = round_price_to_tick("71286.05", "0.1")
        assert result == Decimal("71286.0") or result == Decimal("71286.1")

    def test_sol_tick_size(self):
        result = round_price_to_tick("84.5001", "0.001")
        assert result == Decimal("84.500")

    def test_sui_tick_size(self):
        result = round_price_to_tick("0.962423", "0.00001")
        assert result == Decimal("0.96242")

    def test_zero_tick_size_raises(self):
        with pytest.raises(ValidationError, match="must be positive"):
            round_price_to_tick("100.12345", "0")

    def test_negative_tick_size_raises(self):
        with pytest.raises(ValidationError):
            round_price_to_tick("100.12345", "-0.01")

    def test_simulates_mark_price_offset(self):
        """Simulate Ymir-style price generation: mark * (1 + delta)."""
        mark = Decimal("2234")
        tick = "0.01"
        for i in range(1, 20):
            delta = Decimal(str(i)) * Decimal("0.0001")
            price = mark * (1 + delta)
            rounded = round_price_to_tick(price, tick)
            # Must pass validation
            check_tick_size(rounded, tick)

    def test_mid_price_half_tick(self):
        """Mid price (bid+ask)/2 is often a half-tick."""
        bid = Decimal("100.01")
        ask = Decimal("100.02")
        mid = (bid + ask) / 2  # 100.015
        result = round_price_to_tick(mid, "0.01")
        check_tick_size(result, "0.01")
        assert result == Decimal("100.02")


class TestRoundQuantityToStep:
    """Tests for round_quantity_to_step utility."""

    def test_already_aligned(self):
        result = round_quantity_to_step("1.0", "0.000000001")
        assert result == Decimal("1.000000000")

    def test_rounds_down(self):
        """Quantity should round DOWN to avoid exceeding intended size."""
        result = round_quantity_to_step("1.9999999999", "0.000000001")
        assert result == Decimal("1.999999999")

    def test_float_input(self):
        result = round_quantity_to_step(0.123456789, "0.00000001")
        assert result == Decimal("0.12345678")

    def test_zero_step_raises(self):
        with pytest.raises(ValidationError, match="must be positive"):
            round_quantity_to_step("1.23456", "0")


class TestCheckTickSize:
    """Tests for check_tick_size validation."""

    def test_valid_price(self):
        check_tick_size("100.01", "0.01")  # Should not raise

    def test_invalid_price(self):
        with pytest.raises(ValidationError, match="not a multiple of tick size"):
            check_tick_size("100.001", "0.01")

    def test_zero_tick_size_raises(self):
        with pytest.raises(ValidationError, match="must be positive"):
            check_tick_size("100.12345", "0")

    def test_trigger_price_validation(self):
        with pytest.raises(ValidationError, match="not a multiple of tick size"):
            check_tick_size("1.005", "0.01")

    def test_decimal_input(self):
        check_tick_size(Decimal("100.01"), "0.01")  # Should not raise

    def test_decimal_input_invalid(self):
        with pytest.raises(ValidationError):
            check_tick_size(Decimal("100.001"), "0.01")
