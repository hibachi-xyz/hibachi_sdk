"""Main trading bot orchestration."""

import asyncio
import logging
from decimal import Decimal
from typing import Any

from hibachi_xyz import HibachiApiClient

from hibachi_trading_bot.core.config import BotConfig
from hibachi_trading_bot.data.hibachi_client import HibachiDataExchange
from hibachi_trading_bot.data.market_data import MarketDataManager
from hibachi_trading_bot.risk.portfolio_manager import PortfolioManager
from hibachi_trading_bot.strategies.base import Signal, SignalType
from hibachi_trading_bot.strategies.bollinger_reversion import BollingerReversionStrategy
from hibachi_trading_bot.strategies.ema_crossover import EMACrossoverStrategy
from hibachi_trading_bot.strategies.macd_momentum import MACDMomentumStrategy
from hibachi_trading_bot.strategies.regime_filter import MarketRegime, RegimeFilter
from hibachi_trading_bot.telemetry.telegram_bot import TelegramNotifier

logger = logging.getLogger(__name__)


class HibachiTradingBot:
    """Main algorithmic trading bot for Hibachi DEX.

    Orchestrates:
    - Multi-timeframe data collection
    - Market regime detection
    - Strategy selection and signal generation
    - Risk management and position sizing
    - Order execution
    - Telemetry and notifications
    """

    def __init__(self, config: BotConfig) -> None:
        """Initialize the trading bot.

        Args:
            config: Bot configuration
        """
        self.config = config
        self._api_client = HibachiApiClient(
            api_url=config.api_url,
            data_api_url=config.data_api_url,
            account_id=config.account_id,
            api_key=config.api_key,
            private_key=config.private_key,
        )
        self._exchange: HibachiDataExchange | None = None
        self._market_data = MarketDataManager()
        self._portfolio = PortfolioManager(config.risk)
        self._regime_filters: dict[str, RegimeFilter] = {}
        self._strategies: dict[str, Any] = {}
        self._telegram: TelegramNotifier | None = None
        self._running = False

        # Initialize strategies for each asset
        for asset_config in config.assets:
            self._regime_filters[asset_config.symbol] = RegimeFilter(
                adx_threshold_trend=asset_config.adx_threshold_trend,
                adx_threshold_range=asset_config.adx_threshold_range,
            )
            self._strategies[asset_config.symbol] = {
                "ema": EMACrossoverStrategy(
                    ema_fast=asset_config.ema_fast,
                    ema_slow=asset_config.ema_slow,
                    rsi_period=asset_config.rsi_period,
                    rsi_overbought=asset_config.rsi_overbought,
                    rsi_oversold=asset_config.rsi_oversold,
                ),
                "bb": BollingerReversionStrategy(
                    bb_period=asset_config.bb_period,
                    bb_std=asset_config.bb_std,
                    volume_spike_multiplier=asset_config.volume_spike_multiplier,
                ),
                "macd": MACDMomentumStrategy(
                    macd_fast=asset_config.macd_fast,
                    macd_slow=asset_config.macd_slow,
                    macd_signal=asset_config.macd_signal,
                    atr_period=asset_config.atr_period,
                ),
            }

        if config.telegram.enabled:
            self._telegram = TelegramNotifier(
                bot_token=config.telegram.bot_token,
                chat_id=config.telegram.chat_id,
            )

    async def initialize(self) -> None:
        """Initialize the bot and all components."""
        logger.info("Initializing HibachiTradingBot...")

        # Initialize exchange connection
        self._exchange = HibachiDataExchange(self._api_client)
        await self._exchange.initialize()

        # Update portfolio with current capital
        try:
            account_info = self._api_client.get_account_info()
            capital = Decimal(str(account_info.balance))
            self._portfolio.update_capital(capital)
            logger.info(f"Initial capital: {capital} USDT")
        except Exception as e:
            logger.warning(f"Could not fetch account info: {e}")

        if self._telegram:
            await self._telegram.send_message(
                "🤖 Trading Bot Started\n"
                f"Capital: {self._portfolio.total_capital} USDT\n"
                f"Assets: {[a.symbol for a in self.config.assets]}"
            )

        logger.info("HibachiTradingBot initialized successfully")

    async def _update_market_data(self) -> None:
        """Update market data for all configured assets."""
        if not self._exchange:
            raise RuntimeError("Exchange not initialized")

        tasks = []
        for asset_config in self.config.assets:
            task = self._exchange.fetch_multi_timeframe_data(
                symbol=asset_config.symbol,
                htf_interval=asset_config.htf_interval,
                itf_interval=asset_config.itf_interval,
                ltf_interval=asset_config.ltf_interval,
            )
            tasks.append((asset_config, task))

        results = await asyncio.gather(
            *[t[1] for t in tasks], return_exceptions=True
        )

        for (asset_config, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch data for {asset_config.symbol}: {result}")
                continue

            htf_data, itf_data, ltf_data = result
            self._market_data.update_data(
                symbol=asset_config.symbol,
                htf_data=htf_data,
                itf_data=itf_data,
                ltf_data=ltf_data,
            )

    def _get_htf_bias(self, symbol: str) -> str | None:
        """Get higher timeframe bias for a symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            'bullish', 'bearish', or None
        """
        mtf_data = self._market_data.get_data(symbol)
        if mtf_data is None or mtf_data.htf_data.empty:
            return None

        htf_df = mtf_data.htf_data
        if len(htf_df) < 2:
            return None

        # Simple bias: compare close prices
        current_close = float(htf_df["close"].iloc[-1])
        prev_close = float(htf_df["close"].iloc[-2])

        if current_close > prev_close:
            return "bullish"
        elif current_close < prev_close:
            return "bearish"
        return None

    async def _evaluate_signals(self, asset_config: Any) -> Signal | None:
        """Evaluate trading signals for an asset.

        Args:
            asset_config: Asset configuration

        Returns:
            Signal or None
        """
        symbol = asset_config.symbol
        regime_filter = self._regime_filters[symbol]
        strategies = self._strategies[symbol]

        # Get current price
        mtf_data = self._market_data.get_data(symbol)
        if mtf_data is None or mtf_data.ltf_data.empty:
            return None

        current_price = Decimal(str(mtf_data.ltf_data["close"].iloc[-1]))

        # Compute indicators on ITF data
        itf_indicators = self._market_data.compute_indicators(
            symbol=symbol,
            timeframe="itf",
            config=asset_config,
        )

        # Get market regime
        regime_state = regime_filter.classify_regime(symbol, itf_indicators)

        # Get HTF bias
        htf_bias = self._get_htf_bias(symbol)

        # Select strategy based on regime
        if regime_state.regime == MarketRegime.TRENDING:
            # Use trend-following strategies (S1 or S3)
            primary_strategy = strategies["ema"]
            secondary_strategy = strategies["macd"]
        elif regime_state.regime == MarketRegime.RANGING:
            # Use mean-reversion strategy (S2)
            primary_strategy = strategies["bb"]
            secondary_strategy = None
        else:
            # Transition zone - no trading
            logger.info(f"{symbol}: In transition zone, skipping")
            return None

        # Get current position
        position_info = self._portfolio.get_position(symbol)
        position_dict = None
        if position_info:
            position_dict = {
                "direction": position_info.direction,
                "quantity": str(position_info.quantity),
            }

        # Generate signal from primary strategy
        signal = primary_strategy.generate_signal(
            symbol=symbol,
            df=itf_indicators,
            current_price=current_price,
            position=position_dict,
        )

        # Validate against HTF bias
        if signal.is_entry and htf_bias:
            if signal.signal_type == SignalType.LONG and htf_bias == "bearish":
                logger.debug(f"{symbol}: Blocking LONG signal (HTF bearish)")
                return None
            if signal.signal_type == SignalType.SHORT and htf_bias == "bullish":
                logger.debug(f"{symbol}: Blocking SHORT signal (HTF bullish)")
                return None

        # Confirm with secondary strategy if available
        if secondary_strategy and signal.is_entry:
            confirm_signal = secondary_strategy.generate_signal(
                symbol=symbol,
                df=itf_indicators,
                current_price=current_price,
                position=position_dict,
            )
            # Require confirmation for entries
            if confirm_signal.signal_type != signal.signal_type:
                logger.debug(f"{symbol}: Signal not confirmed by secondary strategy")
                return None

        return signal

    async def _execute_signal(self, signal: Signal, asset_config: Any) -> bool:
        """Execute a trading signal.

        Args:
            signal: Trading signal
            asset_config: Asset configuration

        Returns:
            True if execution successful
        """
        if not self._exchange:
            return False

        symbol = signal.symbol

        if signal.signal_type == SignalType.NONE:
            return True

        # Handle exits
        if signal.signal_type in (SignalType.CLOSE_LONG, SignalType.CLOSE_SHORT):
            logger.info(f"Closing position for {symbol}")
            # In production, this would call cancel/ClosePosition API
            self._portfolio.remove_position(symbol)
            if self._telegram:
                await self._telegram.send_message(
                    f"🔴 Position Closed\nSymbol: {symbol}\nReason: {signal.metadata.get('reason', 'N/A')}"
                )
            return True

        # Handle entries
        if signal.signal_type in (SignalType.LONG, SignalType.SHORT):
            # Check risk constraints
            can_open, reason = self._portfolio.can_open_position(
                symbol, signal.price * Decimal("0.01")  # Estimate
            )
            if not can_open:
                logger.warning(f"Cannot open position: {reason}")
                return False

            # Calculate position size
            mtf_data = self._market_data.get_data(symbol)
            atr = None
            if mtf_data and not mtf_data.ltf_data.empty and "atr" in mtf_data.ltf_data.columns:
                atr = Decimal(str(mtf_data.ltf_data["atr"].iloc[-1]))

            quantity, stop_loss, take_profit = self._portfolio.calculate_position_size(
                symbol=symbol,
                price=signal.price,
                atr=atr,
            )

            direction = "Long" if signal.signal_type == SignalType.LONG else "Short"

            # Add to portfolio
            success, msg = self._portfolio.add_position(
                symbol=symbol,
                direction=direction,
                quantity=quantity,
                entry_price=signal.price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata=signal.metadata or {},
            )

            if success:
                logger.info(
                    f"Opened {direction} position: {symbol} qty={quantity} @ {signal.price}"
                )
                if self._telegram:
                    await self._telegram.send_message(
                        f"🟢 Position Opened\n"
                        f"Symbol: {symbol}\n"
                        f"Direction: {direction}\n"
                        f"Quantity: {quantity}\n"
                        f"Entry: {signal.price}\n"
                        f"SL: {stop_loss}\n"
                        f"TP: {take_profit}"
                    )
                return True

        return False

    async def run_loop(self) -> None:
        """Main trading loop."""
        self._running = True
        logger.info("Starting trading loop...")

        while self._running:
            try:
                # Update market data
                await self._update_market_data()

                # Evaluate and execute signals for each asset
                for asset_config in self.config.assets:
                    signal = await self._evaluate_signals(asset_config)
                    if signal:
                        await self._execute_signal(signal, asset_config)

                # Update position prices
                for symbol in list(self._portfolio.get_all_positions().keys()):
                    mtf_data = self._market_data.get_data(symbol)
                    if mtf_data and not mtf_data.ltf_data.empty:
                        current_price = Decimal(str(mtf_data.ltf_data["close"].iloc[-1]))
                        self._portfolio.update_position_price(symbol, current_price)

                # Wait for next iteration
                await asyncio.sleep(60)  # 1 minute cycle

            except Exception as e:
                logger.error(f"Error in trading loop: {e}", exc_info=True)
                if self._telegram:
                    await self._telegram.send_message(f"⚠️ Error: {e}")
                await asyncio.sleep(30)

    def stop(self) -> None:
        """Stop the trading loop."""
        self._running = False
        logger.info("Stopping trading bot...")
