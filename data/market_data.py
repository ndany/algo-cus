"""
Real market data provider using yfinance.

Fetches OHLCV data from Yahoo Finance with local parquet caching
to avoid rate limits and enable offline development.
"""

import hashlib
import logging
from pathlib import Path

import pandas as pd
import yfinance as yf

from config import DATA_CACHE_DIR, DEFAULT_DATA_INTERVAL, DEFAULT_DATA_PERIOD

logger = logging.getLogger(__name__)


class MarketDataProvider:
    """Fetches and caches real market data from Yahoo Finance."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or DATA_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, ticker: str, start: str | None, end: str | None,
                   period: str | None, interval: str) -> str:
        raw = f"{ticker}|{start}|{end}|{period}|{interval}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _cache_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.parquet"

    def fetch(
        self,
        ticker: str,
        start: str | None = None,
        end: str | None = None,
        period: str | None = None,
        interval: str = DEFAULT_DATA_INTERVAL,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """Fetch OHLCV data for a single ticker.

        Uses either (start, end) date strings or a period string like "2y".
        If neither is provided, defaults to DEFAULT_DATA_PERIOD.

        Returns DataFrame with columns: Date, Open, High, Low, Close, Volume
        (matching the synthetic data contract).
        """
        if start is None and period is None:
            period = DEFAULT_DATA_PERIOD

        key = self._cache_key(ticker, start, end, period, interval)
        cache_file = self._cache_path(key)

        if use_cache and cache_file.exists():
            logger.info(f"Loading {ticker} from cache")
            df = pd.read_parquet(cache_file)
            return df

        logger.info(f"Downloading {ticker} from Yahoo Finance")
        yticker = yf.Ticker(ticker)
        raw = yticker.history(
            start=start,
            end=end,
            period=period,
            interval=interval,
            auto_adjust=True,
        )

        if raw.empty:
            raise ValueError(
                f"No data returned for {ticker}. Check the ticker symbol and date range."
            )

        df = self._normalize(raw, ticker)
        self._validate(df, ticker)

        if use_cache:
            df.to_parquet(cache_file, index=False)
            logger.info(f"Cached {ticker} to {cache_file}")

        return df

    def fetch_multiple(
        self,
        tickers: list[str],
        **kwargs,
    ) -> dict[str, pd.DataFrame]:
        """Fetch data for multiple tickers. Returns {ticker: DataFrame}."""
        results = {}
        for ticker in tickers:
            try:
                results[ticker] = self.fetch(ticker, **kwargs)
            except ValueError as e:
                logger.warning(f"Skipping {ticker}: {e}")
        return results

    def _normalize(self, raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Convert yfinance output to match our standard DataFrame contract."""
        df = raw.reset_index()

        # yfinance returns 'Date' or 'Datetime' depending on interval
        date_col = "Datetime" if "Datetime" in df.columns else "Date"
        df = df.rename(columns={date_col: "Date"})

        # Strip timezone info for consistency with synthetic data
        if pd.api.types.is_datetime64_any_dtype(df["Date"]):
            df["Date"] = df["Date"].dt.tz_localize(None)

        # Keep only the standard columns
        standard_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
        df = df[[c for c in standard_cols if c in df.columns]]

        # Round prices to 2 decimal places
        for col in ["Open", "High", "Low", "Close"]:
            if col in df.columns:
                df[col] = df[col].round(2)

        df["Volume"] = df["Volume"].astype(int)
        df = df.sort_values("Date").reset_index(drop=True)

        return df

    def _validate(self, df: pd.DataFrame, ticker: str) -> None:
        """Check for common data quality issues."""
        required = {"Date", "Open", "High", "Low", "Close", "Volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"{ticker}: missing columns {missing}")

        nan_counts = df[["Open", "High", "Low", "Close"]].isna().sum()
        total_nans = nan_counts.sum()
        if total_nans > 0:
            logger.warning(f"{ticker}: {total_nans} NaN values in price data, forward-filling")
            df[["Open", "High", "Low", "Close"]] = (
                df[["Open", "High", "Low", "Close"]].ffill()
            )

        if len(df) < 20:
            raise ValueError(f"{ticker}: only {len(df)} rows returned, need at least 20")


def get_data(
    ticker_or_synthetic: str = "synthetic",
    **kwargs,
) -> pd.DataFrame:
    """Convenience function: fetch real data by ticker or generate synthetic.

    Args:
        ticker_or_synthetic: A ticker symbol (e.g., "AMZN") or "synthetic".
        **kwargs: Passed to MarketDataProvider.fetch() or generate_ohlcv().
    """
    if ticker_or_synthetic.lower() == "synthetic":
        from data.sample_data import generate_ohlcv
        return generate_ohlcv(**kwargs)

    provider = MarketDataProvider()
    return provider.fetch(ticker_or_synthetic, **kwargs)
