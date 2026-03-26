"""
Bias Guards — utilities to detect common backtesting pitfalls.

These tools help you avoid the three biggest mistakes in backtesting:
1. Lookahead bias: Using future information to make past decisions.
2. Overfitting: Tuning parameters until they work perfectly on history
   but fail on new data.
3. Benchmark illusion: A strategy looks great until you compare it
   to simply buying and holding.
"""

import numpy as np
import pandas as pd

from backtest.engine import Backtest, calculate_metrics
from strategies.base import Strategy
from config import INITIAL_CAPITAL, COMMISSION, SLIPPAGE


def benchmark_buy_and_hold(
    data: pd.DataFrame,
    initial_capital: float = INITIAL_CAPITAL,
    commission: float = COMMISSION,
    slippage: float = SLIPPAGE,
) -> dict:
    """Calculate buy-and-hold benchmark metrics.

    This is the simplest possible strategy: buy on day 1, hold forever.
    Any strategy that can't beat this isn't worth the complexity.
    """
    friction = commission + slippage
    invest_amount = initial_capital / (1 + friction)
    shares = invest_amount / data["Close"].iloc[0]
    final_value = shares * data["Close"].iloc[-1] * (1 - friction)

    portfolio_values = shares * data["Close"]
    # Adjust first value for buy friction and last for sell
    portfolio_values = portfolio_values.copy()

    return calculate_metrics(
        portfolio_values=portfolio_values,
        trades=pd.DataFrame([
            {"Date": data["Date"].iloc[0], "Action": "BUY",
             "Price": data["Close"].iloc[0], "Shares": shares, "Value": invest_amount},
            {"Date": data["Date"].iloc[-1], "Action": "SELL",
             "Price": data["Close"].iloc[-1], "Shares": shares, "Value": final_value},
        ]),
        initial_capital=initial_capital,
        strategy_name="Buy & Hold",
    )


def benchmark_random(
    data: pd.DataFrame,
    n_simulations: int = 100,
    trade_frequency: float = 0.05,
    initial_capital: float = INITIAL_CAPITAL,
    commission: float = COMMISSION,
    slippage: float = SLIPPAGE,
    seed: int = 42,
) -> dict:
    """Simulate random entry/exit as a baseline.

    If your strategy can't beat random coin flips, it has no edge.

    Args:
        data: OHLCV DataFrame.
        n_simulations: Number of random simulations to average.
        trade_frequency: Probability of a signal on any given day.
        seed: Random seed for reproducibility.
    """
    rng = np.random.default_rng(seed)
    all_returns = []

    for _ in range(n_simulations):
        cash = initial_capital
        shares = 0.0
        friction = commission + slippage

        for _, row in data.iterrows():
            price = row["Close"]
            rand = rng.random()

            if rand < trade_frequency and cash > 0 and shares == 0:
                invest = cash / (1 + friction)
                shares = invest / price
                cash -= invest * (1 + friction)
            elif rand < trade_frequency * 2 and shares > 0:
                proceeds = shares * price * (1 - friction)
                cash += proceeds
                shares = 0.0

        final = cash + shares * data["Close"].iloc[-1]
        all_returns.append((final - initial_capital) / initial_capital * 100)

    return {
        "Strategy": "Random Baseline",
        "Mean Return (%)": round(np.mean(all_returns), 2),
        "Median Return (%)": round(np.median(all_returns), 2),
        "Std Return (%)": round(np.std(all_returns), 2),
        "Best Return (%)": round(np.max(all_returns), 2),
        "Worst Return (%)": round(np.min(all_returns), 2),
    }


def parameter_stability_test(
    strategy: Strategy,
    data: pd.DataFrame,
    param_ranges: dict[str, list],
    initial_capital: float = INITIAL_CAPITAL,
    commission: float = COMMISSION,
    slippage: float = SLIPPAGE,
) -> pd.DataFrame:
    """Test how sensitive performance is to parameter changes.

    A robust strategy should perform reasonably across a range of parameters.
    If small changes in parameters cause wild swings in performance,
    the strategy is likely overfit.

    Args:
        strategy: Strategy to test.
        data: OHLCV DataFrame.
        param_ranges: Dict of parameter names to lists of values to test.

    Returns:
        DataFrame with one row per parameter combination and its metrics.
    """
    from itertools import product

    param_names = list(param_ranges.keys())
    param_values = list(param_ranges.values())
    rows = []

    original_params = strategy.get_params()

    for combo in product(*param_values):
        params = dict(zip(param_names, combo))
        strategy.set_params(**params)

        bt = Backtest(
            strategy=strategy,
            initial_capital=initial_capital,
            commission=commission,
            slippage=slippage,
        )
        bt.run(data)
        metrics = bt.get_metrics()

        row = {**params, **metrics}
        rows.append(row)

    # Restore original params
    if original_params:
        strategy.set_params(**original_params)

    return pd.DataFrame(rows)


def detect_lookahead_bias(
    strategy: Strategy,
    data: pd.DataFrame,
    check_points: int = 5,
) -> dict:
    """Detect potential lookahead bias by comparing signals on truncated data.

    The idea: if a strategy uses future information, its signals at time T
    will change depending on whether data after T is available.

    We run the strategy on progressively longer data and check if signals
    for earlier dates change.

    Args:
        strategy: Strategy to test.
        data: Full OHLCV DataFrame.
        check_points: Number of truncation points to test.

    Returns:
        Dict with test results and any flagged inconsistencies.
    """
    n = len(data)
    step = n // (check_points + 1)
    inconsistencies = []

    # Get signals on full data
    full_signals = strategy.generate_signals(data.copy())["Signal"]

    for i in range(1, check_points + 1):
        truncate_at = step * i
        if truncate_at < 50:  # Need enough data for indicators
            continue

        truncated = data.iloc[:truncate_at].copy().reset_index(drop=True)
        partial_signals = strategy.generate_signals(truncated)["Signal"]

        # Compare signals up to the truncation point
        full_slice = full_signals.iloc[:truncate_at].reset_index(drop=True)

        mismatches = (full_slice != partial_signals).sum()
        if mismatches > 0:
            inconsistencies.append({
                "truncated_at": truncate_at,
                "mismatches": int(mismatches),
                "mismatch_rate": round(mismatches / truncate_at * 100, 2),
            })

    passed = len(inconsistencies) == 0
    return {
        "strategy": strategy.name,
        "passed": passed,
        "check_points": check_points,
        "inconsistencies": inconsistencies,
        "message": (
            "No lookahead bias detected."
            if passed
            else f"Potential lookahead bias: signals changed at {len(inconsistencies)} "
                 f"truncation points. This may indicate the strategy uses future data."
        ),
    }
