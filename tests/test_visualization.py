"""Tests for visualization modules."""

import plotly.graph_objects as go
import pytest

from visualization.charts import (
    plot_candlestick,
    plot_strategy_signals,
    plot_portfolio_comparison,
    plot_drawdown,
    plot_metrics_table,
    save_figure,
)
from strategies.moving_average_crossover import MovingAverageCrossover
from backtest.engine import Backtest


class TestPlotCandlestick:
    def test_returns_figure(self, sample_data):
        fig = plot_candlestick(sample_data)
        assert isinstance(fig, go.Figure)

    def test_without_volume(self, sample_data):
        fig = plot_candlestick(sample_data, show_volume=False)
        assert isinstance(fig, go.Figure)


class TestPlotStrategySignals:
    def test_returns_figure(self, sample_data):
        s = MovingAverageCrossover()
        df = s.generate_signals(sample_data)
        fig = plot_strategy_signals(df, "MA Crossover")
        assert isinstance(fig, go.Figure)

    def test_with_no_signals(self, short_data):
        # Very short data may have no crossover signals
        import pandas as pd
        df = short_data.copy()
        df["Signal"] = 0
        fig = plot_strategy_signals(df, "No Signals")
        assert isinstance(fig, go.Figure)


class TestPlotPortfolioComparison:
    def test_returns_figure(self, sample_data):
        bt = Backtest(strategy=MovingAverageCrossover())
        bt.run(sample_data)
        results = {"MA": bt.results}
        fig = plot_portfolio_comparison(results)
        assert isinstance(fig, go.Figure)


class TestPlotDrawdown:
    def test_returns_figure(self, sample_data):
        bt = Backtest(strategy=MovingAverageCrossover())
        bt.run(sample_data)
        fig = plot_drawdown(bt.results)
        assert isinstance(fig, go.Figure)


class TestPlotMetricsTable:
    def test_returns_figure(self, sample_data):
        bt = Backtest(strategy=MovingAverageCrossover())
        bt.run(sample_data)
        fig = plot_metrics_table([bt.get_metrics()])
        assert isinstance(fig, go.Figure)

    def test_empty_list(self):
        fig = plot_metrics_table([])
        assert isinstance(fig, go.Figure)


class TestSaveFigure:
    def test_saves_html(self, sample_data, tmp_path):
        import config
        original = config.OUTPUT_DIR
        config.OUTPUT_DIR = tmp_path
        try:
            fig = plot_candlestick(sample_data)
            path = save_figure(fig, "test_chart")
            assert path.exists()
            assert path.suffix == ".html"
        finally:
            config.OUTPUT_DIR = original
