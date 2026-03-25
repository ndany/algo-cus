"""
Core visualization module using Plotly for interactive charts.

All functions return plotly.graph_objects.Figure objects that can be:
- Displayed in Jupyter notebooks
- Saved as standalone HTML files
- Embedded in the Dash dashboard
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import OUTPUT_DIR


def save_figure(fig: go.Figure, filename: str) -> Path:
    """Save a plotly figure as an interactive HTML file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{filename}.html"
    fig.write_html(str(path))
    return path


def plot_candlestick(
    data: pd.DataFrame,
    title: str = "Price Chart",
    show_volume: bool = True,
) -> go.Figure:
    """Interactive candlestick chart with optional volume bars.

    Args:
        data: DataFrame with Date, Open, High, Low, Close, Volume columns.
        title: Chart title.
        show_volume: Whether to show volume subplot.
    """
    if show_volume:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.75, 0.25],
            subplot_titles=[title, "Volume"],
        )
    else:
        fig = make_subplots(rows=1, cols=1, subplot_titles=[title])

    fig.add_trace(
        go.Candlestick(
            x=data["Date"],
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            name="OHLC",
        ),
        row=1, col=1,
    )

    if show_volume and "Volume" in data.columns:
        colors = [
            "#26a69a" if c >= o else "#ef5350"
            for c, o in zip(data["Close"], data["Open"])
        ]
        fig.add_trace(
            go.Bar(
                x=data["Date"],
                y=data["Volume"],
                marker_color=colors,
                name="Volume",
                showlegend=False,
            ),
            row=2, col=1,
        )

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        height=600 if show_volume else 400,
        margin=dict(l=50, r=50, t=50, b=30),
    )

    return fig


def plot_strategy_signals(
    data: pd.DataFrame,
    strategy_name: str = "Strategy",
    price_col: str = "Close",
    signal_col: str = "Signal",
) -> go.Figure:
    """Price chart with buy/sell signal markers overlaid.

    Args:
        data: DataFrame with Date, price column, and Signal column.
        strategy_name: Name for the chart title.
        price_col: Column to plot as the price line.
        signal_col: Column containing signal values (1=buy, -1=sell).
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=data["Date"],
        y=data[price_col],
        mode="lines",
        name="Price",
        line=dict(color="#2196F3", width=1.5),
    ))

    buys = data[data[signal_col] == 1]
    if not buys.empty:
        fig.add_trace(go.Scatter(
            x=buys["Date"],
            y=buys[price_col],
            mode="markers",
            name="Buy",
            marker=dict(
                symbol="triangle-up",
                size=12,
                color="#26a69a",
                line=dict(width=1, color="#004d40"),
            ),
        ))

    sells = data[data[signal_col] == -1]
    if not sells.empty:
        fig.add_trace(go.Scatter(
            x=sells["Date"],
            y=sells[price_col],
            mode="markers",
            name="Sell",
            marker=dict(
                symbol="triangle-down",
                size=12,
                color="#ef5350",
                line=dict(width=1, color="#b71c1c"),
            ),
        ))

    fig.update_layout(
        title=f"{strategy_name} — Buy/Sell Signals",
        yaxis_title="Price",
        template="plotly_white",
        height=450,
        margin=dict(l=50, r=50, t=50, b=30),
    )

    return fig


def plot_portfolio_comparison(
    results: dict[str, pd.DataFrame],
    initial_capital: float = 10_000.0,
) -> go.Figure:
    """Overlay equity curves for multiple strategies.

    Args:
        results: {strategy_name: backtest_results_DataFrame}.
            Each DataFrame must have Date and Portfolio_Value columns.
        initial_capital: Starting capital (shown as reference line).
    """
    fig = go.Figure()

    colors = ["#2196F3", "#FF9800", "#4CAF50", "#9C27B0", "#F44336", "#00BCD4"]

    for i, (name, df) in enumerate(results.items()):
        color = colors[i % len(colors)]
        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=df["Portfolio_Value"],
            mode="lines",
            name=name,
            line=dict(color=color, width=2),
        ))

    fig.add_hline(
        y=initial_capital,
        line_dash="dash",
        line_color="gray",
        annotation_text="Starting Capital",
        annotation_position="bottom left",
    )

    fig.update_layout(
        title="Portfolio Value Comparison",
        yaxis_title="Portfolio Value ($)",
        template="plotly_white",
        height=450,
        margin=dict(l=50, r=50, t=50, b=30),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )

    return fig


def plot_drawdown(
    data: pd.DataFrame,
    portfolio_col: str = "Portfolio_Value",
    title: str = "Drawdown",
) -> go.Figure:
    """Visualize drawdown over time.

    Args:
        data: DataFrame with Date and portfolio value column.
        portfolio_col: Column containing portfolio values.
        title: Chart title.
    """
    cummax = data[portfolio_col].cummax()
    drawdown = (data[portfolio_col] - cummax) / cummax * 100

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=data["Date"],
        y=drawdown,
        fill="tozeroy",
        name="Drawdown",
        line=dict(color="#ef5350", width=1),
        fillcolor="rgba(239, 83, 80, 0.3)",
    ))

    fig.update_layout(
        title=title,
        yaxis_title="Drawdown (%)",
        template="plotly_white",
        height=300,
        margin=dict(l=50, r=50, t=50, b=30),
    )

    return fig


def plot_metrics_table(
    metrics_list: list[dict],
) -> go.Figure:
    """Render backtest metrics as an interactive table.

    Args:
        metrics_list: List of metric dicts from Backtest.get_metrics().
    """
    if not metrics_list:
        return go.Figure()

    headers = list(metrics_list[0].keys())
    values = [[m[h] for m in metrics_list] for h in headers]

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=[f"<b>{h}</b>" for h in headers],
            fill_color="#2196F3",
            font=dict(color="white", size=12),
            align="center",
        ),
        cells=dict(
            values=values,
            fill_color=[["#f5f5f5", "white"] * len(metrics_list)],
            align="center",
            font=dict(size=11),
        ),
    )])

    fig.update_layout(
        title="Strategy Performance Comparison",
        height=200 + 30 * len(metrics_list),
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return fig
