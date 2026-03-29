"""
Dashboard layout components.

Summary view, strategy detail view, empty state, metric tiles,
navbar, ticker bar, and reports view.
"""

import dash_bootstrap_components as dbc
from dash import html, dcc

from dashboard.theme import COLORS, SERIES_COLORS
from dashboard.charts import (
    build_candlestick, build_signals_chart,
    build_portfolio_comparison, build_drawdown_chart, build_wf_chart,
)


def make_navbar(show_signout=False, user_role=None):
    children = [
        dbc.NavbarBrand(
            [html.Span("ALGO", style={"color": COLORS["accent_cyan"]}),
             html.Span("STATION", style={"color": COLORS["text_secondary"]})],
            className="navbar-brand",
        ),
        html.Div([
            html.Span("TRADING ANALYSIS TERMINAL",
                       style={"color": COLORS["text_muted"], "fontSize": "11px",
                              "letterSpacing": "2px", "fontWeight": "600"}),
        ], style={"flex": "1"}),
    ]
    # Reports link — hidden by default, shown for admins via callback
    children.append(
        html.A("Reports", id="reports-link", className="reports-link",
               style={"cursor": "pointer", "display": "none"}),
    )
    if show_signout:
        children.append(
            dbc.Button("Sign out", href="/auth/signout", external_link=True,
                       className="btn-signout"),
        )
    return dbc.Navbar(
        dbc.Container(children, fluid=True,
                      style={"display": "flex", "alignItems": "center"}),
        className="navbar",
        dark=True,
    )


def make_ticker_bar():
    return html.Div([
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    dbc.InputGroup([
                        dbc.Input(
                            id="ticker-input",
                            placeholder="Enter ticker (e.g. AMZN)",
                            className="ticker-input",
                            debounce=True,
                            maxLength=10,
                        ),
                        dbc.Button(
                            "ANALYZE",
                            id="analyze-btn",
                            className="btn-analyze",
                            n_clicks=0,
                        ),
                    ], size="lg"),
                ], md=6, lg=4),
                dbc.Col([
                    html.Div(id="status-bar", style={
                        "color": COLORS["text_secondary"],
                        "fontSize": "13px",
                        "lineHeight": "48px",
                    }),
                ], md=6, lg=8),
            ], align="center"),
        ], fluid=True),
    ], style={
        "backgroundColor": COLORS["bg_secondary"],
        "borderBottom": f"1px solid {COLORS['border']}",
        "padding": "12px 0",
    })


def make_empty_state():
    return html.Div([
        html.Div([
            html.Div(style={
                "width": "80px", "height": "80px", "margin": "0 auto 24px",
                "border": f"2px solid {COLORS['border']}", "borderRadius": "50%",
                "display": "flex", "alignItems": "center", "justifyContent": "center",
                "fontSize": "32px", "color": COLORS["text_muted"],
            }, children="$"),
            html.H4("Enter a ticker to begin",
                     style={"color": COLORS["text_secondary"], "fontWeight": "400"}),
            html.P("Type a stock symbol above and click ANALYZE to run backtests, "
                    "walk-forward validation, and strategy comparison.",
                    style={"color": COLORS["text_muted"], "maxWidth": "480px",
                           "margin": "0 auto", "fontSize": "14px"}),
        ], style={"textAlign": "center", "padding": "100px 20px"}),
    ])


def make_metric_tile(label, value, is_pct=False, is_currency=False, good_positive=True):
    if isinstance(value, (int, float)):
        if is_currency:
            display = f"${value:,.0f}"
        elif is_pct:
            display = f"{value:+.2f}%"
        else:
            display = f"{value:.2f}"

        if good_positive:
            css_class = "metric-value positive" if value > 0 else "metric-value negative" if value < 0 else "metric-value"
        else:
            css_class = "metric-value negative" if value > 0 else "metric-value positive" if value < 0 else "metric-value"
    else:
        display = str(value)
        css_class = "metric-value"

    return html.Div([
        html.Div(display, className=css_class),
        html.Div(label, className="metric-label"),
    ], className="metric-tile")


