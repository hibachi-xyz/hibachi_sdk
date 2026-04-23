"""Market Regime Filter using ADX.

Determines whether the market is trending or ranging to select appropriate strategies.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

import pandas as pd


class MarketRegime(Enum):
    """Market regime classification."""

    TRENDING = auto()
    RANGING = auto()
    TRANSITION = auto()
    UNKNOWN = auto()


@dataclass
class RegimeState:
    """Current market regime state.

    Attributes:
        regime: Current market regime
        adx_value: Current ADX value
        symbol: Trading pair symbol
        timestamp: State timestamp
        confidence: Confidence level (0.0 to 1.0)
    """

    regime: MarketRegime
    adx_value: float
    symbol: str
    timestamp: int | None = None
    confidence: float = 1.0


class RegimeFilter:
    """Market regime filter using ADX indicator.

    The filter classifies market conditions:
    - ADX > 25: Trending market (use trend-following strategies S1, S3)
    - ADX < 20: Ranging market (use mean-reversion strategy S2)
    - 20 <= ADX <= 25: Transition zone (reduce position size or wait)
    """

    def __init__(
        self,
        adx_threshold_trend: float = 25.0,
        adx_threshold_range: float = 20.0,
        adx_period: int = 14,
    ) -> None:
        """Initialize the regime filter.

        Args:
            adx_threshold_trend: ADX value above which market is considered trending
            adx_threshold_range: ADX value below which market is considered ranging
            adx_period: ADX calculation period
        """
        self.adx_threshold_trend = adx_threshold_trend
        self.adx_threshold_range = adx_threshold_range
        self.adx_period = adx_period

    def classify_regime(
        self,
        symbol: str,
        df: pd.DataFrame,
    ) -> RegimeState:
        """Classify the current market regime.

        Args:
            symbol: Trading pair symbol
            df: DataFrame with OHLCV and ADX data

        Returns:
            RegimeState with current regime classification
        """
        if df.empty or "adx" not in df.columns:
            return RegimeState(
                regime=MarketRegime.UNKNOWN,
                adx_value=0.0,
                symbol=symbol,
                confidence=0.0,
            )

        latest_adx = float(df["adx"].iloc[-1])
        timestamp = int(df.index[-1]) if hasattr(df.index[-1], "item") else int(df.index[-1])

        # Classify based on ADX thresholds
        if latest_adx > self.adx_threshold_trend:
            regime = MarketRegime.TRENDING
            # Higher ADX = higher confidence in trend
            confidence = min(1.0, (latest_adx - self.adx_threshold_trend) / 25.0 + 0.7)
        elif latest_adx < self.adx_threshold_range:
            regime = MarketRegime.RANGING
            # Lower ADX = higher confidence in range
            confidence = min(1.0, (self.adx_threshold_range - latest_adx) / 20.0 + 0.7)
        else:
            regime = MarketRegime.TRANSITION
            # Transition zone has lower confidence
            confidence = 0.5

        return RegimeState(
            regime=regime,
            adx_value=latest_adx,
            symbol=symbol,
            timestamp=timestamp,
            confidence=confidence,
        )

    def get_allowed_strategies(self, regime: MarketRegime) -> list[str]:
        """Get list of allowed strategy names for a given regime.

        Args:
            regime: Current market regime

        Returns:
            List of strategy names allowed in this regime
        """
        if regime == MarketRegime.TRENDING:
            return ["EMA_Crossover", "MACD_Momentum"]
        elif regime == MarketRegime.RANGING:
            return ["Bollinger_Reversion"]
        else:  # TRANSITION or UNKNOWN
            return []  # No trading in transition/unknown

    def should_allow_signal(
        self,
        regime: MarketRegime,
        strategy_name: str,
    ) -> bool:
        """Check if a signal from a strategy should be allowed in current regime.

        Args:
            regime: Current market regime
            strategy_name: Name of the strategy generating the signal

        Returns:
            True if signal should be allowed
        """
        allowed = self.get_allowed_strategies(regime)
        return strategy_name in allowed

    def get_position_size_multiplier(self, regime: MarketRegime) -> float:
        """Get position size multiplier based on regime confidence.

        In transition zones, reduce position size.

        Args:
            regime: Current market regime

        Returns:
            Multiplier (0.0 to 1.0) for position sizing
        """
        if regime == MarketRegime.TRENDING:
            return 1.0  # Full position size
        elif regime == MarketRegime.RANGING:
            return 1.0  # Full position size
        else:  # TRANSITION or UNKNOWN
            return 0.5  # Half position size in uncertain conditions
