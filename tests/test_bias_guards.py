"""Tests for bias guard utilities."""

import pandas as pd
import pytest

from backtest.bias_guards import (
    benchmark_buy_and_hold,
    benchmark_random,
    parameter_stability_test,
    detect_lookahead_bias,
)
from strategies.moving_average_crossover import MovingAverageCrossover
from strategies.rsi_strategy import RSIStrategy


class TestBenchmarkBuyAndHold:
    def test_returns_metrics_dict(self, sample_data):
        metrics = benchmark_buy_and_hold(sample_data)
        assert metrics["Strategy"] == "Buy & Hold"
        assert "Total Return (%)" in metrics

    def test_positive_market_positive_return(self):
        """If price doubles, buy & hold should show ~100% return."""
        from data.sample_data import generate_ohlcv
        import numpy as np

        # Create data where price clearly goes up
        df = generate_ohlcv(days=100, seed=42)
        # Force an uptrend
        df["Close"] = df["Close"].iloc[0] * (1 + 0.005 * pd.Series(range(100)))
        df["Open"] = df["Close"]
        df["High"] = df["Close"] * 1.01
        df["Low"] = df["Close"] * 0.99

        metrics = benchmark_buy_and_hold(df, commission=0, slippage=0)
        assert metrics["Total Return (%)"] > 0


class TestBenchmarkRandom:
    def test_returns_metrics_dict(self, short_data):
        metrics = benchmark_random(short_data, n_simulations=10)
        assert metrics["Strategy"] == "Random Baseline"
        assert "Mean Return (%)" in metrics
        assert "Std Return (%)" in metrics

    def test_reproducible_with_seed(self, short_data):
        m1 = benchmark_random(short_data, n_simulations=20, seed=42)
        m2 = benchmark_random(short_data, n_simulations=20, seed=42)
        assert m1["Mean Return (%)"] == m2["Mean Return (%)"]


class TestParameterStability:
    def test_returns_dataframe(self, short_data):
        strategy = MovingAverageCrossover()
        result = parameter_stability_test(
            strategy, short_data,
            param_ranges={"fast_period": [10, 20], "slow_period": [40, 50]},
        )
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 4  # 2x2 combinations
        assert "fast_period" in result.columns
        assert "Sharpe Ratio" in result.columns

    def test_restores_original_params(self, short_data):
        strategy = MovingAverageCrossover(fast_period=20, slow_period=50)
        parameter_stability_test(
            strategy, short_data,
            param_ranges={"fast_period": [10, 30]},
        )
        assert strategy.fast_period == 20
        assert strategy.slow_period == 50


class TestLookaheadBias:
    def test_clean_strategy_passes(self, sample_data):
        result = detect_lookahead_bias(MovingAverageCrossover(), sample_data)
        assert result["passed"] is True
        assert len(result["inconsistencies"]) == 0

    def test_returns_expected_keys(self, sample_data):
        result = detect_lookahead_bias(RSIStrategy(), sample_data)
        assert "strategy" in result
        assert "passed" in result
        assert "message" in result
        assert "inconsistencies" in result