def build_summary_view(result):
    data = result["data"]
    strategies = result["strategies"]
    buy_hold = result["buy_hold"]
    wf_results = result["walk_forward"]
    ticker = result["ticker"]

    # Metric tiles row
    best_strategy = max(strategies, key=lambda s: s["metrics"]["Total Return (%)"])
    worst_dd = min(s["metrics"]["Max Drawdown (%)"] for s in strategies)

    metrics_row = dbc.Row([
        dbc.Col(make_metric_tile("Ticker", ticker), md=2),
        dbc.Col(make_metric_tile("Buy & Hold", buy_hold["Total Return (%)"], is_pct=True), md=2),
        dbc.Col(make_metric_tile("Best Strategy", best_strategy["metrics"]["Total Return (%)"], is_pct=True), md=2),
        dbc.Col(make_metric_tile("Best Sharpe", best_strategy["metrics"]["Sharpe Ratio"]), md=2),
        dbc.Col(make_metric_tile("Max Drawdown", worst_dd, is_pct=True, good_positive=False), md=2),
        dbc.Col(make_metric_tile("Data Points", len(data)), md=2),
    ], className="g-0", style={
        "backgroundColor": COLORS["bg_secondary"],
        "border": f"1px solid {COLORS['border']}",
        "borderRadius": "8px", "padding": "8px 0", "marginBottom": "16px",
    })

    # Candlestick chart
    candlestick = html.Div([
        dcc.Graph(figure=build_candlestick(data, ticker), config={"displayModeBar": False}),
    ], className="panel")

    # Portfolio comparison
    portfolio = html.Div([
        dcc.Graph(
            figure=build_portfolio_comparison(strategies, buy_hold["Total Return (%)"]),
            config={"displayModeBar": False},
        ),
    ], className="panel")

    # Strategy cards
    strategy_cards = []
    for i, sr in enumerate(strategies):
        m = sr["metrics"]
        wf = wf_results[i] if i < len(wf_results) else None
        deg = wf.degradation_ratio if wf else 0

        ret_color = COLORS["accent_green"] if m["Total Return (%)"] > 0 else COLORS["accent_red"]
        deg_color = COLORS["accent_green"] if deg > 0.7 else COLORS["accent_orange"] if deg > 0.3 else COLORS["accent_red"]

        card = dbc.Col(
            html.Div([
                html.Div(sr["name"], className="strategy-name"),
                html.Div([
                    html.Span(f"{m['Total Return (%)']:+.1f}%",
                              className="strategy-metric",
                              style={"color": ret_color}),
                    html.Span(f"  Sharpe {m['Sharpe Ratio']:.2f}",
                              style={"color": COLORS["text_secondary"], "fontSize": "13px"}),
                ]),
                html.Div([
                    html.Span(f"Trades: {m['Number of Trades']}",
                              style={"color": COLORS["text_secondary"], "fontSize": "12px"}),
                    html.Span(f"  Win: {m['Win Rate (%)']:.0f}%",
                              style={"color": COLORS["text_secondary"], "fontSize": "12px"}),
                    html.Span(f"  Robustness: {deg:.2f}",
                              style={"color": deg_color, "fontSize": "12px"}),
                ], style={"marginTop": "8px"}),
            ], className="strategy-card", id={"type": "strategy-card", "index": i}),
            md=4,
        )
        strategy_cards.append(card)

    cards_row = dbc.Row(strategy_cards, className="g-3", style={"marginBottom": "16px"})

    return html.Div([
        metrics_row,
        candlestick,
        portfolio,
        html.Div([
            html.Div("STRATEGIES", className="panel-header"),
            html.P("Click a strategy for detailed analysis",
                    style={"color": COLORS["text_muted"], "fontSize": "12px",
                           "marginBottom": "12px"}),
            cards_row,
        ]),
    ])


