"""
Walk-forward analysis visualizations.

Charts for understanding train/test splits, in-sample vs out-of-sample
performance, parameter sensitivity, and the degradation ratio.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_walk_forward_splits(
    data: pd.DataFrame,
    splits_info: list[dict],
    title: str = "Walk-Forward Splits",
) -> go.Figure:
    """Show train/test windows as colored bands on the price chart.

    Args:
        data: OHLCV DataFrame with Date and Close columns.
        splits_info: List of dicts from WalkForwardEngine.get_splits_info().
        title: Chart title.
    """
    fig = go.Figure()

    # Price line
    fig.add_trace(go.Scatter(
        x=data["Date"],
        y=data["Close"],
        mode="lines",
        name="Price",
        line=dict(color="#2196F3", width=1.5),
    ))

    # Color bands for each fold
    train_color = "rgba(76, 175, 80, 0.15)"
    test_color = "rgba(255, 152, 0, 0.2)"

    for info in splits_info:
        # Train period
        fig.add_vrect(
            x0=info["train_start"], x1=info["train_end"],
            fillcolor=train_color,
            layer="below",
            line_width=0,
            annotation_text=f"Train {info['fold']}",
            annotation_position="top left",
            annotation_font_size=9,
        )
        # Test period
        fig.add_vrect(
            x0=info["test_start"], x1=info["test_end"],
            fillcolor=test_color,
            layer="below",
            line_width=0,
            annotation_text=f"Test {info['fold']}",
            annotation_position="top left",
            annotation_font_size=9,
        )

    fig.update_layout(
        title=title,
        yaxis_title="Price",
        template="plotly_white",
        height=450,
        margin=dict(l=50, r=50, t=50, b=30),
    )

    return fig


def plot_in_vs_out_sample(
    walk_forward_result,
    metric: str = "Sharpe Ratio",
) -> go.Figure:
    """Grouped bar chart comparing in-sample vs out-of-sample metrics per fold.

    This is the most important chart for detecting overfitting:
    large gaps between in-sample and out-of-sample = overfit.

    Args:
        walk_forward_result: WalkForwardResult from WalkForwardEngine.run().
        metric: Which metric to compare.
    """
    folds = walk_forward_result.folds
    fold_labels = [f"Fold {f.fold_index}" for f in folds]
    is_values = [f.in_sample_metrics.get(metric, 0) for f in folds]
    oos_values = [f.out_of_sample_metrics.get(metric, 0) for f in folds]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="In-Sample",
        x=fold_labels,
        y=is_values,
        marker_color="#4CAF50",
    ))

    fig.add_trace(go.Bar(
        name="Out-of-Sample",
        x=fold_labels,
        y=oos_values,
        marker_color="#FF9800",
    ))

    # Degradation ratio annotation
    deg_ratio = walk_forward_result.degradation_ratio
    color = "#4CAF50" if deg_ratio > 0.7 else "#FF9800" if deg_ratio > 0.3 else "#F44336"

    fig.update_layout(
        title=f"{walk_forward_result.strategy_name} — In-Sample vs Out-of-Sample ({metric})",
        yaxis_title=metric,
        barmode="group",
        template="plotly_white",
        height=400,
        margin=dict(l=50, r=50, t=80, b=30),
        annotations=[dict(
            text=f"Degradation Ratio: {deg_ratio}",
            xref="paper", yref="paper",
            x=0.99, y=1.05,
            showarrow=False,
            font=dict(size=14, color=color),
        )],
    )

    return fig


def plot_parameter_sensitivity(
    stability_results: pd.DataFrame,
    x_param: str,
    y_param: str | None = None,
    metric: str = "Sharpe Ratio",
) -> go.Figure:
    """Heatmap or line chart of performance vs parameter values.

    Args:
        stability_results: DataFrame from parameter_stability_test().
        x_param: Parameter for x-axis.
        y_param: Optional second parameter for heatmap y-axis.
            If None, creates a line chart.
        metric: Metric to plot.
    """
    if y_param and y_param in stability_results.columns:
        # 2D heatmap
        pivot = stability_results.pivot_table(
            index=y_param, columns=x_param, values=metric, aggfunc="mean"
        )
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=[str(x) for x in pivot.columns],
            y=[str(y) for y in pivot.index],
            colorscale="RdYlGn",
            text=np.round(pivot.values, 2),
            texttemplate="%{text}",
            colorbar_title=metric,
        ))
        fig.update_layout(
            title=f"Parameter Sensitivity: {metric}",
            xaxis_title=x_param,
            yaxis_title=y_param,
            template="plotly_white",
            height=400,
        )
    else:
        # 1D line chart
        grouped = stability_results.groupby(x_param)[metric].mean().reset_index()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=grouped[x_param],
            y=grouped[metric],
            mode="lines+markers",
            line=dict(color="#2196F3", width=2),
            marker=dict(size=8),
        ))
        fig.update_layout(
            title=f"Parameter Sensitivity: {metric} vs {x_param}",
            xaxis_title=x_param,
            yaxis_title=metric,
            template="plotly_white",
            height=400,
        )

    return fig


def plot_degradation_summary(
    results: list,
) -> go.Figure:
    """Compare degradation ratios across multiple strategies.

    Args:
        results: List of WalkForwardResult objects.
    """
    names = [r.strategy_name for r in results]
    ratios = [r.degradation_ratio for r in results]
    colors = [
        "#4CAF50" if r > 0.7 else "#FF9800" if r > 0.3 else "#F44336"
        for r in ratios
    ]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=names,
        y=ratios,
        marker_color=colors,
        text=[f"{r:.2f}" for r in ratios],
        textposition="outside",
    ))

    fig.add_hline(
        y=1.0, line_dash="dash", line_color="gray",
        annotation_text="Perfect (1.0)", annotation_position="top left",
    )
    fig.add_hline(
        y=0.7, line_dash="dot", line_color="#4CAF50",
        annotation_text="Good (0.7)", annotation_position="bottom left",
    )

    fig.update_layout(
        title="Strategy Robustness — Degradation Ratios",
        yaxis_title="Degradation Ratio (OOS/IS Sharpe)",
        template="plotly_white",
        height=400,
        yaxis_range=[min(0, min(ratios) - 0.2), max(1.5, max(ratios) + 0.2)],
    )

    return fig
