"""Tests for dashboard modules."""

import os
import pytest
import plotly.graph_objects as go

from dashboard.theme import COLORS, apply_dark_theme, PLOTLY_TEMPLATE
from dashboard.analysis import run_analysis, get_strategies


class TestTheme:
    def test_colors_has_required_keys(self):
        required = [
            "bg_primary", "bg_secondary", "text_primary",
            "accent_cyan", "accent_green", "accent_red",
        ]
        for key in required:
            assert key in COLORS

    def test_apply_dark_theme_returns_figure(self):
        fig = go.Figure()
        result = apply_dark_theme(fig)
        assert isinstance(result, go.Figure)

    def test_template_registered(self):
        import plotly.io as pio
        assert "trader_dark" in pio.templates


class TestAnalysis:
    def test_get_strategies_returns_three(self):
        strategies = get_strategies()
        assert len(strategies) == 3

    def test_get_strategies_all_have_names(self):
        for s in get_strategies():
            assert s.name

    @pytest.mark.integration
    def test_run_analysis_returns_expected_keys(self):
        result = run_analysis("MSFT")
        expected_keys = {
            "ticker", "data", "strategies", "buy_hold",
            "walk_forward", "wf_splits_info", "elapsed",
        }
        assert expected_keys.issubset(set(result.keys()))
        assert result["ticker"] == "MSFT"
        assert len(result["strategies"]) == 3
        assert len(result["walk_forward"]) == 3


class TestDashApp:
    def test_app_imports(self):
        """Verify the Dash app can be imported without errors."""
        from dashboard.app import app, server
        assert app is not None
        assert server is not None

    def test_app_layout_exists(self):
        from dashboard.app import app
        assert app.layout is not None

    def test_chart_builders_with_synthetic_data(self):
        """Test that chart builders produce figures with synthetic data."""
        from data.sample_data import generate_ohlcv
        from dashboard.app import build_candlestick, build_signals_chart, build_drawdown_chart
        from strategies import MovingAverageCrossover
        from backtest.engine import Backtest

        data = generate_ohlcv(days=100, seed=42)

        # Candlestick
        fig = build_candlestick(data, "TEST")
        assert isinstance(fig, go.Figure)

        # Signals
        strategy = MovingAverageCrossover()
        signals = strategy.generate_signals(data.copy())
        fig = build_signals_chart(signals, "MA_Crossover", "#00d4ff")
        assert isinstance(fig, go.Figure)

        # Drawdown
        bt = Backtest(strategy=strategy)
        bt.run(data)
        fig = build_drawdown_chart(bt.results, "MA_Crossover")
        assert isinstance(fig, go.Figure)
