"""
AlgoStation — Trading Algorithm Dashboard

App initialization, middleware wiring, layout shell, and entry point.
"""

import os
import logging

from dotenv import load_dotenv
load_dotenv()

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

from dashboard.layouts import make_navbar, make_ticker_bar
from dashboard.callbacks import register_callbacks
from dashboard.middleware import AuthAndProxyMiddleware

logger = logging.getLogger(__name__)

# --- App Initialization ---
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True,
    title="AlgoStation",
    update_title="Analyzing...",
)
server = app.server

# --- Auth Setup ---
SKIP_AUTH = os.environ.get("SKIP_AUTH", "1") == "1"

auth_funcs = {}
if not SKIP_AUTH:
    from dashboard.auth import (
        get_google_authorize_url, exchange_code_for_session,
        validate_invitation_code, consume_invitation_code,
        register_authorized_user, is_user_authorized,
        get_user_with_role,
    )
    from dashboard.telemetry import log_usage, log_access_attempt
    server.secret_key = os.environ.get(
        "FLASK_SECRET_KEY", os.environ.get("SUPABASE_KEY", "change-me")
    )
    auth_funcs = {
        "get_google_authorize_url": get_google_authorize_url,
        "exchange_code_for_session": exchange_code_for_session,
        "validate_invitation_code": validate_invitation_code,
        "consume_invitation_code": consume_invitation_code,
        "register_authorized_user": register_authorized_user,
        "is_user_authorized": is_user_authorized,
        "get_user_with_role": get_user_with_role,
        "log_usage": log_usage,
        "log_access_attempt": log_access_attempt,
    }

server.wsgi_app = AuthAndProxyMiddleware(
    server.wsgi_app, server, skip_auth=SKIP_AUTH, auth_funcs=auth_funcs,
)

# --- App Layout ---
app.layout = html.Div([
    dcc.Store(id="analysis-store"),
    dcc.Store(id="selected-strategy", data=-1),
    dcc.Store(id="view-mode", data="terminal"),
    dcc.Location(id="url", refresh=False),
    html.Div([
        make_navbar(show_signout=not SKIP_AUTH),
        make_ticker_bar(),
        dbc.Container(id="main-content", fluid=True,
                      style={"padding": "20px 24px", "maxWidth": "1400px"}),
    ]),
])

# --- Register Callbacks ---
register_callbacks(app, skip_auth=SKIP_AUTH)

# --- Entry Point ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    debug = os.environ.get("DASH_DEBUG", "1") == "1"
    app.run(debug=debug, host="0.0.0.0", port=port)
