"""Configuration classes for the Hibachi Trading Bot."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal


@dataclass
class AssetConfig:
    """Configuration for a single trading asset.

    Attributes:
        symbol: Trading pair symbol (e.g., "BTC/USDT-P")
        htf_interval: Higher timeframe interval for bias determination
        itf_interval: Intermediate timeframe for signal generation
        ltf_interval: Lower timeframe for entry refinement
        adx_threshold_trend: ADX threshold above which market is considered trending
        adx_threshold_range: ADX threshold below which market is considered ranging
        ema_fast: Fast EMA period for Strategy 1
        ema_slow: Slow EMA period for Strategy 1
        bb_period: Bollinger Bands period for Strategy 2
        bb_std: Bollinger Bands standard deviations for Strategy 2
        macd_fast: MACD fast period for Strategy 3
        macd_slow: MACD slow period for Strategy 3
        macd_signal: MACD signal period for Strategy 3
        rsi_period: RSI period for quality filter
        rsi_overbought: RSI overbought threshold
        rsi_oversold: RSI oversold threshold
        atr_period: ATR period for adaptive sizing
        volume_spike_multiplier: Volume spike detection multiplier
    """

    symbol: str
    htf_interval: str = "1d"
    itf_interval: str = "4h"
    ltf_interval: str = "15m"
    adx_threshold_trend: float = 25.0
    adx_threshold_range: float = 20.0
    ema_fast: int = 9
    ema_slow: int = 21
    bb_period: int = 20
    bb_std: float = 2.0
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    atr_period: int = 14
    volume_spike_multiplier: float = 2.0

    def __post_init__(self) -> None:
        """Validate configuration constraints."""
        if self.ema_slow <= self.ema_fast + 5:
            raise ValueError(
                f"ema_slow ({self.ema_slow}) must be > ema_fast + 5 ({self.ema_fast + 5})"
            )
        if self.adx_threshold_trend <= self.adx_threshold_range:
            raise ValueError(
                f"adx_threshold_trend ({self.adx_threshold_trend}) must be > "
                f"adx_threshold_range ({self.adx_threshold_range})"
            )


@dataclass
class RiskConfig:
    """Global risk management configuration.

    Attributes:
        max_positions: Maximum number of simultaneous open positions
        position_size_percent: Percentage of capital per position (as decimal, e.g., 0.15 for 15%)
        max_exposure_percent: Maximum total exposure percentage (as decimal)
        default_stop_loss_atr_mult: Default stop loss as multiple of ATR
        default_take_profit_atr_mult: Default take profit as multiple of ATR
        min_tp_sl_ratio: Minimum take profit to stop loss ratio
    """

    max_positions: int = 3
    position_size_percent: Decimal = Decimal("0.15")
    max_exposure_percent: Decimal = Decimal("0.45")
    default_stop_loss_atr_mult: Decimal = Decimal("2.0")
    default_take_profit_atr_mult: Decimal = Decimal("4.0")
    min_tp_sl_ratio: Decimal = Decimal("1.5")

    def __post_init__(self) -> None:
        """Validate risk configuration constraints."""
        if self.max_positions < 1:
            raise ValueError("max_positions must be at least 1")
        if not Decimal("0") < self.position_size_percent <= Decimal("1"):
            raise ValueError("position_size_percent must be between 0 and 1")
        if not Decimal("0") < self.max_exposure_percent <= Decimal("1"):
            raise ValueError("max_exposure_percent must be between 0 and 1")
        expected_max = self.max_positions * self.position_size_percent
        if self.max_exposure_percent < expected_max:
            raise ValueError(
                f"max_exposure_percent ({self.max_exposure_percent}) must be >= "
                f"max_positions * position_size_percent ({expected_max})"
            )


@dataclass
class OptimizationConfig:
    """Optuna optimization configuration.

    Attributes:
        db_url: Database URL for Optuna study storage
        n_trials: Number of optimization trials
        timeout_seconds: Timeout for optimization in seconds
        oos_ratio: Ratio of data reserved for out-of-sample validation
        min_oos_sharpe_ratio: Minimum OOS Sharpe ratio relative to IS Sharpe
        walk_forward_windows: Number of walk-forward validation windows
    """

    db_url: str = "sqlite:///optimization.db"
    n_trials: int = 100
    timeout_seconds: int = 3600
    oos_ratio: float = 0.2
    min_oos_sharpe_ratio: float = 0.7
    walk_forward_windows: int = 5


@dataclass
class TelegramConfig:
    """Telegram bot configuration for notifications.

    Attributes:
        enabled: Whether Telegram notifications are enabled
        bot_token: Telegram bot API token
        chat_id: Telegram chat ID for notifications
    """

    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


@dataclass
class BotConfig:
    """Main bot configuration.

    Attributes:
        assets: List of asset configurations
        risk: Risk management configuration
        optimization: Optimization configuration
        telegram: Telegram notification configuration
        api_url: Hibachi API URL
        data_api_url: Hibachi data API URL
        account_id: Hibachi account ID
        api_key: Hibachi API key
        private_key: Private key for signing requests
    """

    assets: list[AssetConfig] = field(default_factory=list)
    risk: RiskConfig = field(default_factory=RiskConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    api_url: str = "https://api.hibachi.xyz"
    data_api_url: str = "https://data-api.hibachi.xyz"
    account_id: int | None = None
    api_key: str | None = None
    private_key: str | None = None

    @classmethod
    def default_config(cls) -> "BotConfig":
        """Create a default configuration for BTC, ETH, and SOL trading.

        Returns:
            BotConfig: Default configuration with three assets
        """
        return cls(
            assets=[
                AssetConfig(symbol="BTC/USDT-P"),
                AssetConfig(symbol="ETH/USDT-P"),
                AssetConfig(symbol="SOL/USDT-P"),
            ],
        )
