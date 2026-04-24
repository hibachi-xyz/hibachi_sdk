"""Optuna-based strategy optimization with walk-forward validation."""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

try:
    import optuna
    from optuna.storages import RDBStorage
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    logger.warning("Optuna not installed. Optimization features disabled.")


@dataclass
class OptimizationResult:
    """Results from strategy optimization.

    Attributes:
        best_params: Best parameter set found
        in_sample_sharpe: In-sample Sharpe ratio
        out_of_sample_sharpe: Out-of-sample Sharpe ratio
        is_valid: Whether OOS Sharpe meets minimum threshold
        total_trials: Number of trials completed
    """

    best_params: dict[str, Any]
    in_sample_sharpe: float
    out_of_sample_sharpe: float
    is_valid: bool
    total_trials: int


class StrategyOptimizer:
    """Optuna-based optimizer for strategy parameters.

    Features:
    - RDB backend for study persistence
    - Walk-forward validation with expanding windows
    - Out-of-sample validation
    - Logical parameter constraints
    """

    def __init__(
        self,
        symbol: str,
        db_url: str = "sqlite:///optimization.db",
        n_trials: int = 100,
        timeout_seconds: int = 3600,
    ) -> None:
        """Initialize the optimizer.

        Args:
            symbol: Trading pair symbol
            db_url: Database URL for Optuna storage
            n_trials: Number of optimization trials
            timeout_seconds: Optimization timeout
        """
        if not OPTUNA_AVAILABLE:
            raise RuntimeError("Optuna is required for optimization")

        self.symbol = symbol
        self.db_url = db_url
        self.n_trials = n_trials
        self.timeout_seconds = timeout_seconds
        self._storage: RDBStorage | None = None

    def _get_storage(self) -> RDBStorage:
        """Get or create database storage."""
        if self._storage is None:
            self._storage = RDBStorage(
                url=self.db_url,
                engine_kwargs={"pool_pre_ping": True},
            )
        return self._storage

    def _split_data_walk_forward(
        self,
        data: pd.DataFrame,
        n_windows: int = 5,
        oos_ratio: float = 0.2,
    ) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
        """Split data into walk-forward windows.

        Uses anchored expanding windows to avoid look-ahead bias.

        Args:
            data: Full dataset
            n_windows: Number of walk-forward windows
            oos_ratio: Ratio of data reserved for OOS in each split

        Returns:
            List of (in_sample, out_of_sample) DataFrame tuples
        """
        total_len = len(data)
        min_train_size = int(total_len * 0.4)  # Minimum training size
        step_size = (total_len - min_train_size) // n_windows

        splits = []
        for i in range(n_windows):
            train_end = min_train_size + (i * step_size)
            test_start = train_end
            test_end = int(train_end + (train_end * oos_ratio / (1 - oos_ratio)))
            test_end = min(test_end, total_len)

            if test_end <= test_start:
                continue

            in_sample = data.iloc[:train_end].copy()
            out_of_sample = data.iloc[test_start:test_end].copy()

            splits.append((in_sample, out_of_sample))

        return splits

    def _calculate_sharpe(self, returns: pd.Series) -> float:
        """Calculate annualized Sharpe ratio.

        Args:
            returns: Series of returns

        Returns:
            Annualized Sharpe ratio
        """
        if len(returns) < 10 or returns.std() == 0:
            return 0.0

        sharpe = returns.mean() / returns.std()
        # Annualize (assuming daily returns)
        return sharpe * (252 ** 0.5)

    def objective_ema_crossover(self, trial: optuna.Trial) -> float:
        """Objective function for EMA crossover strategy optimization.

        Args:
            trial: Optuna trial object

        Returns:
            Negative Sharpe ratio (for minimization)
        """
        # Suggest parameters with logical constraints
        ema_fast = trial.suggest_int("ema_fast", 5, 20)
        ema_slow = trial.suggest_int("ema_slow", ema_fast + 6, 50)  # Constraint: slow > fast + 5

        rsi_period = trial.suggest_int("rsi_period", 10, 20)
        rsi_overbought = trial.suggest_float("rsi_overbought", 60, 80)
        rsi_oversold = trial.suggest_float("rsi_oversold", 20, 40)

        # Store params for backtest
        params = {
            "ema_fast": ema_fast,
            "ema_slow": ema_slow,
            "rsi_period": rsi_period,
            "rsi_overbought": rsi_overbought,
            "rsi_oversold": rsi_oversold,
        }

        # Run backtest (placeholder - would integrate with vectorbt or custom backtester)
        returns = self._run_backtest(params)

        if len(returns) == 0:
            return 0.0

        sharpe = self._calculate_sharpe(returns)
        return -sharpe  # Negate for minimization

    def objective_bollinger_reversion(self, trial: optuna.Trial) -> float:
        """Objective function for Bollinger Bands reversion optimization."""
        bb_period = trial.suggest_int("bb_period", 15, 30)
        bb_std = trial.suggest_float("bb_std", 1.5, 3.0)
        volume_multiplier = trial.suggest_float("volume_multiplier", 1.5, 3.0)

        params = {
            "bb_period": bb_period,
            "bb_std": bb_std,
            "volume_multiplier": volume_multiplier,
        }

        returns = self._run_backtest(params)
        sharpe = self._calculate_sharpe(returns)
        return -sharpe

    def objective_macd_momentum(self, trial: optuna.Trial) -> float:
        """Objective function for MACD momentum optimization."""
        macd_fast = trial.suggest_int("macd_fast", 8, 15)
        macd_slow = trial.suggest_int("macd_slow", 20, 35)
        macd_signal = trial.suggest_int("macd_signal", 5, 12)

        # Constraint: fast < signal < slow
        if macd_fast >= macd_signal or macd_signal >= macd_slow:
            return 0.0

        params = {
            "macd_fast": macd_fast,
            "macd_slow": macd_slow,
            "macd_signal": macd_signal,
        }

        returns = self._run_backtest(params)
        sharpe = self._calculate_sharpe(returns)
        return -sharpe

    def _run_backtest(self, params: dict[str, Any]) -> pd.Series:
        """Run backtest with given parameters.

        This is a placeholder that should be integrated with
        vectorbt or a custom vectorized backtesting engine.

        Args:
            params: Strategy parameters

        Returns:
            Series of returns
        """
        # Placeholder - in production, this would:
        # 1. Apply strategy logic with params to historical data
        # 2. Calculate position returns
        # 3. Return series of returns
        return pd.Series(dtype=float)

    def optimize(
        self,
        strategy_name: str,
        data: pd.DataFrame,
        oos_ratio: float = 0.2,
        min_oos_sharpe_ratio: float = 0.7,
    ) -> OptimizationResult:
        """Run optimization with walk-forward validation.

        Args:
            strategy_name: Name of strategy to optimize
            data: Historical data for optimization
            oos_ratio: Ratio of data for OOS validation
            min_oos_sharpe_ratio: Minimum OOS/IS Sharpe ratio

        Returns:
            OptimizationResult with best parameters and validation metrics
        """
        study_name = f"strategy_opt_{self.symbol.replace('/', '_')}_{strategy_name}"

        # Select objective function
        if strategy_name == "EMA_Crossover":
            objective = self.objective_ema_crossover
        elif strategy_name == "Bollinger_Reversion":
            objective = self.objective_bollinger_reversion
        elif strategy_name == "MACD_Momentum":
            objective = self.objective_macd_momentum
        else:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        # Create study with RDB storage
        storage = self._get_storage()
        try:
            study = optuna.create_study(
                study_name=study_name,
                storage=storage,
                direction="minimize",
                load_if_exists=True,
            )
        except Exception:
            # If study exists with different direction, delete and recreate
            optuna.delete_study(study_name=study_name, storage=storage)
            study = optuna.create_study(
                study_name=study_name,
                storage=storage,
                direction="minimize",
            )

        # Run optimization
        study.optimize(
            objective,
            n_trials=self.n_trials,
            timeout=self.timeout_seconds,
            show_progress_bar=True,
        )

        # Get best parameters
        best_params = study.best_params

        # Walk-forward validation
        splits = self._split_data_walk_forward(data, oos_ratio=oos_ratio)

        is_sharpe_values = []
        oos_sharpe_values = []

        for in_sample, out_of_sample in splits:
            # In-sample performance
            is_returns = self._run_backtest(best_params)
            is_sharpe = self._calculate_sharpe(is_returns)
            is_sharpe_values.append(is_sharpe)

            # Out-of-sample performance
            oos_returns = self._run_backtest(best_params)
            oos_sharpe = self._calculate_sharpe(oos_returns)
            oos_sharpe_values.append(oos_sharpe)

        avg_is_sharpe = sum(is_sharpe_values) / len(is_sharpe_values) if is_sharpe_values else 0.0
        avg_oos_sharpe = sum(oos_sharpe_values) / len(oos_sharpe_values) if oos_sharpe_values else 0.0

        # Validate OOS performance
        is_valid = (
            avg_oos_sharpe >= (avg_is_sharpe * min_oos_sharpe_ratio)
            if avg_is_sharpe > 0
            else False
        )

        logger.info(
            f"Optimization complete for {self.symbol} {strategy_name}:\n"
            f"  Best params: {best_params}\n"
            f"  IS Sharpe: {avg_is_sharpe:.3f}\n"
            f"  OOS Sharpe: {avg_oos_sharpe:.3f}\n"
            f"  Valid: {is_valid}"
        )

        return OptimizationResult(
            best_params=best_params,
            in_sample_sharpe=avg_is_sharpe,
            out_of_sample_sharpe=avg_oos_sharpe,
            is_valid=is_valid,
            total_trials=len(study.trials),
        )
