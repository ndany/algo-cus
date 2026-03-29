"""
Walk-Forward Backtesting Engine

Walk-forward analysis is the gold standard for validating trading strategies.
Unlike a simple backtest, it simulates how you'd actually use a strategy:
1. Train/optimize on a window of historical data (in-sample).
2. Test on the next unseen period (out-of-sample).
3. Slide the window forward and repeat.

This prevents overfitting because the strategy is always evaluated on data
it has never seen. The key metric is the degradation ratio:
  degradation_ratio = out-of-sample Sharpe / in-sample Sharpe

A ratio close to 1.0 means the strategy generalizes well.
A ratio near 0 or negative means the strategy is overfit.
"""

from dataclasses import dataclass, field
from itertools import product

import numpy as np
import pandas as pd

from backtest.engine import Backtest, calculate_metrics
from strategies.base import Strategy
from config import INITIAL_CAPITAL, COMMISSION, SLIPPAGE


@dataclass
class FoldResult:
    """Results for a single walk-forward fold."""
    fold_index: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    in_sample_metrics: dict
    out_of_sample_metrics: dict
    best_params: dict | None = None


@dataclass
class WalkForwardResult:
    """Aggregated walk-forward analysis results."""
    strategy_name: str
    folds: list[FoldResult] = field(default_factory=list)

    @property
    def n_folds(self) -> int:
        return len(self.folds)

    @property
    def aggregate_oos_metrics(self) -> dict:
        """Average out-of-sample metrics across all folds."""
        if not self.folds:
            return {}
        keys = [k for k in self.folds[0].out_of_sample_metrics if k != "Strategy"]
        result = {"Strategy": self.strategy_name}
        for key in keys:
            values = [f.out_of_sample_metrics[key] for f in self.folds]
            result[key] = round(np.mean(values), 2)
        return result

    @property
    def degradation_ratio(self) -> float:
        """Ratio of out-of-sample to in-sample Sharpe. Closer to 1.0 = better."""
        is_sharpes = [f.in_sample_metrics.get("Sharpe Ratio", 0) for f in self.folds]
        oos_sharpes = [f.out_of_sample_metrics.get("Sharpe Ratio", 0) for f in self.folds]
        avg_is = np.mean(is_sharpes) if is_sharpes else 0
        avg_oos = np.mean(oos_sharpes) if oos_sharpes else 0
        if avg_is == 0:
            return 0.0
        return round(avg_oos / avg_is, 3)

    def summary(self) -> str:
        """Human-readable walk-forward summary."""
        lines = [
            f"\n{'='*60}",
            f"  Walk-Forward Results: {self.strategy_name}",
            f"  Folds: {self.n_folds} | Degradation Ratio: {self.degradation_ratio}",
            f"{'='*60}",
        ]

        agg = self.aggregate_oos_metrics
        lines.append("  Out-of-Sample Averages:")
        for key, value in agg.items():
            if key != "Strategy":
                lines.append(f"    {key:<25} {value:>10}")

        lines.append(f"\n  Per-Fold Breakdown:")
        lines.append(f"  {'Fold':<6} {'IS Sharpe':>10} {'OOS Sharpe':>11} {'OOS Return':>11}")
        for f in self.folds:
            lines.append(
                f"  {f.fold_index:<6} "
                f"{f.in_sample_metrics.get('Sharpe Ratio', 0):>10} "
                f"{f.out_of_sample_metrics.get('Sharpe Ratio', 0):>11} "
                f"{f.out_of_sample_metrics.get('Total Return (%)', 0):>10}%"
            )

        lines.append(f"{'='*60}\n")
        return "\n".join(lines)


