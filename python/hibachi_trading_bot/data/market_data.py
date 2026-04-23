"""Market data management with multi-timeframe support."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

import pandas as pd


@dataclass
class OHLCVData:
    """OHLCV candlestick data.

    Attributes:
        timestamp: Unix timestamp in seconds
        open: Open price
        high: High price
        low: Low price
        close: Close price
        volume: Trading volume
    """

    timestamp: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    @classmethod
    def from_dict(cls, data: dict) -> "OHLCVData":
        """Create OHLCVData from a dictionary.

        Args:
            data: Dictionary with OHLCV fields

        Returns:
            OHLCVData instance
        """
        return cls(
            timestamp=int(data["timestamp"]),
            open=Decimal(str(data["open"])),
            high=Decimal(str(data["high"])),
            low=Decimal(str(data["low"])),
            close=Decimal(str(data["close"])),
            volume=Decimal(str(data["volume"])),
        )


@dataclass
class MultiTimeframeData:
    """Multi-timeframe data container for MTF analysis.

    Attributes:
        symbol: Trading pair symbol
        htf_data: Higher timeframe DataFrame (Daily/Weekly)
        itf_data: Intermediate timeframe DataFrame (4h/1h)
        ltf_data: Lower timeframe DataFrame (1h/15m)
    """

    symbol: str
    htf_data: pd.DataFrame = field(default_factory=pd.DataFrame)
    itf_data: pd.DataFrame = field(default_factory=pd.DataFrame)
    ltf_data: pd.DataFrame = field(default_factory=pd.DataFrame)


class MarketDataManager:
    """Manages market data collection and multi-timeframe analysis.

    This class handles:
    - Fetching kline data from Hibachi DEX
    - Organizing data by timeframe
    - Computing technical indicators
    - Maintaining data freshness
    """

    def __init__(self) -> None:
        """Initialize the MarketDataManager."""
        self._data_cache: dict[str, MultiTimeframeData] = {}
        self._indicator_cache: dict[str, dict[str, pd.DataFrame]] = {}

    def update_data(
        self,
        symbol: str,
        htf_data: pd.DataFrame,
        itf_data: pd.DataFrame,
        ltf_data: pd.DataFrame,
    ) -> None:
        """Update market data for a symbol.

        Args:
            symbol: Trading pair symbol
            htf_data: Higher timeframe OHLCV DataFrame
            itf_data: Intermediate timeframe OHLCV DataFrame
            ltf_data: Lower timeframe OHLCV DataFrame
        """
        self._data_cache[symbol] = MultiTimeframeData(
            symbol=symbol,
            htf_data=htf_data,
            itf_data=itf_data,
            ltf_data=ltf_data,
        )
        # Clear indicator cache for this symbol when data updates
        if symbol in self._indicator_cache:
            del self._indicator_cache[symbol]

    def get_data(self, symbol: str) -> MultiTimeframeData | None:
        """Get cached market data for a symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            MultiTimeframeData or None if not available
        """
        return self._data_cache.get(symbol)

    def compute_indicators(
        self,
        symbol: str,
        timeframe: Literal["htf", "itf", "ltf"],
        config: "AssetConfig",  # type: ignore[name-defined]
    ) -> pd.DataFrame:
        """Compute technical indicators for a symbol and timeframe.

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe level (htf, itf, ltf)
            config: Asset configuration with indicator parameters

        Returns:
            DataFrame with computed indicators

        Raises:
            ValueError: If data is not available for the symbol
        """
        mtf_data = self.get_data(symbol)
        if mtf_data is None:
            raise ValueError(f"No data available for symbol: {symbol}")

        # Select appropriate dataframe based on timeframe
        if timeframe == "htf":
            df = mtf_data.htf_data.copy()
        elif timeframe == "itf":
            df = mtf_data.itf_data.copy()
        else:  # ltf
            df = mtf_data.ltf_data.copy()

        if df.empty:
            return df

        # Compute ADX for regime filter
        df = self._compute_adx(df, period=14)

        # Compute EMA for Strategy 1
        df = self._compute_ema(
            df, fast_period=config.ema_fast, slow_period=config.ema_slow
        )

        # Compute Bollinger Bands for Strategy 2
        df = self._compute_bollinger_bands(
            df, period=config.bb_period, std_dev=config.bb_std
        )

        # Compute MACD for Strategy 3
        df = self._compute_macd(
            df,
            fast_period=config.macd_fast,
            slow_period=config.macd_slow,
            signal_period=config.macd_signal,
        )

        # Compute RSI for quality filter
        df = self._compute_rsi(df, period=config.rsi_period)

        # Compute ATR for adaptive sizing
        df = self._compute_atr(df, period=config.atr_period)

        return df

    def _compute_adx(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Compute Average Directional Index (ADX).

        Args:
            df: DataFrame with OHLCV data
            period: ADX calculation period

        Returns:
            DataFrame with ADX column added
        """
        # Calculate True Range
        df["high_low"] = df["high"] - df["low"]
        df["high_close"] = abs(df["high"] - df["close"].shift())
        df["low_close"] = abs(df["low"] - df["close"].shift())
        df["tr"] = df[["high_low", "high_close", "low_close"]].max(axis=1)

        # Calculate Directional Movement
        df["up_move"] = df["high"] - df["high"].shift()
        df["down_move"] = df["low"].shift() - df["low"]

        df["plus_dm"] = ((df["up_move"] > df["down_move"]) & (df["up_move"] > 0)).astype(
            float
        ) * df["up_move"]
        df["minus_dm"] = (
            (df["down_move"] > df["up_move"]) & (df["down_move"] > 0)
        ).astype(float) * df["down_move"]

        # Smooth with EMA
        df["+di"] = 100 * (
            df["+dm"].ewm(span=period, adjust=False).mean()
            / df["tr"].ewm(span=period, adjust=False).mean()
        )
        df["-di"] = 100 * (
            df["-dm"].ewm(span=period, adjust=False).mean()
            / df["tr"].ewm(span=period, adjust=False).mean()
        )

        # Calculate DX and ADX
        df["dx"] = 100 * abs(df["+di"] - df["-di"]) / (df["+di"] + df["-di"])
        df["adx"] = df["dx"].ewm(span=period, adjust=False).mean()

        return df

    def _compute_ema(
        self, df: pd.DataFrame, fast_period: int = 9, slow_period: int = 21
    ) -> pd.DataFrame:
        """Compute Exponential Moving Averages.

        Args:
            df: DataFrame with OHLCV data
            fast_period: Fast EMA period
            slow_period: Slow EMA period

        Returns:
            DataFrame with EMA columns added
        """
        df[f"ema_fast_{fast_period}"] = df["close"].ewm(
            span=fast_period, adjust=False
        ).mean()
        df[f"ema_slow_{slow_period}"] = df["close"].ewm(
            span=slow_period, adjust=False
        ).mean()
        df["ema_crossover"] = df[f"ema_fast_{fast_period}"] - df[
            f"ema_slow_{slow_period}"
        ]
        return df

    def _compute_bollinger_bands(
        self, df: pd.DataFrame, period: int = 20, std_dev: float = 2.0
    ) -> pd.DataFrame:
        """Compute Bollinger Bands.

        Args:
            df: DataFrame with OHLCV data
            period: BB period
            std_dev: Standard deviation multiplier

        Returns:
            DataFrame with BB columns added
        """
        df["bb_middle"] = df["close"].rolling(window=period).mean()
        bb_std = df["close"].rolling(window=period).std()
        df["bb_upper"] = df["bb_middle"] + (std_dev * bb_std)
        df["bb_lower"] = df["bb_middle"] - (std_dev * bb_std)
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]
        df["bb_position"] = (df["close"] - df["bb_lower"]) / (
            df["bb_upper"] - df["bb_lower"]
        )
        return df

    def _compute_macd(
        self,
        df: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> pd.DataFrame:
        """Compute MACD indicator.

        Args:
            df: DataFrame with OHLCV data
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line period

        Returns:
            DataFrame with MACD columns added
        """
        ema_fast = df["close"].ewm(span=fast_period, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow_period, adjust=False).mean()
        df["macd"] = ema_fast - ema_slow
        df["macd_signal"] = df["macd"].ewm(span=signal_period, adjust=False).mean()
        df["macd_histogram"] = df["macd"] - df["macd_signal"]
        return df

    def _compute_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Compute Relative Strength Index.

        Args:
            df: DataFrame with OHLCV data
            period: RSI period

        Returns:
            DataFrame with RSI column added
        """
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()

        rs = avg_gain / avg_loss
        df["rsi"] = 100 - (100 / (1 + rs))
        return df

    def _compute_atr(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Compute Average True Range.

        Args:
            df: DataFrame with OHLCV data
            period: ATR period

        Returns:
            DataFrame with ATR column added
        """
        high_low = df["high"] - df["low"]
        high_close = abs(df["high"] - df["close"].shift())
        low_close = abs(df["low"] - df["close"].shift())

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df["atr"] = true_range.ewm(span=period, adjust=False).mean()
        return df
