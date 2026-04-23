"""Portfolio manager for global risk controls."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from hibachi_trading_bot.core.config import RiskConfig


@dataclass
class PositionInfo:
    """Information about an open position.

    Attributes:
        symbol: Trading pair symbol
        direction: Position direction (Long/Short)
        quantity: Position quantity
        entry_price: Entry price
        current_price: Current market price
        notional_value: Position notional value
        unrealized_pnl: Unrealized profit/loss
        stop_loss: Stop loss price
        take_profit: Take profit price
    """

    symbol: str
    direction: str
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    notional_value: Decimal
    unrealized_pnl: Decimal = Decimal("0")
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class PortfolioManager:
    """Manages portfolio-level risk constraints.

    Enforces:
    - Maximum number of simultaneous positions
    - Maximum total exposure
    - Per-position allocation limits
    """

    def __init__(self, config: RiskConfig) -> None:
        """Initialize the portfolio manager.

        Args:
            config: Risk configuration
        """
        self.config = config
        self._positions: dict[str, PositionInfo] = {}
        self._total_capital = Decimal("10000")  # Default, should be updated

    def update_capital(self, capital: Decimal) -> None:
        """Update total capital amount.

        Args:
            capital: Total capital in USDT
        """
        self._total_capital = capital

    @property
    def total_capital(self) -> Decimal:
        """Get total capital."""
        return self._total_capital

    @property
    def num_positions(self) -> int:
        """Get number of open positions."""
        return len(self._positions)

    @property
    def max_positions(self) -> int:
        """Get maximum allowed positions."""
        return self.config.max_positions

    @property
    def total_exposure(self) -> Decimal:
        """Calculate total exposure as percentage of capital."""
        if self._total_capital == 0:
            return Decimal("0")
        total_notional = sum(pos.notional_value for pos in self._positions.values())
        return total_notional / self._total_capital

    @property
    def available_exposure(self) -> Decimal:
        """Calculate remaining available exposure."""
        return self.config.max_exposure_percent - self.total_exposure

    def can_open_position(self, symbol: str, proposed_notional: Decimal) -> tuple[bool, str]:
        """Check if a new position can be opened.

        Args:
            symbol: Trading pair symbol
            proposed_notional: Proposed position notional value

        Returns:
            Tuple of (can_open, reason)
        """
        # Check if already have position in this symbol
        if symbol in self._positions:
            return False, f"Already have position in {symbol}"

        # Check max positions limit
        if self.num_positions >= self.config.max_positions:
            return (
                False,
                f"Max positions ({self.config.max_positions}) reached",
            )

        # Check exposure limit
        proposed_exposure = proposed_notional / self._total_capital if self._total_capital > 0 else Decimal("1")
        if self.total_exposure + proposed_exposure > self.config.max_exposure_percent:
            return (
                False,
                f"Would exceed max exposure ({self.config.max_exposure_percent})",
            )

        # Check position size limit
        max_position_size = self._total_capital * self.config.position_size_percent
        if proposed_notional > max_position_size:
            return (
                False,
                f"Position size exceeds limit ({max_position_size})",
            )

        return True, "OK"

    def add_position(
        self,
        symbol: str,
        direction: str,
        quantity: Decimal,
        entry_price: Decimal,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        """Add a new position to the portfolio.

        Args:
            symbol: Trading pair symbol
            direction: Position direction
            quantity: Position quantity
            entry_price: Entry price
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price
            metadata: Additional metadata

        Returns:
            Tuple of (success, message)
        """
        notional = quantity * entry_price

        # Validate
        can_open, reason = self.can_open_position(symbol, notional)
        if not can_open:
            return False, reason

        # Create position
        self._positions[symbol] = PositionInfo(
            symbol=symbol,
            direction=direction,
            quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
            notional_value=notional,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=metadata or {},
        )

        return True, "Position added"

    def update_position_price(self, symbol: str, current_price: Decimal) -> None:
        """Update current price for a position.

        Args:
            symbol: Trading pair symbol
            current_price: Current market price
        """
        if symbol not in self._positions:
            return

        pos = self._positions[symbol]
        pos.current_price = current_price

        # Update notional value
        pos.notional_value = pos.quantity * current_price

        # Calculate unrealized PnL
        if pos.direction == "Long":
            pnl = (current_price - pos.entry_price) * pos.quantity
        else:  # Short
            pnl = (pos.entry_price - current_price) * pos.quantity

        pos.unrealized_pnl = pnl

    def remove_position(self, symbol: str) -> bool:
        """Remove a position from the portfolio.

        Args:
            symbol: Trading pair symbol

        Returns:
            True if position was removed
        """
        if symbol in self._positions:
            del self._positions[symbol]
            return True
        return False

    def get_position(self, symbol: str) -> PositionInfo | None:
        """Get position info for a symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            PositionInfo or None
        """
        return self._positions.get(symbol)

    def get_all_positions(self) -> dict[str, PositionInfo]:
        """Get all open positions.

        Returns:
            Dictionary of symbol -> PositionInfo
        """
        return self._positions.copy()

    def get_total_unrealized_pnl(self) -> Decimal:
        """Get total unrealized PnL across all positions.

        Returns:
            Total unrealized PnL
        """
        return sum(pos.unrealized_pnl for pos in self._positions.values())

    def calculate_position_size(
        self,
        symbol: str,
        price: Decimal,
        atr: Decimal | None = None,
    ) -> tuple[Decimal, Decimal, Decimal]:
        """Calculate optimal position size based on risk parameters.

        Args:
            symbol: Trading pair symbol
            price: Current price
            atr: Optional ATR for volatility-adjusted sizing

        Returns:
            Tuple of (quantity, stop_loss, take_profit)
        """
        # Base position size: 15% of capital
        target_notional = self._total_capital * self.config.position_size_percent

        # Adjust for volatility if ATR provided
        if atr is not None and atr > 0:
            # Use ATR to adjust position size (higher volatility = smaller position)
            volatility_factor = min(Decimal("2.0"), max(Decimal("0.5"), atr / price))
            target_notional *= (Decimal("1") / volatility_factor)

        # Calculate quantity
        quantity = target_notional / price if price > 0 else Decimal("0")

        # Calculate stop loss and take profit based on ATR
        if atr is not None:
            stop_distance = atr * self.config.default_stop_loss_atr_mult
            tp_distance = atr * self.config.default_take_profit_atr_mult
        else:
            # Default percentages if no ATR
            stop_distance = price * Decimal("0.02")  # 2%
            tp_distance = price * Decimal("0.04")  # 4%

        stop_loss = price - stop_distance
        take_profit = price + tp_distance

        return quantity, stop_loss, take_profit
