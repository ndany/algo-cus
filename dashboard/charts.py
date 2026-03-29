"""
Dark-themed chart builders for the dashboard.

Each function composes existing visualization modules with the
trader_dark Plotly template via apply_dark_theme(). These are
dashboard-specific presentations; the standalone visualization/*.py
charts remain composable for CLI/Jupyter use.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard.theme import COLORS, SERIES_COLORS, apply_dark_theme


def build_candlestick(data, ticker):
    """Candlestick + volume chart."""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.03, row_heights=[0.75, 0.25],
    )
    fig.add_trace(go.Candlestick(
        x=data["Date"], open=data["Open"], high=data["High"],
        low=data["Low"], close=data["Close"], name="OHLC",
        increasing_line_color=COLORS["accent_green"],
        decreasing_line_color=COLORS["accent_red"],
    ), row=1, col=1)

    colors = [
        COLORS["accent_green"] if c >= o else COLORS["accent_red"]
        for c, o in zip(data["Close"], data["Open"])
    ]
    fig.add_trace(go.Bar(
        x=data["Date"], y=data["Volume"], marker_color=colors,
        name="Volume", showlegend=False, opacity=0.5,
    ), row=2, col=1)

    fig.update_layout(xaxis_rangeslider_visible=False, height=500, showlegend=False)
    return apply_dark_theme(fig)


def build_signals_chart(signals_df, strategy_name, color):
    """Price chart with buy/sell signal markers."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=signals_df["Date"], y=signals_df["Close"],
        mode="lines", name="Price",
        line=dict(color=COLORS["text_muted"], width=1),
    ))

    buys = signals_df[signals_df["Signal"] == 1]
    if not buys.empty:
        fig.add_trace(go.Scatter(
            x=buys["Date"], y=buys["Close"],
            mode="markers", name="Buy",
            marker=dict(symbol="triangle-up", size=10,
                        color=COLORS["accent_green"],
                        line=dict(width=1, color="#004d40")),
        ))

    sells = signals_df[signals_df["Signal"] == -1]
    if not sells.empty:
        fig.add_trace(go.Scatter(
            x=sells["Date"], y=sells["Close"],
            mode="markers", name="Sell",
            marker=dict(symbol="triangle-down", size=10,
                        color=COLORS["accent_red"],
                        line=dict(width=1, color="#b71c1c")),
        ))

    fig.update_layout(
        title=f"{strategy_name} Signals", height=350,
        margin=dict(l=50, r=30, t=40, b=30),
    )
    return apply_dark_theme(fig)


def build_portfolio_comparison(strategy_results, buy_hold_return):
    """Multi-strategy portfolio value comparison chart."""
    fig = go.Figure()
    for i, sr in enumerate(strategy_results):
        name = sr["name"]
        color = SERIES_COLORS[i % len(SERIES_COLORS)]
        fig.add_trace(go.Scatter(
            x=sr["backtest_results"]["Date"],
            y=sr["backtest_results"]["Portfolio_Value"],
            mode="lines", name=name, line=dict(color=color, width=2),
        ))

    fig.add_hline(
        y=10_000, line_dash="dash", line_color=COLORS["text_muted"],
        annotation_text="Starting Capital",
        annotation_font_color=COLORS["text_muted"],
    )
    fig.update_layout(
        title="Portfolio Value Comparison", height=400,
        yaxis_title="Value ($)",
        legend=dict(orientation="h", y=-0.15),
    )
    return apply_dark_theme(fig)


def build_drawdown_chart(backtest_results, strategy_name):
    """Drawdown area chart for a single strategy."""
    pv = backtest_results["Portfolio_Value"]
    cummax = pv.cummax()
    dd = (pv - cummax) / cummax * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=backtest_results["Date"], y=dd,
        fill="tozeroy", name="Drawdown",
        line=dict(color=COLORS["accent_red"], width=1),
        fillcolor="rgba(255, 71, 87, 0.2)",
    ))
    fig.update_layout(
        title=f"{strategy_name} — Drawdown", height=250,
        yaxis_title="Drawdown (%)",
    )
    return apply_dark_theme(fig)


def build_wf_chart(wf_result):
    """Walk-forward in-sample vs out-of-sample Sharpe comparison."""
    folds = wf_result.folds
    fold_labels = [f"Fold {f.fold_index}" for f in folds]
    is_vals = [f.in_sample_metrics.get("Sharpe Ratio", 0) for f in folds]
    oos_vals = [f.out_of_sample_metrics.get("Sharpe Ratio", 0) for f in folds]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="In-Sample", x=fold_labels, y=is_vals,
        marker_color=COLORS["accent_green"], opacity=0.7,
    ))
    fig.add_trace(go.Bar(
        name="Out-of-Sample", x=fold_labels, y=oos_vals,
        marker_color=COLORS["accent_orange"], opacity=0.7,
    ))

    deg = wf_result.degradation_ratio
    deg_color = COLORS["accent_green"] if deg > 0.7 else COLORS["accent_orange"] if deg > 0.3 else COLORS["accent_red"]

    fig.update_layout(
        title=f"{wf_result.strategy_name} — Walk-Forward (Degradation: {deg})",
        barmode="group", height=300,
        yaxis_title="Sharpe Ratio",
        annotations=[dict(
            text=f"Degradation Ratio: {deg}", xref="paper", yref="paper",
            x=0.99, y=1.08, showarrow=False,
            font=dict(size=13, color=deg_color),
        )],
    )
    return apply_dark_theme(fig)
