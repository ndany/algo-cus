"""Tests for dashboard modules."""

import io
import os

import pandas as pd
import pytest
import plotly.graph_objects as go
from dash import html

from dashboard.theme import COLORS, apply_dark_theme, PLOTLY_TEMPLATE
from dashboard.analysis import run_analysis, get_strategies
from dashboard.app import (
    app, server, make_empty_state, make_metric_tile,
    build_candlestick, build_signals_chart, build_drawdown_chart,
    build_portfolio_comparison, build_wf_chart,
    build_summary_view, build_strategy_detail,
)
from data.sample_data import generate_ohlcv
from strategies import MovingAverageCrossover
from strategies.rsi_strategy import RSIStrategy
from strategies.bollinger_bands import BollingerBandsStrategy
from backtest.engine import Backtest
from backtest.walk_forward import WalkForwardEngine
from backtest.bias_guards import benchmark_buy_and_hold
from config import INITIAL_CAPITAL, COMMISSION, SLIPPAGE


# ── Shared fixtures ──────────────────────────────────────────────


class _WFProxy:
    """Lightweight stand-in for WalkForwardResult, matching render_main."""

    def __init__(self, d):
        self.strategy_name = d["strategy_name"]
        self.degradation_ratio = d["degradation_ratio"]
        self.folds = [type("Fold", (), {
            "fold_index": f["fold_index"],
            "in_sample_metrics": f["is_metrics"],
            "out_of_sample_metrics": f["oos_metrics"],
        })() for f in d["folds"]]


def _serialize_analysis(data, strategy_results, buy_hold, wf_results):
    """Serialize analysis output the same way on_analyze does."""
    return {
        "ticker": "TEST",
        "elapsed": 1.0,
        "data_json": data.to_json(date_format="iso"),
        "strategies": [{
            "name": sr["name"],
            "signals_json": sr["signals_df"].to_json(date_format="iso"),
            "results_json": sr["backtest_results"].to_json(date_format="iso"),
            "metrics": sr["metrics"],
        } for sr in strategy_results],
        "buy_hold": buy_hold,
        "walk_forward": [{
            "strategy_name": wf.strategy_name,
            "degradation_ratio": wf.degradation_ratio,
            "folds": [{
                "fold_index": f.fold_index,
                "is_metrics": f.in_sample_metrics,
                "oos_metrics": f.out_of_sample_metrics,
            } for f in wf.folds],
        } for wf in wf_results],
    }


def _deserialize_store(store_data):
    """Deserialize store data the same way render_main does."""
    data = pd.read_json(io.StringIO(store_data["data_json"]))
    data = data.sort_values("Date").reset_index(drop=True)
    result = {
        "ticker": store_data["ticker"],
        "data": data,
        "buy_hold": store_data["buy_hold"],
        "strategies": [],
        "walk_forward": [],
    }
    for sr in store_data["strategies"]:
        sdf = pd.read_json(io.StringIO(sr["signals_json"])).sort_values("Date").reset_index(drop=True)
        rdf = pd.read_json(io.StringIO(sr["results_json"])).sort_values("Date").reset_index(drop=True)
        result["strategies"].append({
            "name": sr["name"],
            "signals_df": sdf,
            "backtest_results": rdf,
            "metrics": sr["metrics"],
        })
    result["walk_forward"] = [_WFProxy(wf) for wf in store_data["walk_forward"]]
    return result


@pytest.fixture(scope="module")
def analysis_result():
    """Run a full analysis on synthetic data once for the module."""
    data = generate_ohlcv(days=200, seed=42)
    strategies = [
        MovingAverageCrossover(fast_period=20, slow_period=50),
        RSIStrategy(period=14, oversold=30, overbought=70),
        BollingerBandsStrategy(period=20, num_std=2.0),
    ]
    strategy_results = []
    for strategy in strategies:
        signals_df = strategy.generate_signals(data.copy())
        bt = Backtest(strategy=strategy, initial_capital=INITIAL_CAPITAL,
                      commission=COMMISSION, slippage=SLIPPAGE)
        bt.run(data)
        strategy_results.append({
            "name": strategy.name,
            "signals_df": signals_df,
            "backtest_results": bt.results,
            "metrics": bt.get_metrics(),
        })
    buy_hold = benchmark_buy_and_hold(data)
    wf_engine = WalkForwardEngine(n_splits=3, gap_days=5)
    wf_results = [wf_engine.run(s, data) for s in strategies]
    return {
        "data": data,
        "strategy_results": strategy_results,
        "buy_hold": buy_hold,
        "wf_results": wf_results,
    }


