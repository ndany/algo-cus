"""Tests for data modules — sample_data and market_data."""

import pandas as pd
import pytest

from data.sample_data import generate_ohlcv
from data.market_data import MarketDataProvider, get_data


REQUIRED_COLUMNS = {"Date", "Open", "High", "Low", "Close", "Volume"}


class TestSyntheticData:
    def test_generates_correct_columns(self):
        df = generate_ohlcv(days=100)
        assert set(df.columns) == REQUIRED_COLUMNS

    def test_generates_correct_number_of_rows(self):
        df = generate_ohlcv(days=200)
        assert len(df) == 200

    def test_reproducible_with_seed(self):
        df1 = generate_ohlcv(days=50, seed=42)
        df2 = generate_ohlcv(days=50, seed=42)
        pd.testing.assert_frame_equal(df1, df2)

    def test_different_seeds_produce_different_data(self):
        df1 = generate_ohlcv(days=50, seed=42)
        df2 = generate_ohlcv(days=50, seed=99)
        assert not df1["Close"].equals(df2["Close"])

    def test_high_ge_low(self):
        df = generate_ohlcv(days=500)
        assert (df["High"] >= df["Low"]).all()

    def test_volume_positive(self):
        df = generate_ohlcv(days=100)
        assert (df["Volume"] > 0).all()

    def test_prices_positive(self):
        df = generate_ohlcv(days=100)
        for col in ["Open", "High", "Low", "Close"]:
            assert (df[col] > 0).all()


class TestGetData:
    def test_synthetic_returns_dataframe(self):
        df = get_data("synthetic", days=50)
        assert isinstance(df, pd.DataFrame)
        assert set(df.columns) == REQUIRED_COLUMNS
        assert len(df) == 50

    def test_synthetic_case_insensitive(self):
        df = get_data("Synthetic", days=30)
        assert len(df) == 30


class TestMarketDataProvider:
    def test_cache_dir_created(self, tmp_path):
        cache_dir = tmp_path / "cache"
        provider = MarketDataProvider(cache_dir=cache_dir)
        assert cache_dir.exists()

    @pytest.mark.integration
    def test_fetch_real_ticker(self, tmp_path):
        provider = MarketDataProvider(cache_dir=tmp_path / "cache")
        df = provider.fetch("MSFT", period="1mo")
        assert set(df.columns) >= REQUIRED_COLUMNS
        assert len(df) > 10
        assert (df["Close"] > 0).all()

    @pytest.mark.integration
    def test_caching(self, tmp_path):
        cache_dir = tmp_path / "cache"
        provider = MarketDataProvider(cache_dir=cache_dir)
        df1 = provider.fetch("MSFT", period="1mo")
        # Second call should use cache
        df2 = provider.fetch("MSFT", period="1mo")
        pd.testing.assert_frame_equal(df1, df2)
        # Verify cache file exists
        assert len(list(cache_dir.glob("*.parquet"))) == 1

    @pytest.mark.integration
    def test_fetch_multiple(self, tmp_path):
        provider = MarketDataProvider(cache_dir=tmp_path / "cache")
        results = provider.fetch_multiple(["MSFT", "GOOG"], period="1mo")
        assert "MSFT" in results
        assert "GOOG" in results
