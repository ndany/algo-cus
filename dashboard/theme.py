"""
Dark trader workstation theme.

Color palette and Plotly template for the trading dashboard.
"""

import plotly.graph_objects as go
import plotly.io as pio

# --- Color Palette ---
COLORS = {
    "bg_primary": "#0a0e17",         # Deep dark navy — main background
    "bg_secondary": "#111827",        # Slightly lighter — cards, panels
    "bg_tertiary": "#1a2332",         # Borders, hover states
    "text_primary": "#e2e8f0",        # Off-white text
    "text_secondary": "#8892a4",      # Muted text
    "text_muted": "#4a5568",          # Very subtle text
    "accent_cyan": "#00d4ff",         # Primary accent — highlights, links
    "accent_green": "#00ff88",        # Buy signals, positive values
    "accent_red": "#ff4757",          # Sell signals, negative values
    "accent_orange": "#ff9800",       # Warnings, out-of-sample
    "accent_purple": "#a855f7",       # Tertiary accent
    "grid": "#1e293b",               # Chart gridlines
    "border": "#1e293b",             # Panel borders
}

# Strategy-specific colors (consistent across all charts)
STRATEGY_COLORS = {
    "MA_Crossover": "#00d4ff",
    "RSI": "#ff9800",
    "Bollinger": "#a855f7",
    "Buy & Hold": "#4a5568",
}

# Sequential palette for generic multi-series charts
SERIES_COLORS = [
    "#00d4ff", "#ff9800", "#a855f7", "#00ff88", "#ff4757", "#ffeb3b",
]

# --- Plotly Template ---
PLOTLY_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor=COLORS["bg_secondary"],
        plot_bgcolor=COLORS["bg_primary"],
        font=dict(
            family="JetBrains Mono, Fira Code, Consolas, monospace",
            color=COLORS["text_primary"],
            size=12,
        ),
        title=dict(
            font=dict(size=16, color=COLORS["text_primary"]),
            x=0.01,
        ),
        xaxis=dict(
            gridcolor=COLORS["grid"],
            zerolinecolor=COLORS["grid"],
            tickfont=dict(color=COLORS["text_secondary"]),
        ),
        yaxis=dict(
            gridcolor=COLORS["grid"],
            zerolinecolor=COLORS["grid"],
            tickfont=dict(color=COLORS["text_secondary"]),
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=COLORS["text_secondary"]),
        ),
        colorway=SERIES_COLORS,
        margin=dict(l=50, r=30, t=50, b=30),
    ),
)

# Register as a named template
pio.templates["trader_dark"] = PLOTLY_TEMPLATE


def apply_dark_theme(fig: go.Figure) -> go.Figure:
    """Apply the trader dark theme to any plotly figure."""
    fig.update_layout(template="trader_dark")
    return fig


# --- Dash / CSS Styling ---
# Card style for dashboard panels
CARD_STYLE = {
    "backgroundColor": COLORS["bg_secondary"],
    "border": f"1px solid {COLORS['border']}",
    "borderRadius": "8px",
    "padding": "20px",
    "marginBottom": "16px",
}

CARD_HEADER_STYLE = {
    "color": COLORS["text_primary"],
    "fontSize": "14px",
    "fontWeight": "600",
    "textTransform": "uppercase",
    "letterSpacing": "1px",
    "marginBottom": "12px",
}

METRIC_VALUE_STYLE = {
    "color": COLORS["accent_cyan"],
    "fontSize": "28px",
    "fontWeight": "700",
    "fontFamily": "JetBrains Mono, monospace",
}

METRIC_LABEL_STYLE = {
    "color": COLORS["text_secondary"],
    "fontSize": "11px",
    "textTransform": "uppercase",
    "letterSpacing": "1px",
}