@pytest.fixture(scope="module")
def store_data(analysis_result):
    """Serialized store_data as produced by on_analyze."""
    return _serialize_analysis(
        analysis_result["data"],
        analysis_result["strategy_results"],
        analysis_result["buy_hold"],
        analysis_result["wf_results"],
    )


@pytest.fixture(scope="module")
def deserialized_result(store_data):
    """Deserialized result as consumed by render_main."""
    return _deserialize_store(store_data)


# ── Theme tests ──────────────────────────────────────────────────


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


# ── Analysis tests ───────────────────────────────────────────────


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


# ── Dashboard app tests ─────────────────────────────────────────


class TestDashApp:
    def test_app_imports(self):
        assert app is not None
        assert server is not None

    def test_app_layout_exists(self):
        assert app.layout is not None

    def test_no_string_id_back_to_summary_in_layout(self):
        """Regression: a string-ID 'back-to-summary' in the layout combined with
        a duplicate created dynamically in build_strategy_detail caused Dash to
        lose track of the ID after the detail view was removed. The fix uses
        pattern-matching IDs (dict IDs) so the component can be absent."""
        layout_str = str(app.layout)
        assert "back-to-summary" not in layout_str

    def test_skip_auth_layout_has_main_content(self):
        """With SKIP_AUTH=1 (default in tests), layout should show the app directly."""
        from dashboard.app import SKIP_AUTH
        assert SKIP_AUTH is True  # tests run with SKIP_AUTH=1
        layout_str = str(app.layout)
        assert "main-content" in layout_str

    def test_login_page_has_required_components(self):
        """Login page should have Google sign-in link and invitation code input."""
        from dashboard.app import make_login_page
        login = make_login_page()
        login_str = str(login)
        assert "google-login-link" in login_str
        assert "invitation-code" in login_str
        assert "verify-code-btn" in login_str
        assert "invitation-status" in login_str

    def test_login_page_with_message(self):
        """Login page should display a message when provided."""
        from dashboard.app import make_login_page
        login = make_login_page(message="Welcome Alice")
        login_str = str(login)
        assert "Welcome Alice" in login_str


class TestAuthModule:
    def test_auth_module_imports(self):
        """auth.py should be importable without Supabase credentials."""
        import dashboard.auth as auth_mod
        assert hasattr(auth_mod, "validate_invitation_code")
        assert hasattr(auth_mod, "get_google_login_url")
        assert hasattr(auth_mod, "get_user_from_token")

    def test_get_supabase_requires_env_vars(self):
        """get_supabase should raise if SUPABASE_URL/KEY are missing."""
        import dashboard.auth as auth_mod
        # Clear any cached client
        auth_mod._client = None
        saved_url = os.environ.pop("SUPABASE_URL", None)
        saved_key = os.environ.pop("SUPABASE_KEY", None)
        try:
            with pytest.raises(RuntimeError, match="SUPABASE_URL"):
                auth_mod.get_supabase()
        finally:
            auth_mod._client = None
            if saved_url:
                os.environ["SUPABASE_URL"] = saved_url
            if saved_key:
                os.environ["SUPABASE_KEY"] = saved_key


# ── Serialization round-trip (regression for pd.read_json bug) ──


