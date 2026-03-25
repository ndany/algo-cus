"""
Base strategy class — the foundation for all trading strategies.

Every strategy follows the same pattern:
1. Receive market data (OHLCV)
2. Calculate indicators (moving averages, RSI, etc.)
3. Generate signals (buy=1, sell=-1, hold=0)

This base class defines that interface so the backtester can work
with any strategy interchangeably.
"""

from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    """Abstract base class for trading strategies."""

    def __init__(self, name: str = "BaseStrategy"):
        self.name = name

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Analyze market data and produce trading signals.

        Args:
            data: DataFrame with OHLCV columns.

        Returns:
            The same DataFrame with an added 'Signal' column:
              1  = Buy signal
             -1  = Sell signal
              0  = Hold / no action
        """

    def __repr__(self) -> str:
        return f"{self.name}"
