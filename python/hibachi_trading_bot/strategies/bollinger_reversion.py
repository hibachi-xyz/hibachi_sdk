"""Bollinger Bands Mean Reversion Strategy (Strategy 2).

Mean reversion strategy that trades bounces off Bollinger Bands with volume confirmation.
"""

from decimal import Decimal
from typing import Any

import pandas as pd

from hibachi_trading_bot.strategies.base import Signal, SignalType, Strategy


class BollingerReversionStrategy(Strategy):
    """Bollinger Bands Mean Reversion strategy.

    Entry conditions:
    - Long: Price touches/breaks lower BB, volume spike confirms exhaustion
    - Short: Price touches/breaks upper BB, volume spike confirms exhaustion

    Exit conditions:
    - Price returns to middle band (mean)
    - Opposite band touch
    """

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        volume_spike_multiplier: float = 2.0,
        volume_lookback: int = 20,
    ) -> None:
        """Initialize the Bollinger Reversion strategy.

        Args:
            bb_period: Bollinger Bands period
            bb_std: Standard deviation multiplier for bands
            volume_spike_multiplier: Multiplier for volume spike detection
            volume_lookback: Lookback period for average volume calculation
        """
        super().__init__("Bollinger_Reversion")
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.volume_spike_multiplier = volume_spike_multiplier
        self.volume_lookback = volume_lookback

    def generate_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        current_price: Decimal,
        position: dict[str, Any] | None = None,
    ) -> Signal:
        """Generate trading signal based on Bollinger Bands mean reversion.

        Args:
            symbol: Trading pair symbol
            df: DataFrame with OHLCV and indicator data
            current_price: Current market price
            position: Current position info (if any)

        Returns:
            Signal object
        """
        if df.empty or len(df) < self.bb_period + 10:
            return Signal(
                signal_type=SignalType.NONE,
                symbol=symbol,
                strength=0.0,
                timestamp=int(pd.Timestamp.now().timestamp()),
            )

        if not self.validate_data(
            df, ["close", "bb_upper", "bb_middle", "bb_lower", "bb_position", "volume"]
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

        close = float(latest["close"])
        bb_upper = float(latest["bb_upper"])
        bb_middle = float(latest["bb_middle"])
        bb_lower = float(latest["bb_lower"])
        bb_position = float(latest["bb_position"])
        volume = float(latest["volume"])

        # Calculate average volume for spike detection
        avg_volume = df["volume"].rolling(window=self.volume_lookback).mean().iloc[-1]
        volume_spike = volume > (avg_volume * self.volume_spike_multiplier)

        timestamp = int(df.index[-1]) if hasattr(df.index[-1], "item") else int(df.index[-1])

        # Check if price is at extremes (outside or touching bands)
        price_at_lower = close <= bb_lower * 1.001  # Within 0.1% of lower band
        price_at_upper = close >= bb_upper * 0.999  # Within 0.1% of upper band

        # For mean reversion, we want to buy low and sell high
        # Long signal: Price at lower band with volume spike (selling exhaustion)
        if price_at_lower and volume_spike:
            # Calculate strength based on how far below the middle we are
            strength = min(1.0, (bb_middle - close) / (bb_middle - bb_lower))
            return Signal(
                signal_type=SignalType.LONG,
                symbol=symbol,
                strength=strength,
                price=current_price,
                metadata={
                    "strategy": self.name,
                    "bb_position": bb_position,
                    "volume_spike": True,
                    "volume_ratio": volume / avg_volume if avg_volume > 0 else 0,
                },
                timestamp=timestamp,
            )

        # Short signal: Price at upper band with volume spike (buying exhaustion)
        if price_at_upper and volume_spike:
            strength = min(1.0, (close - bb_middle) / (bb_upper - bb_middle))
            return Signal(
                signal_type=SignalType.SHORT,
                symbol=symbol,
                strength=strength,
                price=current_price,
                metadata={
                    "strategy": self.name,
                    "bb_position": bb_position,
                    "volume_spike": True,
                    "volume_ratio": volume / avg_volume if avg_volume > 0 else 0,
                },
                timestamp=timestamp,
            )

        # Exit conditions for existing positions
        if position is not None:
            direction = position.get("direction", "")

            # Exit long when price reaches middle band or goes above
            if direction == "Long" and close >= bb_middle:
                return Signal(
                    signal_type=SignalType.CLOSE_LONG,
                    symbol=symbol,
                    strength=0.7,
                    price=current_price,
                    metadata={"reason": "reached_mean"},
                    timestamp=timestamp,
                )

            # Exit short when price reaches middle band or goes below
            if direction == "Short" and close <= bb_middle:
                return Signal(
                    signal_type=SignalType.CLOSE_SHORT,
                    symbol=symbol,
                    strength=0.7,
                    price=current_price,
                    metadata={"reason": "reached_mean"},
                    timestamp=timestamp,
                )

        return Signal(
            signal_type=SignalType.NONE,
            symbol=symbol,
            strength=0.0,
            timestamp=timestamp,
        )
