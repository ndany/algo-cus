"""
Run and compare all three strategies on real or synthetic data.

Usage:
    python examples/run_backtest.py                    # Synthetic data
    python examples/run_backtest.py --ticker AMZN      # Single ticker
    python examples/run_backtest.py --ticker AMZN GOOG # Multiple tickers

Run with: python examples/run_backtest.py
"""

import argparse
import sys
import os

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import get_data
from strategies import MovingAverageCrossover, RSIStrategy, BollingerBandsStrategy
from backtest.engine import Backtest
from visualization.charts import (
    plot_candlestick,
    plot_strategy_signals,
    plot_portfolio_comparison,
    plot_metrics_table,
    plot_drawdown,
    save_figure,
)
from config import DEFAULT_TICKERS


def run_for_ticker(ticker_label: str, data, strategies, initial_capital=10_000):
    """Run all strategies on one dataset and display results."""
    print(f"\n{'='*60}")
    print(f"  {ticker_label}")
    print(f"{'='*60}")

    # Backtest each strategy
    all_metrics = []
    results = {}
    for strategy in strategies:
        bt = Backtest(strategy=strategy, initial_capital=initial_capital, commission=0.001)
        bt.run(data)
        print(bt.summary())
        all_metrics.append(bt.get_metrics())
        results[strategy.name] = bt.results

    # Interactive charts
    fig_candle = plot_candlestick(data, title=f"{ticker_label} — Price")
    save_figure(fig_candle, f"{ticker_label}_candlestick")

    for strategy in strategies:
        signals_df = strategy.generate_signals(data.copy())
        fig_signals = plot_strategy_signals(signals_df, strategy.name)
        save_figure(fig_signals, f"{ticker_label}_{strategy.name}_signals")

    fig_compare = plot_portfolio_comparison(results, initial_capital)
    save_figure(fig_compare, f"{ticker_label}_portfolio_comparison")

    fig_table = plot_metrics_table(all_metrics)
    save_figure(fig_table, f"{ticker_label}_metrics")

    print(f"\n  Charts saved to output/ directory")
    return all_metrics


def main():
    parser = argparse.ArgumentParser(description="Backtest trading strategies")
    parser.add_argument(
        "--ticker", nargs="*", default=None,
        help="Ticker symbol(s) to backtest. Omit for synthetic data.",
    )
    args = parser.parse_args()

    strategies = [
        MovingAverageCrossover(fast_period=20, slow_period=50),
        RSIStrategy(period=14, oversold=30, overbought=70),
        BollingerBandsStrategy(period=20, num_std=2.0),
    ]

    if args.ticker is None:
        data = get_data("synthetic", days=500)
        run_for_ticker("Synthetic", data, strategies)
    else:
        tickers = args.ticker if args.ticker else DEFAULT_TICKERS
        for ticker in tickers:
            try:
                data = get_data(ticker)
                run_for_ticker(ticker, data, strategies)
            except Exception as e:
                print(f"\nError fetching {ticker}: {e}")


if __name__ == "__main__":
    main()
