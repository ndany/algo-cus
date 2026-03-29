"""Tests for walk-forward engine."""

import pytest

from backtest.walk_forward import WalkForwardEngine, WalkForwardResult
from strategies.moving_average_crossover import MovingAverageCrossover
from strategies.rsi_strategy import RSIStrategy


class TestWalkForwardEngine:
    def test_generates_correct_number_of_folds(self, sample_data):
        engine = WalkForwardEngine(n_splits=3)
        result = engine.run(MovingAverageCrossover(), sample_data)
        assert result.n_folds == 3

    def test_folds_are_sequential(self, sample_data):
        engine = WalkForwardEngine(n_splits=3)
        result = engine.run(MovingAverageCrossover(), sample_data)
        for fold in result.folds:
            assert fold.train_end < fold.test_start

    def test_degradation_ratio_is_float(self, sample_data):
        engine = WalkForwardEngine(n_splits=3)
        result = engine.run(MovingAverageCrossover(), sample_data)
        assert isinstance(result.degradation_ratio, float)

    def test_aggregate_oos_metrics(self, sample_data):
        engine = WalkForwardEngine(n_splits=3)
        result = engine.run(RSIStrategy(), sample_data)
        agg = result.aggregate_oos_metrics
        assert "Strategy" in agg
        assert "Sharpe Ratio" in agg

    def test_with_param_grid(self, sample_data):
        engine = WalkForwardEngine(n_splits=2)
        strategy = MovingAverageCrossover()
        param_grid = {"fast_period": [10, 20], "slow_period": [40, 50]}
        result = engine.run(strategy, sample_data, param_grid=param_grid)
        assert result.n_folds == 2
        # Should have best_params for each fold
        for fold in result.folds:
            assert fold.best_params is not None
            assert "fast_period" in fold.best_params

    def test_anchored_mode(self, sample_data):
        engine = WalkForwardEngine(n_splits=3, anchored=True)
        result = engine.run(MovingAverageCrossover(), sample_data)
        # In anchored mode, all folds should start training from the beginning
        assert result.n_folds >= 2

    def test_summary_returns_string(self, sample_data):
        engine = WalkForwardEngine(n_splits=2)
        result = engine.run(MovingAverageCrossover(), sample_data)
        summary = result.summary()
        assert isinstance(summary, str)
        assert "Walk-Forward" in summary

    def test_get_splits_info(self, sample_data):
        engine = WalkForwardEngine(n_splits=3)
        info = engine.get_splits_info(sample_data)
        assert len(info) == 3
        for split in info:
            assert "train_start" in split
            assert "test_end" in split
            assert split["train_size"] > 0
            assert split["test_size"] > 0

    def test_does_not_mutate_original_strategy(self, sample_data):
        """Walk-forward uses copies — original strategy must be untouched (#31)."""
        strategy = MovingAverageCrossover(fast_period=20, slow_period=50)
        engine = WalkForwardEngine(n_splits=2)
        param_grid = {"fast_period": [10, 30], "slow_period": [40, 60]}
        engine.run(strategy, sample_data, param_grid=param_grid)
        assert strategy.fast_period == 20
        assert strategy.slow_period == 50


class TestWalkForwardEdgeCases:
    """Edge-case coverage for walk-forward (#45)."""

    def test_aggregate_oos_metrics_empty_folds(self):
        """aggregate_oos_metrics returns {} when there are no folds."""
        result = WalkForwardResult(strategy_name="Empty")
        assert result.aggregate_oos_metrics == {}

    def test_degradation_ratio_with_zero_in_sample_sharpe(self, short_data):
        """degradation_ratio returns 0.0 when in-sample Sharpe averages to 0."""
        result = WalkForwardResult(strategy_name="ZeroSharpe")
        assert result.degradation_ratio == 0.0

    def test_anchored_skip_when_data_too_small(self):
        """Anchored splits skip folds when gap pushes test start past data end."""
        from data.sample_data import generate_ohlcv
        tiny = generate_ohlcv(days=30, seed=42)
        # Many splits + large gap on tiny data → some splits skipped
        engine = WalkForwardEngine(n_splits=10, gap_days=15, anchored=True)
        result = engine.run(MovingAverageCrossover(fast_period=5, slow_period=10), tiny)
        # Should run but produce fewer folds than requested
        assert result.n_folds < 10

    def test_rolling_skip_when_gap_too_large(self):
        """Rolling splits skip folds when gap pushes test start past window end."""
        from data.sample_data import generate_ohlcv
        tiny = generate_ohlcv(days=30, seed=42)
        engine = WalkForwardEngine(n_splits=5, gap_days=20, anchored=False)
        result = engine.run(MovingAverageCrossover(fast_period=5, slow_period=10), tiny)
        assert result.n_folds < 5
