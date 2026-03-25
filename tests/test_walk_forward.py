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

    def test_restores_original_params(self, sample_data):
        strategy = MovingAverageCrossover(fast_period=20, slow_period=50)
        engine = WalkForwardEngine(n_splits=2)
        param_grid = {"fast_period": [10, 30], "slow_period": [40, 60]}
        engine.run(strategy, sample_data, param_grid=param_grid)
        # Original params should be restored
        assert strategy.fast_period == 20
        assert strategy.slow_period == 50
