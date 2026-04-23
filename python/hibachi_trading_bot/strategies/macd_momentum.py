"""MACD Momentum Strategy (Strategy 3).

Momentum strategy based on MACD crossovers with ATR adaptive position sizing.
"""

from decimal import Decimal
from typing import Any

import pandas as pd

from hibachi_trading_bot.strategies.base import Signal, SignalType, Strategy


class MACDMomentumStrategy(Strategy):
    """MACD Momentum strategy.

    Entry conditions:
    - Long: MACD line crosses above signal line (bullish momentum)
    - Short: MACD line crosses below signal line (bearish momentum)

    Exit conditions:
    - Opposite crossover
    - MACD histogram divergence
    """

    def __init__(
        self,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        atr_period: int = 14,
        min_histogram_threshold: float = 0.0,
    ) -> None:
        """Initialize the MACD Momentum strategy.

        Args:
            macd_fast: Fast EMA period for MACD
            macd_slow: Slow EMA period for MACD
            macd_signal: Signal line period
            atr_period: ATR period for adaptive sizing
            min_histogram_threshold: Minimum histogram value to confirm signal
        """
        super().__init__("MACD_Momentum")
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.atr_period = atr_period
        self.min_histogram_threshold = min_histogram_threshold

    def generate_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        current_price: Decimal,
        position: dict[str, Any] | None = None,
    ) -> Signal:
        """Generate trading signal based on MACD momentum.

        Args:
            symbol: Trading pair symbol
            df: DataFrame with OHLCV and indicator data
            current_price: Current market price
            position: Current position info (if any)

        Returns:
            Signal object
        """
        if df.empty or len(df) < self.macd_slow + 10:
            return Signal(
                signal_type=SignalType.NONE,
                symbol=symbol,
                strength=0.0,
                timestamp=int(pd.Timestamp.now().timestamp()),
            )

        if not self.validate_data(
            df, ["macd", "macd_signal", "macd_histogram", "atr"]
        ):
            return Signal(
                signal_type=SignalType.NONE,
                symbol=symbol,
                strength=0.0,
                metadata={"error": "Missing required columns"},
                timestamp=int(pd.Timestamp.now().timestamp()),
            )

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        macd = float(latest["macd"])
        macd_sig = float(latest["macd_signal"])
        macd_hist = float(latest["macd_histogram"])
        atr = float(latest["atr"])

        macd_prev = float(prev["macd"])
        macd_sig_prev = float(prev["macd_signal"])

        timestamp = int(df.index[-1]) if hasattr(df.index[-1], "item") else int(df.index[-1])

        # Check for bullish crossover (MACD crosses above signal)
        bullish_crossover = (macd_prev <= macd_sig_prev) and (macd > macd_sig)
        # Check for bearish crossover (MACD crosses below signal)
        bearish_crossover = (macd_prev >= macd_sig_prev) and (macd < macd_sig)

        # Confirm with histogram strength
        histogram_confirmed_long = macd_hist > self.min_histogram_threshold
        histogram_confirmed_short = macd_hist < -self.min_histogram_threshold

        # Generate entry signals
        if bullish_crossover and histogram_confirmed_long:
            # Strength based on histogram magnitude relative to ATR
            strength = min(1.0, abs(macd_hist) / (atr * 0.01) if atr > 0 else 0.5)
            return Signal(
                signal_type=SignalType.LONG,
                symbol=symbol,
                strength=strength,
                price=current_price,
                metadata={
                    "strategy": self.name,
                    "crossover_type": "bullish",
                    "macd": macd,
                    "macd_signal": macd_sig,
                    "macd_histogram": macd_hist,
                    "atr": atr,
                },
                timestamp=timestamp,
            )

        if bearish_crossover and histogram_confirmed_short:
            strength = min(1.0, abs(macd_hist) / (atr * 0.01) if atr > 0 else 0.5)
            return Signal(
                signal_type=SignalType.SHORT,
                symbol=symbol,
                strength=strength,
                price=current_price,
                metadata={
                    "strategy": self.name,
                    "crossover_type": "bearish",
                    "macd": macd,
                    "macd_signal": macd_sig,
                    "macd_histogram": macd_hist,
                    "atr": atr,
                },
                timestamp=timestamp,
            )

        # Exit conditions for existing positions
        if position is not None:
            direction = position.get("direction", "")

            # Exit long on bearish crossover or histogram divergence
            if direction == "Long" and (bearish_crossover or macd_hist < 0):
                return Signal(
                    signal_type=SignalType.CLOSE_LONG,
                    symbol=symbol,
                    strength=0.7,
                    price=current_price,
                    metadata={"reason": "momentum_reversal"},
                    timestamp=timestamp,
                )

            # Exit short on bullish crossover or histogram divergence
            if direction == "Short" and (bullish_crossover or macd_hist > 0):
                return Signal(
                    signal_type=SignalType.CLOSE_SHORT,
                    symbol=symbol,
                    strength=0.7,
                    price=current_price,
                    metadata={"reason": "momentum_reversal"},
                    timestamp=timestamp,
                )

        return Signal(
            signal_type=SignalType.NONE,
            symbol=symbol,
            strength=0.0,
            timestamp=timestamp,
        )
