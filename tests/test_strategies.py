"""Tests for strategy classes."""

import pandas as pd
import pytest

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
