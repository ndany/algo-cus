"""
Dash callbacks — analyze, render, navigation, reports.

All callbacks are registered via the module-level `register_callbacks(app)`
function, called once from app.py after the app is created.
"""

import logging

import dash
from dash import html, Input, Output, State, no_update

from dashboard.theme import COLORS
from dashboard.analysis import run_analysis
from dashboard.serialization import serialize_analysis, deserialize_store
from dashboard.layouts import (
    make_empty_state, build_summary_view, build_strategy_detail,
    build_reports_view,
)

logger = logging.getLogger(__name__)


def register_callbacks(app, skip_auth: bool):
    """Register all Dash callbacks on the given app instance."""

    @app.callback(
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
            store_data = serialize_analysis(result)

            # Log usage telemetry
            if not skip_auth:
                from flask import session as flask_session
                auth_user = flask_session.get("user", {})
                if auth_user:
                    from dashboard.telemetry import log_usage
                    log_usage(auth_user.get("email", ""), "analyze",
                              detail=ticker, user_name=auth_user.get("name", ""))

            status = f"\u2713 {ticker} analyzed in {result['elapsed']}s \u2014 {len(result['data'])} data points"
            return store_data, html.Span(status, style={"color": COLORS["accent_green"]})

        except Exception as e:
            logger.exception(f"Analysis failed for {ticker}")
            if not skip_auth:
                from flask import session as flask_session
                auth_user = flask_session.get("user", {})
                if auth_user:
                    from dashboard.telemetry import log_usage
                    log_usage(auth_user.get("email", ""), "analyze_error",
                              detail=ticker, user_name=auth_user.get("name", ""))
            return no_update, html.Span(f"Error: {e}", style={"color": COLORS["accent_red"]})

    @app.callback(
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

        result = deserialize_store(store_data)

        if selected_strategy >= 0 and selected_strategy < len(result["strategies"]):
            return build_strategy_detail(result, selected_strategy)

        return build_summary_view(result)

    @app.callback(
        Output("reports-link", "style"),
        Input("url", "href"),
    )
    def toggle_reports_link(href):
        """Show Reports link for admin users, hide for others."""
        from flask import session
        user = session.get("user", {})
        role = user.get("role", "admin" if skip_auth else "user")
        if role == "admin":
            return {"cursor": "pointer", "display": "inline"}
        return {"cursor": "pointer", "display": "none"}

    @app.callback(
        Output("view-mode", "data"),
        Input("reports-link", "n_clicks"),
        prevent_initial_call=True,
    )
    def show_reports(n_clicks):
        return "reports"

    @app.callback(
        Output("view-mode", "data", allow_duplicate=True),
        Input("back-to-terminal", "n_clicks"),
        prevent_initial_call=True,
    )
    def back_to_terminal(n_clicks):
        return "terminal"

    @app.callback(
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

        if "strategy-card" in trigger:
            for i, clicks in enumerate(card_clicks or []):
                if clicks:
                    return i

        return no_update

    # Allow triggering analyze with Enter key
    @app.callback(
        Output("analyze-btn", "n_clicks"),
        Input("ticker-input", "n_submit"),
        State("analyze-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def submit_on_enter(n_submit, current_clicks):
        return (current_clicks or 0) + 1
