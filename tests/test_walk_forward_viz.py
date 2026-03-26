"""Tests for walk-forward visualization module."""

import plotly.graph_objects as go
import pytest

from backtest.walk_forward import WalkForwardEngine
from strategies.moving_average_crossover import MovingAverageCrossover
from strategies.rsi_strategy import RSIStrategy
from visualization.walk_forward import (
    plot_walk_forward_splits,
    plot_in_vs_out_sample,
    plot_parameter_sensitivity,
    plot_degradation_summary,
)
from backtest.bias_guards import parameter_stability_test


class TestPlotWalkForwardSplits:
    def test_returns_figure(self, sample_data):
        engine = WalkForwardEngine(n_splits=3)
        info = engine.get_splits_info(sample_data)
        fig = plot_walk_forward_splits(sample_data, info)
        assert isinstance(fig, go.Figure)


class TestPlotInVsOutSample:
    def test_returns_figure(self, sample_data):
        engine = WalkForwardEngine(n_splits=3)
        result = engine.run(MovingAverageCrossover(), sample_data)
        fig = plot_in_vs_out_sample(result)
        assert isinstance(fig, go.Figure)

    def test_custom_metric(self, sample_data):
        engine = WalkForwardEngine(n_splits=2)
        result = engine.run(RSIStrategy(), sample_data)
        fig = plot_in_vs_out_sample(result, metric="Total Return (%)")
        assert isinstance(fig, go.Figure)


class TestPlotParameterSensitivity:
    def test_1d_line_chart(self, short_data):
        stability = parameter_stability_test(
            MovingAverageCrossover(), short_data,
            param_ranges={"fast_period": [10, 15, 20]},
        )
        fig = plot_parameter_sensitivity(stability, x_param="fast_period")
        assert isinstance(fig, go.Figure)

    def test_2d_heatmap(self, short_data):
        stability = parameter_stability_test(
            MovingAverageCrossover(), short_data,
            param_ranges={"fast_period": [10, 20], "slow_period": [40, 50]},
        )
        fig = plot_parameter_sensitivity(
            stability, x_param="fast_period", y_param="slow_period"
        )
        assert isinstance(fig, go.Figure)


class TestPlotDegradationSummary:
    def test_returns_figure(self, sample_data):
        engine = WalkForwardEngine(n_splits=2)
        r1 = engine.run(MovingAverageCrossover(), sample_data)
        r2 = engine.run(RSIStrategy(), sample_data)
        fig = plot_degradation_summary([r1, r2])
        assert isinstance(fig, go.Figure)
