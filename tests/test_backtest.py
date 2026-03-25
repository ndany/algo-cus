"""Tests for backtest engine."""

import pandas as pd
import pytest

from backtest.engine import Backtest, calculate_metrics
from strategies.moving_average_crossover import MovingAverageCrossover
from strategies.rsi_strategy import RSIStrategy


class TestBacktest:
    def test_run_returns_dataframe(self, sample_data):
        bt = Backtest(strategy=MovingAverageCrossover())
        result = bt.run(sample_data)
        assert isinstance(result, pd.DataFrame)
        assert "Portfolio_Value" in result.columns
        assert "Daily_Return" in result.columns

    def test_initial_portfolio_value(self, sample_data):
        bt = Backtest(strategy=MovingAverageCrossover(), initial_capital=10_000)
        bt.run(sample_data)
        # First row should be close to initial capital (no trade on first day usually)
        assert abs(bt.results["Portfolio_Value"].iloc[0] - 10_000) < 1

    def test_metrics_keys(self, sample_data):
        bt = Backtest(strategy=MovingAverageCrossover())
        bt.run(sample_data)
        metrics = bt.get_metrics()
        expected_keys = {
            "Strategy", "Total Return (%)", "Sharpe Ratio",
            "Max Drawdown (%)", "Number of Trades", "Win Rate (%)",
            "Final Value ($)",
        }
        assert set(metrics.keys()) == expected_keys

    def test_metrics_before_run_raises(self):
        bt = Backtest(strategy=MovingAverageCrossover())
        with pytest.raises(ValueError, match="Run the backtest first"):
            bt.get_metrics()

    def test_slippage_reduces_returns(self, sample_data):
        bt_no_slip = Backtest(
            strategy=RSIStrategy(), slippage=0.0, commission=0.0
        )
        bt_slip = Backtest(
            strategy=RSIStrategy(), slippage=0.01, commission=0.0
        )
        bt_no_slip.run(sample_data)
        bt_slip.run(sample_data)
        # Higher slippage should result in lower or equal final value
        assert (
            bt_slip.results["Portfolio_Value"].iloc[-1]
            <= bt_no_slip.results["Portfolio_Value"].iloc[-1]
        )

    def test_date_slicing(self, sample_data):
        bt = Backtest(strategy=MovingAverageCrossover())
        start = sample_data["Date"].iloc[50]
        end = sample_data["Date"].iloc[150]
        result = bt.run(sample_data, start_date=str(start), end_date=str(end))
        assert len(result) <= 101  # 150-50+1
        assert result["Date"].iloc[0] >= start
        assert result["Date"].iloc[-1] <= end

    def test_summary_returns_string(self, sample_data):
        bt = Backtest(strategy=MovingAverageCrossover())
        bt.run(sample_data)
        summary = bt.summary()
        assert isinstance(summary, str)
        assert "Backtest Results" in summary


class TestCalculateMetrics:
    def test_standalone_metrics(self, sample_data):
        bt = Backtest(strategy=MovingAverageCrossover(), initial_capital=10_000)
        bt.run(sample_data)
        metrics = calculate_metrics(
            portfolio_values=bt.results["Portfolio_Value"],
            trades=bt.trades,
            initial_capital=10_000,
            strategy_name="Test",
        )
        assert metrics["Strategy"] == "Test"
        assert isinstance(metrics["Total Return (%)"], float)

    def test_max_drawdown_non_positive(self, sample_data):
        bt = Backtest(strategy=MovingAverageCrossover())
        bt.run(sample_data)
        metrics = bt.get_metrics()
        assert metrics["Max Drawdown (%)"] <= 0
