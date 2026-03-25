"""Shared test fixtures."""

import sys
from pathlib import Path

import pytest
import pandas as pd

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.sample_data import generate_ohlcv


@pytest.fixture
def sample_data():
    """500 days of deterministic synthetic OHLCV data."""
    return generate_ohlcv(days=500, seed=42)


@pytest.fixture
def short_data():
    """100 days of synthetic data for faster tests."""
    return generate_ohlcv(days=100, seed=42)
