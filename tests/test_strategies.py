"""Tests for strategy classes."""

import pandas as pd
import pytest

from strategies.base import Strategy
from strategies.moving_average_crossover import MovingAverageCrossover
from strategies.rsi_strategy import RSIStrategy
from strategies.bollinger_bands import BollingerBandsStrategy


class TestMovingAverageCrossover:
    def test_generates_signal_column(self, sample_data):
        s = MovingAverageCrossover()
        df = s.generate_signals(sample_data)
        assert "Signal" in df.columns

    def test_signals_are_valid(self, sample_data):
        s = MovingAverageCrossover()
        df = s.generate_signals(sample_data)
        assert set(df["Signal"].unique()).issubset({-1, 0, 1})

    def test_get_params(self):
        s = MovingAverageCrossover(fast_period=10, slow_period=30)
        params = s.get_params()
        assert params == {"fast_period": 10, "slow_period": 30}

    def test_set_params(self):
        s = MovingAverageCrossover()
        s.set_params(fast_period=15, slow_period=60)
        assert s.fast_period == 15
        assert s.slow_period == 60
        assert "15" in s.name and "60" in s.name

    def test_does_not_modify_input(self, sample_data):
        original = sample_data.copy()
        s = MovingAverageCrossover()
        s.generate_signals(sample_data)
        pd.testing.assert_frame_equal(sample_data, original)


class TestRSIStrategy:
    def test_generates_signal_column(self, sample_data):
        s = RSIStrategy()
        df = s.generate_signals(sample_data)
        assert "Signal" in df.columns

    def test_signals_are_valid(self, sample_data):
        s = RSIStrategy()
        df = s.generate_signals(sample_data)
        assert set(df["Signal"].unique()).issubset({-1, 0, 1})

    def test_rsi_column_bounded(self, sample_data):
        s = RSIStrategy()
        df = s.generate_signals(sample_data)
        rsi = df["RSI"].dropna()
        assert (rsi >= 0).all() and (rsi <= 100).all()

    def test_get_params(self):
        s = RSIStrategy(period=10, oversold=25, overbought=75)
        params = s.get_params()
        assert params == {"period": 10, "oversold": 25, "overbought": 75}

    def test_set_params(self):
        s = RSIStrategy()
        s.set_params(period=21, oversold=20)
        assert s.period == 21
        assert s.oversold == 20


class TestBaseClassDefaults:
    """Tests for Strategy base class default method implementations."""

    def test_default_get_params_returns_empty(self):
        """Base class get_params() returns {} when not overridden."""
        class MinimalStrategy(Strategy):
            def generate_signals(self, data):
                return data
        s = MinimalStrategy(name="Minimal")
        assert s.get_params() == {}

    def test_default_set_params_is_noop(self):
        """Base class set_params() is a no-op when not overridden."""
        class MinimalStrategy(Strategy):
            def generate_signals(self, data):
                return data
        s = MinimalStrategy(name="Minimal")
        s.set_params(foo=42)  # should not raise
        assert s.name == "Minimal"

    def test_default_confidence_returns_one(self, sample_data):
        s = MovingAverageCrossover()
        assert s.confidence(sample_data, 0) == 1.0

    def test_repr(self):
        s = MovingAverageCrossover(fast_period=10, slow_period=30)
        assert repr(s) == "MA_Crossover(10,30)"

    def test_default_data_requirement(self):
        s = MovingAverageCrossover()
        assert s.data_requirement == "OHLCV_ONLY"

    def test_default_required_columns(self):
        s = RSIStrategy()
        assert s.required_columns == []


class TestStrategyCopy:
    """Tests for Strategy.copy() — immutable optimization (#31)."""

    def test_copy_returns_independent_instance(self):
        original = MovingAverageCrossover(fast_period=10, slow_period=30)
        clone = original.copy()
        assert clone is not original
        assert clone.get_params() == original.get_params()

    def test_copy_mutation_does_not_affect_original(self):
        original = MovingAverageCrossover(fast_period=10, slow_period=30)
        clone = original.copy()
        clone.set_params(fast_period=99, slow_period=200)
        assert original.fast_period == 10
        assert original.slow_period == 30

    def test_copy_all_strategy_types(self):
        strategies = [
            MovingAverageCrossover(fast_period=15, slow_period=45),
            RSIStrategy(period=21, oversold=25, overbought=75),
            BollingerBandsStrategy(period=30, num_std=1.5),
        ]
        for s in strategies:
            clone = s.copy()
            assert clone.get_params() == s.get_params()
            assert clone is not s

    def test_copy_produces_equivalent_signals(self, sample_data):
        original = RSIStrategy(period=14, oversold=30, overbought=70)
        clone = original.copy()
        original_signals = original.generate_signals(sample_data.copy())["Signal"]
        clone_signals = clone.generate_signals(sample_data.copy())["Signal"]
        pd.testing.assert_series_equal(original_signals, clone_signals)


class TestBollingerBands:
    def test_generates_signal_column(self, sample_data):
        s = BollingerBandsStrategy()
        df = s.generate_signals(sample_data)
        assert "Signal" in df.columns

    def test_signals_are_valid(self, sample_data):
        s = BollingerBandsStrategy()
        df = s.generate_signals(sample_data)
        assert set(df["Signal"].unique()).issubset({-1, 0, 1})

    def test_bands_exist(self, sample_data):
        s = BollingerBandsStrategy()
        df = s.generate_signals(sample_data)
        assert "BB_Upper" in df.columns
        assert "BB_Lower" in df.columns
        assert "BB_Middle" in df.columns

    def test_upper_above_lower(self, sample_data):
        s = BollingerBandsStrategy()
        df = s.generate_signals(sample_data).dropna()
        assert (df["BB_Upper"] >= df["BB_Lower"]).all()

    def test_get_params(self):
        s = BollingerBandsStrategy(period=30, num_std=2.5)
        params = s.get_params()
        assert params == {"period": 30, "num_std": 2.5}

    def test_set_params(self):
        s = BollingerBandsStrategy()
        s.set_params(period=30, num_std=1.5)
        assert s.period == 30
        assert s.num_std == 1.5
