"""
AlgoStation — Trading Algorithm Dashboard

Dark-mode trader workstation with progressive disclosure:
  1. Enter ticker → Analyze
  2. Summary view: price chart, metrics, strategy comparison
  3. Click a strategy → detail view with signals, walk-forward, drawdown
"""

import os
import logging

from dotenv import load_dotenv
load_dotenv()  # Load .env file if present (local dev); no-op on Render

import dash
from dash import html, dcc, Input, Output, State, callback, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard.theme import COLORS, SERIES_COLORS, STRATEGY_COLORS, apply_dark_theme
from dashboard.analysis import run_analysis

logger = logging.getLogger(__name__)

# --- App Initialization ---
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True,
    title="AlgoStation",
    update_title="Analyzing...",
)
server = app.server  # Expose for gunicorn


# --- Auth Check ---
# Set SKIP_AUTH=1 for local dev (no Supabase needed). In production, set SKIP_AUTH=0.
SKIP_AUTH = os.environ.get("SKIP_AUTH", "1") == "1"

if not SKIP_AUTH:
    from dashboard.auth import (
        get_google_login_url, get_user_from_token,
        validate_invitation_code, consume_invitation_code,
        register_authorized_user, is_user_authorized,
    )


# ============================================================
# LAYOUT COMPONENTS
# ============================================================