class TestSerializationRoundtrip:
    def test_data_survives_roundtrip(self, store_data, deserialized_result):
        """Regression: pd.read_json() treats long JSON strings as file paths.
        Fix uses io.StringIO()."""
        assert "Date" in deserialized_result["data"].columns
        assert len(deserialized_result["data"]) == 200

    def test_strategy_dataframes_survive_roundtrip(self, store_data, deserialized_result):
        for i, sr in enumerate(deserialized_result["strategies"]):
            assert "Date" in sr["signals_df"].columns
            assert "Date" in sr["backtest_results"].columns
            assert "Portfolio_Value" in sr["backtest_results"].columns
            assert sr["name"] == store_data["strategies"][i]["name"]

    def test_walk_forward_proxy_survives_roundtrip(self, store_data, deserialized_result):
        assert len(deserialized_result["walk_forward"]) == len(store_data["walk_forward"])
        for wf in deserialized_result["walk_forward"]:
            assert hasattr(wf, "strategy_name")
            assert hasattr(wf, "degradation_ratio")
            assert len(wf.folds) > 0
            for fold in wf.folds:
                assert hasattr(fold, "in_sample_metrics")
                assert hasattr(fold, "out_of_sample_metrics")

    def test_metrics_preserved_through_roundtrip(self, deserialized_result):
        for sr in deserialized_result["strategies"]:
            m = sr["metrics"]
            required_keys = {
                "Total Return (%)", "Sharpe Ratio", "Max Drawdown (%)",
                "Number of Trades", "Win Rate (%)", "Final Value ($)",
            }
            assert required_keys.issubset(set(m.keys()))

    def test_buy_hold_preserved_through_roundtrip(self, deserialized_result):
        assert "Total Return (%)" in deserialized_result["buy_hold"]


# ── Empty state ──────────────────────────────────────────────────


class TestEmptyState:
    def test_make_empty_state_returns_div(self):
        result = make_empty_state()
        assert isinstance(result, html.Div)

    def test_render_main_returns_empty_state_when_no_data(self):
        """render_main with store_data=None should return empty state."""
        from dashboard.app import render_main
        result = render_main(None, -1)
        assert isinstance(result, html.Div)

    def test_render_main_returns_empty_state_when_empty_dict(self):
        """render_main with store_data={} (falsy) returns empty state."""
        from dashboard.app import render_main
        result = render_main({}, -1)
        assert isinstance(result, html.Div)


# ── Metric tile builder ─────────────────────────────────────────


class TestMetricTile:
    def test_percentage_positive(self):
        tile = make_metric_tile("Return", 12.5, is_pct=True)
        assert isinstance(tile, html.Div)

    def test_percentage_negative(self):
        tile = make_metric_tile("Return", -3.2, is_pct=True)
        assert isinstance(tile, html.Div)

    def test_currency_format(self):
        tile = make_metric_tile("Value", 10500.0, is_currency=True)
        assert isinstance(tile, html.Div)

    def test_plain_number(self):
        tile = make_metric_tile("Sharpe", 1.25)
        assert isinstance(tile, html.Div)

    def test_string_value(self):
        tile = make_metric_tile("Ticker", "AMZN")
        assert isinstance(tile, html.Div)

    def test_zero_value(self):
        tile = make_metric_tile("Return", 0.0, is_pct=True)
        assert isinstance(tile, html.Div)

    def test_good_positive_false_inverts_color(self):
        tile = make_metric_tile("Drawdown", -5.0, is_pct=True, good_positive=False)
        # Negative with good_positive=False should get "positive" class
        value_div = tile.children[0]
        assert "positive" in value_div.className

    def test_integer_value(self):
        tile = make_metric_tile("Trades", 42)
        assert isinstance(tile, html.Div)


# ── Chart builder tests ─────────────────────────────────────────


class TestChartBuilders:
    def test_candlestick_returns_figure(self):
        data = generate_ohlcv(days=100, seed=42)
        fig = build_candlestick(data, "TEST")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2  # candlestick + volume bar

    def test_signals_chart_with_buys_and_sells(self):
        data = generate_ohlcv(days=100, seed=42)
        strategy = MovingAverageCrossover()
        signals = strategy.generate_signals(data.copy())
        fig = build_signals_chart(signals, "MA_Crossover", "#00d4ff")
        assert isinstance(fig, go.Figure)
        # Price line + at least one of buys/sells
        assert len(fig.data) >= 1

    def test_signals_chart_no_signals(self):
        """Signals chart should still work with zero buy/sell signals."""
        data = generate_ohlcv(days=10, seed=42)
        data["Signal"] = 0  # no signals
        fig = build_signals_chart(data, "NoSignals", "#00d4ff")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1  # price line only

    def test_drawdown_chart(self):
        data = generate_ohlcv(days=100, seed=42)
        strategy = MovingAverageCrossover()
        bt = Backtest(strategy=strategy)
        bt.run(data)
        fig = build_drawdown_chart(bt.results, "MA_Crossover")
        assert isinstance(fig, go.Figure)

    def test_portfolio_comparison(self, deserialized_result):
        fig = build_portfolio_comparison(
            deserialized_result["strategies"],
            deserialized_result["buy_hold"]["Total Return (%)"],
        )
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 3  # one trace per strategy

    def test_walk_forward_chart(self, deserialized_result):
        wf = deserialized_result["walk_forward"][0]
        fig = build_wf_chart(wf)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2  # in-sample + out-of-sample bars