class WalkForwardEngine:
    """Walk-forward validation engine.

    Splits data into sequential train/test windows, optionally optimizes
    parameters on the training set, and evaluates on the test set.

    Args:
        n_splits: Number of walk-forward folds.
        train_ratio: Fraction of each window used for training (0-1).
        gap_days: Number of days to skip between train and test sets
            to prevent information leakage at the boundary.
        anchored: If True, training window always starts from the beginning
            (expanding window). If False, uses a rolling window.
        initial_capital: Starting capital for each fold's backtest.
        commission: Commission rate per trade.
        slippage: Slippage rate per trade.
    """

    def __init__(
        self,
        n_splits: int = 5,
        train_ratio: float = 0.7,
        gap_days: int = 5,
        anchored: bool = False,
        initial_capital: float = INITIAL_CAPITAL,
        commission: float = COMMISSION,
        slippage: float = SLIPPAGE,
    ):
        self.n_splits = n_splits
        self.train_ratio = train_ratio
        self.gap_days = gap_days
        self.anchored = anchored
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage

    def _generate_splits(self, data: pd.DataFrame) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
        """Generate train/test splits preserving time order."""
        n = len(data)
        splits = []

        if self.anchored:
            # Expanding window: train always starts at 0
            test_size = n // (self.n_splits + 1)
            for i in range(self.n_splits):
                train_end_idx = test_size * (i + 1)
                test_start_idx = train_end_idx + self.gap_days
                test_end_idx = min(test_start_idx + test_size, n)

                if test_start_idx >= n or test_end_idx <= test_start_idx:
                    continue

                train = data.iloc[:train_end_idx].copy().reset_index(drop=True)
                test = data.iloc[test_start_idx:test_end_idx].copy().reset_index(drop=True)
                splits.append((train, test))
        else:
            # Rolling window
            window_size = n // self.n_splits
            for i in range(self.n_splits):
                start_idx = i * (n - window_size) // max(self.n_splits - 1, 1)
                end_idx = start_idx + window_size

                train_end_idx = start_idx + int(window_size * self.train_ratio)
                test_start_idx = train_end_idx + self.gap_days
                test_end_idx = end_idx

                if test_start_idx >= test_end_idx or test_start_idx >= n:
                    continue

                train = data.iloc[start_idx:train_end_idx].copy().reset_index(drop=True)
                test = data.iloc[test_start_idx:test_end_idx].copy().reset_index(drop=True)
                splits.append((train, test))

        return splits

    def _run_single_backtest(self, strategy: Strategy, data: pd.DataFrame) -> dict:
        """Run a backtest and return metrics."""
        bt = Backtest(
            strategy=strategy,
            initial_capital=self.initial_capital,
            commission=self.commission,
            slippage=self.slippage,
        )
        bt.run(data)
        return bt.get_metrics()

    def _optimize_params(
        self,
        strategy: Strategy,
        train_data: pd.DataFrame,
        param_grid: dict[str, list],
    ) -> dict:
        """Grid search over param_grid, return best params by Sharpe ratio."""
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        best_sharpe = -np.inf
        best_params = strategy.get_params()

        for combo in product(*param_values):
            params = dict(zip(param_names, combo))
            candidate = strategy.copy()
            candidate.set_params(**params)
            metrics = self._run_single_backtest(candidate, train_data)
            sharpe = metrics.get("Sharpe Ratio", 0)
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_params = params.copy()

        return best_params

    def run(
        self,
        strategy: Strategy,
        data: pd.DataFrame,
        param_grid: dict[str, list] | None = None,
    ) -> WalkForwardResult:
        """Run walk-forward analysis.

        Args:
            strategy: Strategy to evaluate.
            data: Full OHLCV dataset.
            param_grid: Optional parameter grid for optimization.
                Example: {"fast_period": [10, 20, 30], "slow_period": [40, 50, 60]}
                If None, uses the strategy's current parameters for all folds.

        Returns:
            WalkForwardResult with per-fold and aggregate metrics.
        """
        splits = self._generate_splits(data)
        result = WalkForwardResult(strategy_name=strategy.name)

        for i, (train, test) in enumerate(splits):
            best_params = None
            fold_strategy = strategy.copy()

            if param_grid:
                best_params = self._optimize_params(fold_strategy, train, param_grid)
                fold_strategy.set_params(**best_params)

            is_metrics = self._run_single_backtest(fold_strategy, train)
            oos_metrics = self._run_single_backtest(fold_strategy, test)

            fold = FoldResult(
                fold_index=i,
                train_start=train["Date"].iloc[0],
                train_end=train["Date"].iloc[-1],
                test_start=test["Date"].iloc[0],
                test_end=test["Date"].iloc[-1],
                in_sample_metrics=is_metrics,
                out_of_sample_metrics=oos_metrics,
                best_params=best_params,
            )
            result.folds.append(fold)

        return result

    def get_splits_info(self, data: pd.DataFrame) -> list[dict]:
        """Return split boundary info for visualization."""
        splits = self._generate_splits(data)
        info = []
        for i, (train, test) in enumerate(splits):
            info.append({
                "fold": i,
                "train_start": train["Date"].iloc[0],
                "train_end": train["Date"].iloc[-1],
                "test_start": test["Date"].iloc[0],
                "test_end": test["Date"].iloc[-1],
                "train_size": len(train),
                "test_size": len(test),
            })
        return info
