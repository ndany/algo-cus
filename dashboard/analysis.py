"""
Analysis engine for the dashboard.

Runs all strategies and backtests on a given ticker, returning
structured results for the dashboard to render.
"""

import logging
import time

import pandas as pd

from data.market_data import MarketDataProvider
from strategies import registry
from backtest.engine import Backtest
from backtest.walk_forward import WalkForwardEngine
from backtest.bias_guards import benchmark_buy_and_hold
from config import INITIAL_CAPITAL, COMMISSION, SLIPPAGE

logger = logging.getLogger(__name__)


def get_strategies():
    """Return instances of all registered strategies compatible with OHLCV data."""
    return registry.create_all()


def run_analysis(ticker: str) -> dict:
    """Run full analysis on a ticker.

    Returns a dict with:
        - ticker: str
        - data: DataFrame (OHLCV)
        - strategies: list of {name, strategy, signals_df, backtest_results, metrics}
        - buy_hold: dict of buy-and-hold metrics
        - walk_forward: list of WalkForwardResult (one per strategy)
        - elapsed: float (seconds)
    """
    start_time = time.time()

    provider = MarketDataProvider()
    data = provider.fetch(ticker, period="2y")

    strategies = get_strategies()
    strategy_results = []

    for strategy in strategies:
        signals_df = strategy.generate_signals(data.copy())

        bt = Backtest(
            strategy=strategy,
            initial_capital=INITIAL_CAPITAL,
            commission=COMMISSION,
            slippage=SLIPPAGE,
        )
        bt.run(data)
        metrics = bt.get_metrics()

        strategy_results.append({
            "name": strategy.name,
            "strategy": strategy,
            "signals_df": signals_df,
            "backtest_results": bt.results,
            "trades": bt.trades,
            "metrics": metrics,
        })

    buy_hold = benchmark_buy_and_hold(data)

    # Walk-forward (fewer splits for speed)
    wf_engine = WalkForwardEngine(n_splits=3, gap_days=5)
    wf_results = []
    for strategy in strategies:
        wf_result = wf_engine.run(strategy, data)
        wf_results.append(wf_result)

    elapsed = round(time.time() - start_time, 1)

    return {
        "ticker": ticker,
        "data": data,
        "strategies": strategy_results,
        "buy_hold": buy_hold,
        "walk_forward": wf_results,
        "wf_splits_info": wf_engine.get_splits_info(data),
        "elapsed": elapsed,
    }