# ── View builder tests ───────────────────────────────────────────


class TestViewBuilders:
    def test_summary_view_returns_div(self, deserialized_result):
        view = build_summary_view(deserialized_result)
        assert isinstance(view, html.Div)

    def test_strategy_detail_each_index(self, deserialized_result):
        """build_strategy_detail should work for every strategy index."""
        for i in range(len(deserialized_result["strategies"])):
            view = build_strategy_detail(deserialized_result, i)
            assert isinstance(view, html.Div)

    def test_strategy_detail_contains_back_button(self, deserialized_result):
        view = build_strategy_detail(deserialized_result, 0)
        # First child should be the back button with pattern-matching ID
        import dash_bootstrap_components as dbc
        back_btn = view.children[0]
        assert isinstance(back_btn, dbc.Button)
        assert isinstance(back_btn.id, dict), "Back button must use pattern-matching ID"
        assert back_btn.id == {"type": "back-btn", "index": 0}

    def test_summary_view_with_negative_returns(self):
        """Summary view should handle strategies with all-negative returns."""
        data = generate_ohlcv(days=200, seed=99)
        strategy = MovingAverageCrossover(fast_period=5, slow_period=10)
        signals_df = strategy.generate_signals(data.copy())
        bt = Backtest(strategy=strategy, initial_capital=INITIAL_CAPITAL,
                      commission=0.05, slippage=0.05)  # high costs
        bt.run(data)
        metrics = bt.get_metrics()

        wf_engine = WalkForwardEngine(n_splits=3, gap_days=5)
        wf = wf_engine.run(strategy, data)
        buy_hold = benchmark_buy_and_hold(data)

        result = {
            "ticker": "BAD",
            "data": data,
            "buy_hold": buy_hold,
            "strategies": [{
                "name": strategy.name,
                "signals_df": signals_df,
                "backtest_results": bt.results,
                "metrics": metrics,
            }],
            "walk_forward": [wf],
        }
        view = build_summary_view(result)
        assert isinstance(view, html.Div)

    def test_render_main_summary_when_no_strategy_selected(self, store_data):
        """render_main with selected_strategy=-1 returns summary view."""
        from dashboard.app import render_main
        result = render_main(store_data, -1)
        assert isinstance(result, html.Div)

    def test_render_main_detail_when_strategy_selected(self, store_data):
        """render_main with selected_strategy=0 returns detail view."""
        from dashboard.app import render_main
        result = render_main(store_data, 0)
        assert isinstance(result, html.Div)

    def test_render_main_each_strategy_index(self, store_data):
        """render_main should work for each valid strategy index."""
        from dashboard.app import render_main
        for i in range(len(store_data["strategies"])):
            result = render_main(store_data, i)
            assert isinstance(result, html.Div)

    def test_render_main_out_of_range_index_returns_summary(self, store_data):
        """Out-of-range strategy index should fall through to summary."""
        from dashboard.app import render_main
        result = render_main(store_data, 99)
        assert isinstance(result, html.Div)

    def test_navigation_cycle_summary_detail_back_detail(self, store_data):
        """Regression: navigating summary → detail → back → detail broke because
        Dash lost track of a string-ID 'back-to-summary' after the detail view
        was removed. Pattern-matching IDs fix this."""
        from dashboard.app import render_main
        # Summary
        r = render_main(store_data, -1)
        assert isinstance(r, html.Div)
        # Detail (strategy 0)
        r = render_main(store_data, 0)
        assert isinstance(r, html.Div)
        # Back to summary
        r = render_main(store_data, -1)
        assert isinstance(r, html.Div)
        # Detail again (strategy 1) — this is where the old bug hit
        r = render_main(store_data, 1)
        assert isinstance(r, html.Div)
        # Back and into strategy 2
        r = render_main(store_data, -1)
        assert isinstance(r, html.Div)
        r = render_main(store_data, 2)
        assert isinstance(r, html.Div)
