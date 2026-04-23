"""Hibachi Algorithmic Trading Bot.

A multi-asset quantitative trading bot for Hibachi DEX focusing on robustness,
automated optimization, and institutional-grade risk management.
"""

from hibachi_trading_bot.core.bot import HibachiTradingBot
from hibachi_trading_bot.core.config import BotConfig, AssetConfig

__version__ = "1.0.0"
__all__ = [
    "HibachiTradingBot",
    "BotConfig",
    "AssetConfig",
]
