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
        get_google_authorize_url, exchange_code_for_session,
        validate_invitation_code, consume_invitation_code,
        register_authorized_user, is_user_authorized,
        get_user_with_role,
    )
    from dashboard.telemetry import log_usage, log_access_attempt
    # Flask session secret — must be stable across gunicorn workers.
    server.secret_key = os.environ.get(
        "FLASK_SECRET_KEY", os.environ.get("SUPABASE_KEY", "change-me")
    )


# --- WSGI middleware for auth + proxy headers ---
# Dash wraps server.wsgi_app with its own middleware that intercepts ALL
# requests and serves the SPA index. Flask before_request and routes never
# fire. We must handle auth at the WSGI layer, outside Dash's middleware.

_INPUT_STYLE = ("width:100%;padding:12px;background:#1a2332;border:1px solid #1e293b;"
                "color:#e2e8f0;border-radius:6px;box-sizing:border-box")
_GOOGLE_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18"'
    ' style="vertical-align:middle;margin-right:10px">'
    '<path fill="#fff" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92'
    'a5.06 5.06 0 0 1-2.2 3.32l3.55 2.76c2.07-1.91 3.29-4.73 3.29-8.09z"/>'
    '<path fill="#fff" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.55-2.76'
    'c-.98.66-2.23 1.06-3.73 1.06-2.87 0-5.3-1.94-6.16-4.54l-3.66 2.84'
    'A11.99 11.99 0 0 0 12 23z"/>'
    '<path fill="#fff" d="M5.84 14.1a7.2 7.2 0 0 1 0-4.2L2.18 7.06'
    'A11.99 11.99 0 0 0 0 12c0 1.94.46 3.77 1.28 5.4l3.66-2.84z"/>'
    '<path fill="#fff" d="M12 4.75c1.62 0 3.06.56 4.21 1.64l3.15-3.15'
    'C17.45 1.09 14.97 0 12 0 7.31 0 3.25 2.7 1.28 6.61l3.66 2.84'
    'c.87-2.6 3.3-4.54 6.16-4.54z"/></svg>')


def _login_page(message=""):
    """Single login page: invitation code (optional) + Google sign-in button."""
    msg_html = (f'<div style="color:#ff4757;font-size:13px;margin-top:12px">{message}</div>'
                if message else "")
    return f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AlgoStation</title>
