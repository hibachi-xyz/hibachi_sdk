"""Trading strategies module."""

from hibachi_trading_bot.strategies.base import Signal, SignalType, Strategy
from hibachi_trading_bot.strategies.ema_crossover import EMACrossoverStrategy
from hibachi_trading_bot.strategies.bollinger_reversion import BollingerReversionStrategy
from hibachi_trading_bot.strategies.macd_momentum import MACDMomentumStrategy
from hibachi_trading_bot.strategies.regime_filter import RegimeFilter

__all__ = [
    "Signal",
    "SignalType",
    "Strategy",
    "EMACrossoverStrategy",
    "BollingerReversionStrategy",
    "MACDMomentumStrategy",
    "RegimeFilter",
]
