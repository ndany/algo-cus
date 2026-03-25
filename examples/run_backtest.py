"""
Example: Run and compare all three strategies.

This script demonstrates the full workflow:
1. Generate (or load) market data
2. Run each strategy through the backtester
3. Compare performance metrics
4. Plot the results

Run with: python examples/run_backtest.py
"""

import sys
import os

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.sample_data import generate_ohlcv
from strategies import MovingAverageCrossover, RSIStrategy, BollingerBandsStrategy
from backtest.engine import Backtest


def main():
    # Step 1: Generate sample market data
    print("Generating 500 days of sample market data...\n")
    data = generate_ohlcv(days=500)

    # Step 2: Define strategies to compare
    strategies = [
        MovingAverageCrossover(fast_period=20, slow_period=50),
        RSIStrategy(period=14, oversold=30, overbought=70),
        BollingerBandsStrategy(period=20, num_std=2.0),
    ]

    # Step 3: Backtest each strategy
    all_metrics = []
    for strategy in strategies:
        bt = Backtest(
            strategy=strategy,
            initial_capital=10_000,
            commission=0.001,
        )
        bt.run(data)
        print(bt.summary())
        all_metrics.append(bt.get_metrics())

    # Step 4: Side-by-side comparison
    print("\n" + "=" * 60)
    print("  STRATEGY COMPARISON")
    print("=" * 60)
    header = f"  {'Metric':<25}"
    for m in all_metrics:
        header += f" {m['Strategy']:>15}"
    print(header)
    print("  " + "-" * (25 + 16 * len(all_metrics)))

    for key in ["Total Return (%)", "Sharpe Ratio", "Max Drawdown (%)",
                "Number of Trades", "Win Rate (%)", "Final Value ($)"]:
        row = f"  {key:<25}"
        for m in all_metrics:
            row += f" {m[key]:>15}"
        print(row)
    print("=" * 60)

    # Step 5: Try to plot (optional — works if matplotlib is installed)
    try:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

        # Plot price with moving averages
        axes[0].plot(data["Date"], data["Close"], label="Price", color="black", alpha=0.7)
        axes[0].set_title("Asset Price")
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # Plot portfolio values for each strategy
        for strategy in strategies:
            bt = Backtest(strategy=strategy, initial_capital=10_000)
            results = bt.run(data)
            axes[1].plot(results["Date"], results["Portfolio_Value"], label=str(strategy))

        axes[1].axhline(y=10_000, color="gray", linestyle="--", alpha=0.5, label="Starting Capital")
        axes[1].set_title("Portfolio Value Comparison")
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig("backtest_results.png", dpi=150)
        print("\nChart saved to backtest_results.png")
    except ImportError:
        print("\nInstall matplotlib to generate charts: pip install matplotlib")


if __name__ == "__main__":
    main()
