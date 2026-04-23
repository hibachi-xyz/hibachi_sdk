"""Telegram bot for trading notifications."""

import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends trading notifications via Telegram Bot API.

    Supports:
    - Trade execution notifications
    - System health heartbeats
    - Daily PnL reports
    - Market regime shift alerts
    """

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        base_url: str = "https://api.telegram.org",
    ) -> None:
        """Initialize the Telegram notifier.

        Args:
            bot_token: Telegram bot API token
            chat_id: Target chat ID for notifications
            base_url: Telegram API base URL
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = base_url
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def send_message(
        self,
        message: str,
        parse_mode: str = "HTML",
    ) -> bool:
        """Send a message to the configured chat.

        Args:
            message: Message text (supports HTML formatting)
            parse_mode: Message parse mode (HTML or Markdown)

        Returns:
            True if message sent successfully
        """
        url = f"{self.base_url}/bot{self.bot_token}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode,
        }

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.debug(f"Telegram message sent: {message[:50]}...")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Telegram API error ({response.status}): {error_text}")
                    return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    async def send_trade_notification(
        self,
        action: str,
        symbol: str,
        direction: str,
        quantity: str,
        price: str,
        stop_loss: str | None = None,
        take_profit: str | None = None,
    ) -> bool:
        """Send trade execution notification.

        Args:
            action: Action type (OPENED, CLOSED)
            symbol: Trading pair symbol
            direction: Long or Short
            quantity: Position quantity
            price: Entry/exit price
            stop_loss: Stop loss price (for opens)
            take_profit: Take profit price (for opens)

        Returns:
            True if sent successfully
        """
        emoji = "🟢" if action == "OPENED" else "🔴"
        message = f"{emoji} <b>Position {action}</b>\n\n"
        message += f"Symbol: <code>{symbol}</code>\n"
        message += f"Direction: <b>{direction}</b>\n"
        message += f"Quantity: <code>{quantity}</code>\n"
        message += f"Price: <code>{price}</code>"

        if stop_loss:
            message += f"\nStop Loss: <code>{stop_loss}</code>"
        if take_profit:
            message += f"\nTake Profit: <code>{take_profit}</code>"

        return await self.send_message(message)

    async def send_pnl_report(
        self,
        total_pnl: str,
        realized_pnl: str,
        unrealized_pnl: str,
        win_rate: str,
        num_trades: int,
    ) -> bool:
        """Send daily PnL report.

        Args:
            total_pnl: Total PnL
            realized_pnl: Realized PnL
            unrealized_pnl: Unrealized PnL
            win_rate: Win rate percentage
            num_trades: Number of trades

        Returns:
            True if sent successfully
        """
        color = "🟢" if float(total_pnl.replace("%", "")) > 0 else "🔴"
        message = f"{color} <b>Daily PnL Report</b>\n\n"
        message += f"Total PnL: <b>{total_pnl}</b>\n"
        message += f"Realized: <code>{realized_pnl}</code>\n"
        message += f"Unrealized: <code>{unrealized_pnl}</code>\n"
        message += f"Win Rate: <b>{win_rate}</b>\n"
        message += f"Trades: <code>{num_trades}</code>"

        return await self.send_message(message)

    async def send_regime_alert(
        self,
        symbol: str,
        old_regime: str,
        new_regime: str,
        adx_value: float,
    ) -> bool:
        """Send market regime shift alert.

        Args:
            symbol: Trading pair symbol
            old_regime: Previous regime
            new_regime: New regime
            adx_value: Current ADX value

        Returns:
            True if sent successfully
        """
        message = f"⚠️ <b>Regime Shift Alert</b>\n\n"
        message += f"Symbol: <code>{symbol}</code>\n"
        message += f"Changed: <b>{old_regime}</b> → <b>{new_regime}</b>\n"
        message += f"ADX: <code>{adx_value:.2f}</code>"

        return await self.send_message(message)

    async def send_heartbeat(self, uptime_hours: float) -> bool:
        """Send system health heartbeat.

        Args:
            uptime_hours: System uptime in hours

        Returns:
            True if sent successfully
        """
        message = f"💓 <b>Bot Heartbeat</b>\n\n"
        message += f"Status: <b>Running</b>\n"
        message += f"Uptime: <code>{uptime_hours:.1f} hours</code>"

        return await self.send_message(message)

    async def send_error_alert(self, error_message: str) -> bool:
        """Send error alert.

        Args:
            error_message: Error description

        Returns:
            True if sent successfully
        """
        message = f"🚨 <b>Error Alert</b>\n\n"
        message += f"<code>{error_message[:200]}</code>"

        return await self.send_message(message)
