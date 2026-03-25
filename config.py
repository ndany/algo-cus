"""
Central configuration for the trading algorithm project.

All tunable parameters live here so they're easy to find and change.
"""

from pathlib import Path

# --- Project Paths ---
PROJECT_ROOT = Path(__file__).parent
DATA_CACHE_DIR = PROJECT_ROOT / "data" / "cache"
OUTPUT_DIR = PROJECT_ROOT / "output"

# --- Ticker Universe ---
# Change this list to trade different assets.
DEFAULT_TICKERS = ["AMZN", "GOOG", "JPM", "MSFT"]

# --- Backtest Defaults ---
INITIAL_CAPITAL = 10_000.0
COMMISSION = 0.001       # 0.1% per trade
SLIPPAGE = 0.003         # 0.3% per trade (manual execution estimate)
POSITION_SIZE = 1.0      # Fraction of capital per trade

# --- Data Defaults ---
DEFAULT_DATA_PERIOD = "2y"       # yfinance period string
DEFAULT_DATA_INTERVAL = "1d"     # Daily bars

# --- FRED (Phase 5) ---
# Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html
# Set as environment variable: export FRED_API_KEY=your_key_here
FRED_SERIES = {
    "FEDFUNDS": "Federal Funds Rate",
    "T10Y2Y": "10Y-2Y Treasury Spread (Yield Curve)",
    "VIXCLS": "CBOE Volatility Index (VIX)",
    "UNRATE": "Unemployment Rate",
    "CPIAUCSL": "Consumer Price Index",
}
