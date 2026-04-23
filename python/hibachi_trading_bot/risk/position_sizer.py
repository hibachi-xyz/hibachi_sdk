"""Position sizer for ATR-based dynamic position sizing."""

from decimal import Decimal


class PositionSizer:
    """Calculates position sizes based on volatility and risk parameters.

    Uses ATR (Average True Range) to adjust position sizes dynamically:
    - Higher volatility (higher ATR) = smaller position size
    - Lower volatility (lower ATR) = larger position size
    """

    def __init__(
        self,
        base_capital: Decimal,
        risk_per_trade: Decimal = Decimal("0.01"),
        max_position_percent: Decimal = Decimal("0.15"),
    ) -> None:
        """Initialize the position sizer.

        Args:
            base_capital: Total capital available
            risk_per_trade: Risk per trade as percentage of capital (default 1%)
            max_position_percent: Maximum position size as percentage (default 15%)
        """
        self.base_capital = base_capital
        self.risk_per_trade = risk_per_trade
        self.max_position_percent = max_position_percent

    def calculate_size_by_atr(
        self,
        price: Decimal,
        atr: Decimal,
        stop_loss_atr_multiple: Decimal = Decimal("2.0"),
    ) -> tuple[Decimal, Decimal]:
        """Calculate position size based on ATR.

        Args:
            price: Current price
            atr: Average True Range value
            stop_loss_atr_multiple: Stop loss distance as multiple of ATR

        Returns:
            Tuple of (quantity, stop_loss_price)
        """
        if atr <= 0:
            raise ValueError("ATR must be positive")

        # Calculate stop loss distance
        stop_distance = atr * stop_loss_atr_multiple

        # Calculate risk amount in capital terms
        risk_amount = self.base_capital * self.risk_per_trade

        # Calculate quantity based on risk
        # Quantity = Risk Amount / Stop Distance
        quantity = risk_amount / stop_distance if stop_distance > 0 else Decimal("0")

        # Apply maximum position size constraint
        max_quantity = (self.base_capital * self.max_position_percent) / price
        quantity = min(quantity, max_quantity)

        # Calculate stop loss price
        stop_loss = price - stop_distance

        return quantity, stop_loss

    def calculate_size_fixed_risk(
        self,
        price: Decimal,
        stop_loss_price: Decimal,
    ) -> Decimal:
        """Calculate position size for fixed dollar risk.

        Args:
            price: Entry price
            stop_loss_price: Stop loss price

        Returns:
            Quantity to trade
        """
        if price <= stop_loss_price:
            raise ValueError("Stop loss must be below entry price for long positions")

        risk_per_unit = price - stop_loss_price
        risk_amount = self.base_capital * self.risk_per_trade

        quantity = risk_amount / risk_per_unit

        # Apply maximum position size constraint
        max_quantity = (self.base_capital * self.max_position_percent) / price
        quantity = min(quantity, max_quantity)

        return quantity

    def calculate_take_profit(
        self,
        entry_price: Decimal,
        stop_loss_price: Decimal,
        risk_reward_ratio: Decimal = Decimal("2.0"),
    ) -> Decimal:
        """Calculate take profit price based on risk/reward ratio.

        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            risk_reward_ratio: Desired risk/reward ratio (default 2:1)

        Returns:
            Take profit price
        """
        risk = entry_price - stop_loss_price
        reward = risk * risk_reward_ratio
        take_profit = entry_price + reward

        return take_profit

    def validate_tp_sl_ratio(
        self,
        entry_price: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal,
        min_ratio: Decimal = Decimal("1.5"),
    ) -> bool:
        """Validate that take profit to stop loss ratio meets minimum.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            min_ratio: Minimum acceptable ratio

        Returns:
            True if ratio is acceptable
        """
        risk = entry_price - stop_loss
        reward = take_profit - entry_price

        if risk <= 0:
            return False

        actual_ratio = reward / risk
        return actual_ratio >= min_ratio