<link rel="stylesheet" href="/assets/style.css">
<style>body{{background:#0a0e17;margin:0;font-family:'Inter',sans-serif}}</style>
</head><body>
<div class="login-container"><div class="login-card">
<div class="login-title">ALGOSTATION</div>
<div style="color:#94a3b8;font-size:14px;margin-bottom:24px">Trading Analysis Terminal</div>
<form method="POST" action="/auth/login">
<div style="color:#94a3b8;font-size:13px;margin-bottom:8px">
Invitation code <span style="color:#475569">(only required for first-time access)</span></div>
<input name="code" placeholder="XXXX-XXXX-XXXX" maxlength="20"
 style="{_INPUT_STYLE};font-family:'JetBrains Mono',monospace;
 text-transform:uppercase;margin-bottom:16px">
<button type="submit" class="btn-google" style="width:100%;padding:12px;
 border:none;border-radius:6px;cursor:pointer;font-size:14px;font-weight:500;
 display:flex;align-items:center;justify-content:center">
{_GOOGLE_SVG}Sign in with Google</button>
</form>{msg_html}
</div></div>
</body></html>"""


class _AuthAndProxyMiddleware:
    """WSGI middleware for auth and proxy headers.

    Handles everything auth-related as plain HTTP — no Dash involvement.
    Unauthenticated users see a plain HTML login page. Authenticated
    users pass through to Dash.
    """

    def __init__(self, wsgi_app, flask_app):
        self.wsgi_app = wsgi_app
        self.flask_app = flask_app

    def __call__(self, environ, start_response):
        if environ.get("HTTP_X_FORWARDED_PROTO") == "https":
            environ["wsgi.url_scheme"] = "https"

        if SKIP_AUTH:
            return self.wsgi_app(environ, start_response)

        path = environ.get("PATH_INFO", "/")

        # Auth routes — always handled here
        if path.startswith("/auth/"):
            return self._handle_auth(environ, start_response, path)

        # Dash assets/API — always pass through
        if path.startswith(("/_dash", "/assets/")):
            return self.wsgi_app(environ, start_response)

        # Check authentication for all other paths
        with self.flask_app.request_context(environ):
            from flask import session
            if session.get("authenticated"):
                return self.wsgi_app(environ, start_response)

        # Not authenticated — show login page
        return self._serve_html(start_response, _login_page())

    def _serve_html(self, start_response, html):
        encoded = html.encode()
        start_response("200 OK", [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(encoded))),
        ])
        return [encoded]

    def _save_session_and_respond(self, environ, start_response, resp):
        from flask import session
        self.flask_app.session_interface.save_session(self.flask_app, session, resp)
        return resp(environ, start_response)

    def _handle_auth(self, environ, start_response, path):
        from werkzeug.wrappers import Request
        req = Request(environ)

        if path == "/auth/login":
            # POST from login form — store invitation code, redirect to Google
            scheme = environ.get("wsgi.url_scheme", "http")
            host = environ.get("HTTP_HOST", "localhost")
            callback_url = f"{scheme}://{host}/auth/callback"
            authorize_url, code_verifier = get_google_authorize_url(callback_url)

            with self.flask_app.request_context(environ):
                from flask import session, redirect as flask_redirect
                session["code_verifier"] = code_verifier
                # Store invitation code for use after Google auth
                invite_code = req.form.get("code", "").strip().upper()
                if invite_code:
                    session["invite_code"] = invite_code
                resp = flask_redirect(authorize_url)
                return self._save_session_and_respond(environ, start_response, resp)

        if path == "/auth/callback":
            with self.flask_app.request_context(environ):
                from flask import session, redirect as flask_redirect

                auth_code = req.args.get("code")
                code_verifier = session.pop("code_verifier", None)

                if not auth_code or not code_verifier:
                    logger.warning(f"OAuth callback missing: code={bool(auth_code)}, verifier={bool(code_verifier)}")
                    return self._serve_html(start_response,
                        _login_page("Sign-in failed. Please try again."))

                user = exchange_code_for_session(auth_code, code_verifier)
                if not user:
                    logger.warning("OAuth code exchange failed")
                    log_access_attempt("", "auth_failed", name="unknown")
                    return self._serve_html(start_response,
                        _login_page("Sign-in failed. Please try again."))

                invite_code = session.pop("invite_code", "")

                if is_user_authorized(user["id"]):
                    # Returning user — go straight in
                    db_user = get_user_with_role(user["id"])
                    if db_user:
                        user["role"] = db_user.get("role", "user")
                    session["authenticated"] = True
                    session["user"] = user
                    log_usage(user["email"], "login", user_name=user.get("name", ""))
                    resp = flask_redirect("/")
                    return self._save_session_and_respond(environ, start_response, resp)

                # New user — need a valid invitation code
                if not invite_code or not validate_invitation_code(invite_code, user_identity=user["email"]):
                    log_access_attempt(
                        user["email"], "invalid_code" if invite_code else "no_code",
                        name=user.get("name", ""), code_provided=invite_code)
                    return self._serve_html(start_response,
                        _login_page("You're not yet registered. "
                                    "Please enter a valid invitation code to get started."))

                # Register the new user
                consume_invitation_code(invite_code, user["email"])
                register_authorized_user(user["id"], user["email"],
                                         user.get("name", user["email"]))
                user["role"] = "user"  # new users default to user role
                log_usage(user["email"], "login", detail="first_login",
                          user_name=user.get("name", ""))
                session["authenticated"] = True
                session["user"] = user
                resp = flask_redirect("/")
                return self._save_session_and_respond(environ, start_response, resp)

        if path == "/auth/signout":
            with self.flask_app.request_context(environ):
                from flask import session, redirect as flask_redirect
                session.clear()
                resp = flask_redirect("/")
                return self._save_session_and_respond(environ, start_response, resp)

        # Unknown /auth/ path — pass through
        return self.wsgi_app(environ, start_response)


server.wsgi_app = _AuthAndProxyMiddleware(server.wsgi_app, server)


# ============================================================
# LAYOUT COMPONENTS
# ============================================================

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



# Login page is now plain HTML served by _AuthAndProxyMiddleware.
# No Dash components involved in the auth flow.


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
    """The authenticated app layout.

    Reports link visibility is controlled at request time by the
    toggle_reports_link callback — not here (no request context at build).
    """
    return html.Div([
        make_navbar(show_signout=not SKIP_AUTH),
        make_ticker_bar(),
        dbc.Container(id="main-content", fluid=True,
                      style={"padding": "20px 24px", "maxWidth": "1400px"}),
    ])


# Auth is handled entirely by _AuthAndProxyMiddleware at the WSGI layer.
# Unauthenticated users see a plain HTML login page (no Dash).
# Authenticated users reach this Dash layout.
app.layout = html.Div([
    dcc.Store(id="analysis-store"),
    dcc.Store(id="selected-strategy", data=-1),
    dcc.Store(id="view-mode", data="terminal"),
    dcc.Location(id="url", refresh=False),
    _make_app_shell(),
])


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

        # Log usage telemetry
        from flask import session as flask_session
        auth_user = flask_session.get("user", {})
        if auth_user:
            from dashboard.telemetry import log_usage
            log_usage(auth_user.get("email", ""), "analyze",
                      detail=ticker, user_name=auth_user.get("name", ""))

        status = f"✓ {ticker} analyzed in {result['elapsed']}s — {len(result['data'])} data points"
        return store_data, html.Span(status, style={"color": COLORS["accent_green"]})

    except Exception as e:
        logger.exception(f"Analysis failed for {ticker}")
        # Log analysis failure
        from flask import session as flask_session
        auth_user = flask_session.get("user", {})
        if auth_user:
            from dashboard.telemetry import log_usage
            log_usage(auth_user.get("email", ""), "analyze_error",
                      detail=ticker, user_name=auth_user.get("name", ""))
        return no_update, html.Span(f"Error: {e}", style={"color": COLORS["accent_red"]})


@callback(
    Output("main-content", "children"),
    Input("analysis-store", "data"),
    Input("selected-strategy", "data"),
    Input("view-mode", "data"),
)
def render_main(store_data, selected_strategy, view_mode):
    if view_mode == "reports":
        return build_reports_view()

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


def build_reports_view():
    """Admin reports page with tabbed views."""
    import dash_bootstrap_components as dbc
    from dashboard.reporting import (
        get_active_users, get_top_tickers,
        get_expressed_interest, get_login_frequency,
    )

    def make_report_table(data, columns=None):
        if data is None:
            return html.Div("Reports unavailable — no database connection",
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
            html.A("← Back to Terminal", id="back-to-terminal",
                   style={"color": COLORS["accent_cyan"], "cursor": "pointer",
                          "fontSize": "13px", "textDecoration": "none"}),
        ], style={"marginBottom": "16px"}),
        html.Div("REPORTS", className="panel-header"),
        html.Div(tabs, className="panel", style={"marginTop": "8px"}),
    ])


@callback(
    Output("reports-link", "style"),
    Input("url", "href"),
)
def toggle_reports_link(href):
    """Show Reports link for admin users, hide for others."""
    from flask import session
    user = session.get("user", {})
    role = user.get("role", "admin" if SKIP_AUTH else "user")
    if role == "admin":
        return {"cursor": "pointer", "display": "inline"}
    return {"cursor": "pointer", "display": "none"}


@callback(
    Output("view-mode", "data"),
    Input("reports-link", "n_clicks"),
    prevent_initial_call=True,
)
def show_reports(n_clicks):
    return "reports"


@callback(
    Output("view-mode", "data", allow_duplicate=True),
    Input("back-to-terminal", "n_clicks"),
    prevent_initial_call=True,
)
def back_to_terminal(n_clicks):
    return "terminal"


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
