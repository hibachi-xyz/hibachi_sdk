"""Hibachi DEX data exchange integration."""

import asyncio
import logging
from decimal import Decimal
from typing import Any

import pandas as pd

from hibachi_xyz import HibachiApiClient, FutureContract
from hibachi_xyz.types import Interval, Kline

logger = logging.getLogger(__name__)


# Mapping from string interval to Hibachi Interval enum
INTERVAL_MAP: dict[str, Interval] = {
    "1m": Interval.MINUTE_1,
    "3m": Interval.MINUTE_3,
    "5m": Interval.MINUTE_5,
    "15m": Interval.MINUTE_15,
    "30m": Interval.MINUTE_30,
    "1h": Interval.HOUR_1,
    "2h": Interval.HOUR_2,
    "4h": Interval.HOUR_4,
    "6h": Interval.HOUR_6,
    "12h": Interval.HOUR_12,
    "1d": Interval.DAY_1,
    "3d": Interval.DAY_3,
    "1w": Interval.WEEK_1,
    "1M": Interval.MONTH_1,
}


class HibachiDataExchange:
    """Handles communication with Hibachi DEX for market data and order execution.

    This class wraps the HibachiApiClient and provides:
    - Metadata retrieval (exchange info, fees, decimals)
    - Kline data fetching with proper conversion
    - Price format conversion to 64-bit integers
    - Order placement with proper formatting
    """

    def __init__(
        self,
        api_client: HibachiApiClient,
    ) -> None:
        """Initialize the Hibachi data exchange.

        Args:
            api_client: Initialized Hibachi API client
        """
        self._client = api_client
        self._contracts: dict[str, FutureContract] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the exchange connection and load metadata.

        This must be called before any other operations. It fetches
        exchange info and caches contract metadata.

        Raises:
            RuntimeError: If initialization fails
        """
        try:
            exchange_info = self._client.get_exchange_info()
            for contract in exchange_info.futureContracts:
                self._contracts[contract.symbol] = contract
            self._initialized = True
            logger.info(
                f"Initialized HibachiDataExchange with {len(self._contracts)} contracts"
            )
        except Exception as e:
            logger.error(f"Failed to initialize HibachiDataExchange: {e}")
            raise RuntimeError(f"Initialization failed: {e}") from e

    @property
    def is_initialized(self) -> bool:
        """Check if the exchange is initialized."""
        return self._initialized

    def get_contract(self, symbol: str) -> FutureContract:
        """Get contract metadata for a symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            FutureContract metadata

        Raises:
            ValueError: If symbol is not found or not initialized
        """
        if not self._initialized:
            raise ValueError("Exchange not initialized")
        if symbol not in self._contracts:
            raise ValueError(f"Contract not found for symbol: {symbol}")
        return self._contracts[symbol]

    def price_to_int64(self, price: Decimal, symbol: str) -> int:
        """Convert price to 64-bit integer format for Hibachi DEX.

        Uses the formula: 2^32 * 10^(settlementDecimals - underlyingDecimals)

        Args:
            price: Price as Decimal
            symbol: Trading pair symbol

        Returns:
            Price as 64-bit integer

        Raises:
            ValueError: If symbol not found or price invalid
        """
        contract = self.get_contract(symbol)
        multiplier = (
            Decimal(2) ** 32
            * Decimal(10) ** (contract.settlementDecimals - contract.underlyingDecimals)
        )
        return int(price * multiplier)

    def quantity_to_int64(self, quantity: Decimal, symbol: str) -> int:
        """Convert quantity to 64-bit integer format for Hibachi DEX.

        Args:
            quantity: Quantity as Decimal
            symbol: Trading pair symbol

        Returns:
            Quantity as 64-bit integer

        Raises:
            ValueError: If symbol not found or quantity invalid
        """
        contract = self.get_contract(symbol)
        multiplier = Decimal(10) ** contract.underlyingDecimals
        return int(quantity * multiplier)

    async def fetch_klines(
        self,
        symbol: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """Fetch kline (candlestick) data from Hibachi DEX.

        Args:
            symbol: Trading pair symbol
            interval: Timeframe interval (e.g., "1h", "4h", "1d")
            start_time: Optional start timestamp (Unix seconds)
            end_time: Optional end timestamp (Unix seconds)
            limit: Maximum number of candles to fetch

        Returns:
            DataFrame with OHLCV columns

        Raises:
            ValueError: If interval is invalid or exchange not initialized
        """
        if not self._initialized:
            raise ValueError("Exchange not initialized")

        if interval not in INTERVAL_MAP:
            raise ValueError(
                f"Invalid interval: {interval}. Valid intervals: {list(INTERVAL_MAP.keys())}"
            )

        hibachi_interval = INTERVAL_MAP[interval]

        try:
            # Fetch klines from API
            klines_response = self._client.get_klines(
                symbol=symbol,
                interval=hibachi_interval,
                startTime=start_time,
                endTime=end_time,
                limit=limit,
            )

            # Convert to DataFrame
            data = []
            for kline in klines_response.klines:
                data.append(
                    {
                        "timestamp": kline.startTime,
                        "open": Decimal(str(kline.open)),
                        "high": Decimal(str(kline.high)),
                        "low": Decimal(str(kline.low)),
                        "close": Decimal(str(kline.close)),
                        "volume": Decimal(str(kline.volume)),
                    }
                )

            df = pd.DataFrame(data)
            if not df.empty:
                df.set_index("timestamp", inplace=True)
                df.sort_index(inplace=True)

            logger.debug(
                f"Fetched {len(df)} klines for {symbol} {interval}"
            )
            return df

        except Exception as e:
            logger.error(f"Failed to fetch klines for {symbol} {interval}: {e}")
            raise

    async def fetch_multi_timeframe_data(
        self,
        symbol: str,
        htf_interval: str,
        itf_interval: str,
        ltf_interval: str,
        bars_per_timeframe: int = 500,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Fetch multi-timeframe data for a symbol.

        Args:
            symbol: Trading pair symbol
            htf_interval: Higher timeframe interval
            itf_interval: Intermediate timeframe interval
            ltf_interval: Lower timeframe interval
            bars_per_timeframe: Number of bars to fetch per timeframe

        Returns:
            Tuple of (htf_data, itf_data, ltf_data) DataFrames
        """
        tasks = [
            self.fetch_klines(symbol, htf_interval, limit=bars_per_timeframe),
            self.fetch_klines(symbol, itf_interval, limit=bars_per_timeframe),
            self.fetch_klines(symbol, ltf_interval, limit=bars_per_timeframe),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch timeframe data: {result}")
                raise result

        htf_data, itf_data, ltf_data = results
        return htf_data, itf_data, ltf_data

    def get_fee_rates(self, symbol: str) -> tuple[Decimal, Decimal]:
        """Get maker and taker fee rates for a symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            Tuple of (maker_fee, taker_fee) as Decimals

        Raises:
            ValueError: If exchange not initialized
        """
        if not self._initialized:
            raise ValueError("Exchange not initialized")

        # Get fee config from exchange info
        # Note: In practice, you'd cache this from get_exchange_info()
        exchange_info = self._client.get_exchange_info()
        maker_fee = Decimal(str(exchange_info.feeConfig.tradeMakerFeeRate))
        taker_fee = Decimal(str(exchange_info.feeConfig.tradeTakerFeeRate))
        return maker_fee, taker_fee
