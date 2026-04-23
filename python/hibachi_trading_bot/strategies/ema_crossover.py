"""EMA Crossover Strategy (Strategy 1).

Trend-following strategy based on EMA crossovers with RSI quality filter.
"""

from decimal import Decimal
from typing import Any

import pandas as pd

from hibachi_trading_bot.strategies.base import Signal, SignalType, Strategy


class EMACrossoverStrategy(Strategy):
    """EMA Crossover trend-following strategy.

    Entry conditions:
    - Long: Fast EMA crosses above Slow EMA, RSI not overbought
    - Short: Fast EMA crosses below Slow EMA, RSI not oversold

    Exit conditions:
    - Opposite crossover or RSI extreme levels
    """

    def __init__(
        self,
        ema_fast: int = 9,
        ema_slow: int = 21,
        rsi_period: int = 14,
        rsi_overbought: float = 70.0,
        rsi_oversold: float = 30.0,
    ) -> None:
        """Initialize the EMA Crossover strategy.

        Args:
            ema_fast: Fast EMA period
            ema_slow: Slow EMA period
            rsi_period: RSI calculation period
            rsi_overbought: RSI overbought threshold
            rsi_oversold: RSI oversold threshold
        """
        super().__init__("EMA_Crossover")
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold

    def generate_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        current_price: Decimal,
        position: dict[str, Any] | None = None,
    ) -> Signal:
        """Generate trading signal based on EMA crossover.

        Args:
            symbol: Trading pair symbol
            df: DataFrame with OHLCV and indicator data
            current_price: Current market price
            position: Current position info (if any)

        Returns:
            Signal object
        """
        if df.empty or len(df) < self.ema_slow + 5:
            return Signal(
                signal_type=SignalType.NONE,
                symbol=symbol,
                strength=0.0,
                timestamp=int(pd.Timestamp.now().timestamp()),
            )

        # Get latest values
        ema_fast_col = f"ema_fast_{self.ema_fast}"
        ema_slow_col = f"ema_slow_{self.ema_slow}"

        if not self.validate_data(
            df, ["close", ema_fast_col, ema_slow_col, "rsi"]
        ):
            return Signal(
                signal_type=SignalType.NONE,
                symbol=symbol,
                strength=0.0,
                metadata={"error": "Missing required columns"},
                timestamp=int(pd.Timestamp.now().timestamp()),
            )

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        rsi = float(latest["rsi"])
        ema_fast = float(latest[ema_fast_col])
        ema_slow = float(latest[ema_slow_col])
        ema_fast_prev = float(prev[ema_fast_col])
        ema_slow_prev = float(prev[ema_slow_col])

        timestamp = int(df.index[-1]) if hasattr(df.index[-1], "item") else int(df.index[-1])

        # Check for bullish crossover (fast crosses above slow)
        bullish_crossover = (ema_fast_prev <= ema_slow_prev) and (ema_fast > ema_slow)
        # Check for bearish crossover (fast crosses below slow)
        bearish_crossover = (ema_fast_prev >= ema_slow_prev) and (ema_fast < ema_slow)

        # RSI filter - avoid entering when overbought/oversold
        rsi_valid_for_long = rsi < self.rsi_overbought
        rsi_valid_for_short = rsi > self.rsi_oversold

        # Generate signal
        if bullish_crossover and rsi_valid_for_long:
            strength = min(1.0, (self.rsi_overbought - rsi) / 40.0)
            return Signal(
                signal_type=SignalType.LONG,
                symbol=symbol,
                strength=strength,
                price=current_price,
                metadata={
                    "strategy": self.name,
                    "crossover_type": "bullish",
                    "rsi": rsi,
                    "ema_fast": ema_fast,
                    "ema_slow": ema_slow,
                },
                timestamp=timestamp,
            )

        if bearish_crossover and rsi_valid_for_short:
            strength = min(1.0, (rsi - self.rsi_oversold) / 40.0)
            return Signal(
                signal_type=SignalType.SHORT,
                symbol=symbol,
                strength=strength,
                price=current_price,
                metadata={
                    "strategy": self.name,
                    "crossover_type": "bearish",
                    "rsi": rsi,
                    "ema_fast": ema_fast,
                    "ema_slow": ema_slow,
                },
                timestamp=timestamp,
            )

        # Check exit conditions for existing positions
        if position is not None:
            direction = position.get("direction", "")
            if direction == "Long" and bearish_crossover:
                return Signal(
                    signal_type=SignalType.CLOSE_LONG,
                    symbol=symbol,
                    strength=0.8,
                    price=current_price,
                    metadata={"reason": "bearish_crossover"},
                    timestamp=timestamp,
                )
            if direction == "Short" and bullish_crossover:
                return Signal(
                    signal_type=SignalType.CLOSE_SHORT,
                    symbol=symbol,
                    strength=0.8,
                    price=current_price,
                    metadata={"reason": "bullish_crossover"},
                    timestamp=timestamp,
                )

        return Signal(
            signal_type=SignalType.NONE,
            symbol=symbol,
            strength=0.0,
            timestamp=timestamp,
        )