def make_navbar(show_signout=False):
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
    if show_signout:
        children.append(
            dbc.Button("Sign out", id="signout-btn", outline=True, color="secondary",
                       size="sm", style={"fontSize": "12px", "padding": "4px 12px"}),
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


def make_login_page(message=None):
    status_children = []
    if message:
        status_children = [html.Span(message, style={
            "color": COLORS["accent_cyan"], "fontSize": "13px",
        })]

    return html.Div([
        html.Div([
            html.Div("ALGOSTATION", className="login-title"),
            html.Div("Trading Analysis Terminal", className="login-subtitle"),
            html.Div([
                html.Div("Enter your invitation code to access the terminal", style={
                    "color": COLORS["text_secondary"], "fontSize": "13px",
                    "marginBottom": "12px",
                }),
                dbc.Input(
                    id="invitation-code",
                    placeholder="XXXX-XXXX-XXXX",
                    className="invitation-input",
                    maxLength=20,
                ),
                dbc.Button(
                    "Access Terminal",
                    id="verify-code-btn",
                    className="btn-analyze",
                    style={"marginTop": "12px", "width": "100%"},
                    n_clicks=0,
                ),
                html.Div(id="invitation-status", children=status_children,
                         style={"marginTop": "8px"}),
            ]),
            html.Hr(style={"borderColor": COLORS["border"], "margin": "24px 0"}),
            html.A(
                dbc.Button([
                    # White Google "G" — clean on dark background
                    html.Img(src="data:image/svg+xml,"
                        "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E"
                        "%3Cpath fill='%23fff' d='M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92"
                        "a5.06 5.06 0 0 1-2.2 3.32l3.55 2.76c2.07-1.91 3.29-4.73 3.29-8.09z'/%3E"
                        "%3Cpath fill='%23fff' d='M12 23c2.97 0 5.46-.98 7.28-2.66l-3.55-2.76"
                        "c-.98.66-2.23 1.06-3.73 1.06-2.87 0-5.3-1.94-6.16-4.54l-3.66 2.84"
                        "A11.99 11.99 0 0 0 12 23z'/%3E"
                        "%3Cpath fill='%23fff' d='M5.84 14.1a7.2 7.2 0 0 1 0-4.2L2.18 7.06"
                        "A11.99 11.99 0 0 0 0 12c0 1.94.46 3.77 1.28 5.4l3.66-2.84z'/%3E"  # noqa: E501
                        "%3Cpath fill='%23fff' d='M12 4.75c1.62 0 3.06.56 4.21 1.64l3.15-3.15"
                        "C17.45 1.09 14.97 0 12 0 7.31 0 3.25 2.7 1.28 6.61l3.66 2.84"
                        "c.87-2.6 3.3-4.54 6.16-4.54z'/%3E%3C/svg%3E",  # noqa: E501
                        style={"width": "18px", "height": "18px", "marginRight": "10px",
                               "verticalAlign": "middle"}),
                    html.Span("Sign in with Google",
                              style={"verticalAlign": "middle"}),
                ], className="btn-google"),
                id="google-login-link",
                href="#",
            ),
            html.Div("For returning users with linked accounts", style={
                "color": COLORS["text_muted"], "fontSize": "11px",
                "marginTop": "8px", "textAlign": "center",
            }),
        ], className="login-card"),
    ], className="login-container")


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


# ============================================================
# CHART BUILDERS (dark themed)
# ============================================================

def build_candlestick(data, ticker):
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


# ============================================================
# LAYOUT BUILDERS
# ============================================================

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
            "← Back to Summary",
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


# ============================================================
# APP LAYOUT
# ============================================================


def _make_app_shell():
    """The authenticated app layout."""
    return html.Div([
        make_navbar(show_signout=not SKIP_AUTH),
        make_ticker_bar(),
        dbc.Container(id="main-content", fluid=True,
                      style={"padding": "20px 24px", "maxWidth": "1400px"}),
    ])


if SKIP_AUTH:
    # No auth — go straight to the app
    app.layout = html.Div([
        dcc.Store(id="analysis-store"),
        dcc.Store(id="selected-strategy", data=-1),
        dcc.Location(id="url", refresh=False),
        _make_app_shell(),
    ])
else:
    # Auth enabled — page-container swaps between login and app
    app.layout = html.Div([
        dcc.Store(id="analysis-store"),
        dcc.Store(id="selected-strategy", data=-1),
        dcc.Store(id="auth-store", storage_type="session"),
        dcc.Location(id="url", refresh=False),
        html.Div(id="page-container"),
    ])


# ============================================================
# AUTH CALLBACKS (only when auth is enabled)
# ============================================================

if not SKIP_AUTH:
    @callback(
        Output("page-container", "children"),
        Output("auth-store", "data"),
        Input("url", "href"),
        State("auth-store", "data"),
    )
    def route_page(href, auth_data):
        """Show login or app based on auth state and URL tokens."""
        # Already authenticated via session store
        if auth_data and auth_data.get("authenticated"):
            return _make_app_shell(), auth_data

        logger.info(f"route_page: href={'[has access_token]' if href and 'access_token' in href else href and href[:80] or 'None'}")

        # Check for OAuth callback with access_token in URL fragment
        # (implicit flow returns #access_token=...&token_type=...)
        if href and "access_token=" in href:
            from urllib.parse import urlparse, parse_qs
            fragment = urlparse(href).fragment
            params = parse_qs(fragment)
            token = params.get("access_token", [None])[0]

            if token:
                user = get_user_from_token(token)
                if user:
                    # Auto-register on first Google sign-in
                    if not is_user_authorized(user["id"]):
                        register_authorized_user(user["id"], user["email"],
                                                 user.get("name", user["email"]))
                    return _make_app_shell(), {
                        "authenticated": True,
                        "user": user,
                        "token": token,
                    }

        # Not authenticated — show login page
        return make_login_page(), no_update

    @callback(
        Output("google-login-link", "href"),
        Input("url", "href"),
    )
    def set_google_login_url(href):
        """Generate the Google OAuth URL with the current page as redirect."""
        if not href:
            return "#"
        try:
            return get_google_login_url(redirect_to=href.split("#")[0])
        except Exception as e:
            logger.warning(f"Failed to generate Google login URL: {e}")
            return "#"

    @callback(
        Output("invitation-status", "children"),
        Output("auth-store", "data", allow_duplicate=True),
        Input("verify-code-btn", "n_clicks"),
        State("invitation-code", "value"),
        State("auth-store", "data"),
        prevent_initial_call=True,
    )
    def verify_invitation(n_clicks, code, auth_data):
        """Validate an invitation code and grant access."""
        if not code or not code.strip():
            return html.Span("Enter a code",
                             style={"color": COLORS["accent_orange"], "fontSize": "12px"}), no_update

        code = code.strip().upper()

        # If user signed in with Google, link the code to their account
        user = (auth_data or {}).get("google_user")
        identity = user["email"] if user else f"code:{code}"

        if not validate_invitation_code(code, user_identity=identity):
            return html.Span("Invalid or already claimed by another user",
                             style={"color": COLORS["accent_red"], "fontSize": "12px"}), no_update

        if user:
            consume_invitation_code(code, user["email"])
            register_authorized_user(user["id"], user["email"], user["name"])
            token = (auth_data or {}).get("token", "")
            return no_update, {"authenticated": True, "user": user, "token": token}

        # No Google sign-in — grant access with code only
        consume_invitation_code(code, identity)
        return no_update, {
            "authenticated": True,
            "user": {"email": identity, "name": "Guest"},
        }

    @callback(
        Output("auth-store", "data", allow_duplicate=True),
        Output("page-container", "children", allow_duplicate=True),
        Input("signout-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def sign_out(n_clicks):
        """Clear auth state and return to login page."""
        return {}, make_login_page()


# ============================================================
# CALLBACKS
# ============================================================

@callback(
    Output("analysis-store", "data"),
    Output("status-bar", "children"),
    Input("analyze-btn", "n_clicks"),
    State("ticker-input", "value"),
    prevent_initial_call=True,
)
def on_analyze(n_clicks, ticker):
    if not ticker or not ticker.strip():
        return no_update, "Enter a ticker symbol"

    ticker = ticker.strip().upper()

    try:
        result = run_analysis(ticker)
        # Store serializable data (not DataFrames)
        store_data = {
            "ticker": result["ticker"],
            "elapsed": result["elapsed"],
            "data_json": result["data"].to_json(date_format="iso"),
            "strategies": [],
            "buy_hold": result["buy_hold"],
            "walk_forward": [],
            "wf_splits_info": result["wf_splits_info"],
        }

        for sr in result["strategies"]:
            store_data["strategies"].append({
                "name": sr["name"],
                "signals_json": sr["signals_df"].to_json(date_format="iso"),
                "results_json": sr["backtest_results"].to_json(date_format="iso"),
                "metrics": sr["metrics"],
            })

        for wf in result["walk_forward"]:
            store_data["walk_forward"].append({
                "strategy_name": wf.strategy_name,
                "degradation_ratio": wf.degradation_ratio,
                "folds": [
                    {
                        "fold_index": f.fold_index,
                        "is_metrics": f.in_sample_metrics,
                        "oos_metrics": f.out_of_sample_metrics,
                    }
                    for f in wf.folds
                ],
            })

        status = f"✓ {ticker} analyzed in {result['elapsed']}s — {len(result['data'])} data points"
        return store_data, html.Span(status, style={"color": COLORS["accent_green"]})

    except Exception as e:
        logger.exception(f"Analysis failed for {ticker}")
        return no_update, html.Span(f"Error: {e}", style={"color": COLORS["accent_red"]})


@callback(
    Output("main-content", "children"),
    Input("analysis-store", "data"),
    Input("selected-strategy", "data"),
)
def render_main(store_data, selected_strategy):
    if not store_data:
        return make_empty_state()

    import io
    import pandas as pd

    # Reconstruct DataFrames from JSON (StringIO required — pandas treats raw strings as file paths)
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
        signals_df = pd.read_json(io.StringIO(sr["signals_json"])).sort_values("Date").reset_index(drop=True)
        results_df = pd.read_json(io.StringIO(sr["results_json"])).sort_values("Date").reset_index(drop=True)
        result["strategies"].append({
            "name": sr["name"],
            "signals_df": signals_df,
            "backtest_results": results_df,
            "metrics": sr["metrics"],
        })

    # Reconstruct lightweight WF result objects
    class WFProxy:
        def __init__(self, d):
            self.strategy_name = d["strategy_name"]
            self.degradation_ratio = d["degradation_ratio"]
            self.folds = [type("Fold", (), {
                "fold_index": f["fold_index"],
                "in_sample_metrics": f["is_metrics"],
                "out_of_sample_metrics": f["oos_metrics"],
            })() for f in d["folds"]]

    result["walk_forward"] = [WFProxy(wf) for wf in store_data["walk_forward"]]

    if selected_strategy >= 0 and selected_strategy < len(result["strategies"]):
        return build_strategy_detail(result, selected_strategy)

    return build_summary_view(result)


@callback(
    Output("selected-strategy", "data"),
    Input({"type": "strategy-card", "index": dash.ALL}, "n_clicks"),
    Input({"type": "back-btn", "index": dash.ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def handle_navigation(card_clicks, back_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update

    trigger = ctx.triggered[0]["prop_id"]

    if "back-btn" in trigger:
        return -1

    # Parse which strategy card was clicked
    if "strategy-card" in trigger:
        for i, clicks in enumerate(card_clicks or []):
            if clicks:
                return i

    return no_update


# Allow triggering analyze with Enter key
@callback(
    Output("analyze-btn", "n_clicks"),
    Input("ticker-input", "n_submit"),
    State("analyze-btn", "n_clicks"),
    prevent_initial_call=True,
)
def submit_on_enter(n_submit, current_clicks):
    return (current_clicks or 0) + 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    debug = os.environ.get("DASH_DEBUG", "1") == "1"
    app.run(debug=debug, host="0.0.0.0", port=port)
