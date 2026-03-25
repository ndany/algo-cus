"""
Generate sample OHLCV (Open, High, Low, Close, Volume) market data.

In real trading, you'd fetch this from an API like Yahoo Finance, Alpha Vantage,
or your broker. Here we generate realistic synthetic data for learning.
"""

import numpy as np
import pandas as pd


def generate_ohlcv(
    days: int = 500,
    start_price: float = 100.0,
    volatility: float = 0.02,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic daily OHLCV data that mimics real stock behavior.

    The price follows a geometric Brownian motion model — the same model
    used in the Black-Scholes option pricing formula.

    Args:
        days: Number of trading days to generate.
        start_price: Starting price of the asset.
        volatility: Daily volatility (standard deviation of returns).
        seed: Random seed for reproducibility.

    Returns:
        DataFrame with columns: Date, Open, High, Low, Close, Volume
    """
    rng = np.random.default_rng(seed)

    # Generate daily returns from a normal distribution
    daily_returns = rng.normal(loc=0.0003, scale=volatility, size=days)

    # Build the close price series using cumulative returns
    close_prices = start_price * np.cumprod(1 + daily_returns)

    # Derive OHLV from close prices
    # In real markets, open ~ previous close, high/low are intraday extremes
    open_prices = np.roll(close_prices, 1)
    open_prices[0] = start_price

    high_prices = np.maximum(open_prices, close_prices) * (
        1 + rng.uniform(0, 0.015, days)
    )
    low_prices = np.minimum(open_prices, close_prices) * (
        1 - rng.uniform(0, 0.015, days)
    )

    # Volume tends to spike on big price moves
    base_volume = 1_000_000
    volume = (base_volume * (1 + 5 * np.abs(daily_returns))).astype(int)

    dates = pd.bdate_range(start="2024-01-02", periods=days)

    return pd.DataFrame(
        {
            "Date": dates,
            "Open": np.round(open_prices, 2),
            "High": np.round(high_prices, 2),
            "Low": np.round(low_prices, 2),
            "Close": np.round(close_prices, 2),
            "Volume": volume,
        }
    )