def build_strategy_detail(result, strategy_index):
    sr = result["strategies"][strategy_index]
    wf = result["walk_forward"][strategy_index] if strategy_index < len(result["walk_forward"]) else None

    signals_chart = dcc.Graph(
        figure=build_signals_chart(sr["signals_df"], sr["name"], SERIES_COLORS[strategy_index]),
        config={"displayModeBar": False},
    )

    drawdown_chart = dcc.Graph(
        figure=build_drawdown_chart(sr["backtest_results"], sr["name"]),
        config={"displayModeBar": False},
    )

    wf_chart = dcc.Graph(
        figure=build_wf_chart(wf),
        config={"displayModeBar": False},
    ) if wf else html.Div()

    m = sr["metrics"]
    metrics_grid = dbc.Row([
        dbc.Col(make_metric_tile("Return", m["Total Return (%)"], is_pct=True), md=2),
        dbc.Col(make_metric_tile("Sharpe", m["Sharpe Ratio"]), md=2),
        dbc.Col(make_metric_tile("Max DD", m["Max Drawdown (%)"], is_pct=True, good_positive=False), md=2),
        dbc.Col(make_metric_tile("Trades", m["Number of Trades"]), md=2),
        dbc.Col(make_metric_tile("Win Rate", m["Win Rate (%)"], is_pct=True), md=2),
        dbc.Col(make_metric_tile("Final Value", m["Final Value ($)"], is_currency=True), md=2),
    ], className="g-0", style={
        "backgroundColor": COLORS["bg_secondary"],
        "border": f"1px solid {COLORS['border']}",
        "borderRadius": "8px", "padding": "8px 0", "marginBottom": "16px",
    })

    return html.Div([
        dbc.Button(
            "\u2190 Back to Summary",
            id={"type": "back-btn", "index": 0},
            outline=True,
            color="secondary",
            size="sm",
            style={"marginBottom": "16px"},
        ),
        html.H5(sr["name"], style={
            "color": COLORS["text_primary"],
            "fontFamily": "JetBrains Mono, monospace",
            "marginBottom": "16px",
        }),
        metrics_grid,
        html.Div(signals_chart, className="panel"),
        dbc.Row([
            dbc.Col(html.Div(drawdown_chart, className="panel"), md=6),
            dbc.Col(html.Div(wf_chart, className="panel"), md=6),
        ]),
    ])


def build_reports_view():
    """Admin reports page with tabbed views."""
    from dashboard.reporting import (
        get_active_users, get_top_tickers,
        get_expressed_interest, get_login_frequency,
    )

    def make_report_table(data, columns=None):
        if data is None:
            return html.Div("Reports unavailable \u2014 no database connection",
                           style={"color": COLORS["accent_orange"], "padding": "20px"})
        if not data:
            return html.Div("No data available",
                           style={"color": COLORS["text_muted"], "padding": "20px"})
        if columns is None:
            columns = list(data[0].keys())
        header = html.Tr([html.Th(c.replace("_", " ").title(),
                    style={"color": COLORS["text_secondary"], "padding": "8px 12px",
                           "borderBottom": f"1px solid {COLORS['border']}",
                           "fontSize": "12px", "fontWeight": "600"})
                    for c in columns])
        rows = []
        for row in data:
            rows.append(html.Tr([
                html.Td(str(row.get(c, "")),
                    style={"color": COLORS["text_primary"], "padding": "8px 12px",
                           "borderBottom": f"1px solid {COLORS['border']}",
                           "fontSize": "13px"})
                for c in columns
            ]))
        return html.Table([html.Thead(header), html.Tbody(rows)],
                         style={"width": "100%", "borderCollapse": "collapse"})

    tabs = dbc.Tabs([
        dbc.Tab(html.Div(make_report_table(get_active_users()),
                style={"padding": "16px"}),
                label="Active Users", tab_id="active-users"),
        dbc.Tab(html.Div(make_report_table(get_top_tickers()),
                style={"padding": "16px"}),
                label="Top Tickers", tab_id="top-tickers"),
        dbc.Tab(html.Div(make_report_table(get_expressed_interest()),
                style={"padding": "16px"}),
                label="Expressed Interest", tab_id="interest"),
        dbc.Tab(html.Div(make_report_table(get_login_frequency()),
                style={"padding": "16px"}),
                label="Login Frequency", tab_id="logins"),
    ], active_tab="active-users")

    return html.Div([
        html.Div([
            html.A("\u2190 Back to Terminal", id="back-to-terminal",
                   style={"color": COLORS["accent_cyan"], "cursor": "pointer",
                          "fontSize": "13px", "textDecoration": "none"}),
        ], style={"marginBottom": "16px"}),
        html.Div("REPORTS", className="panel-header"),
        html.Div(tabs, className="panel", style={"marginTop": "8px"}),
    ])
