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

    @property
    def data_requirement(self) -> str:
        """What data this strategy needs. Default: OHLCV_ONLY (backward compatible)."""
        return "OHLCV_ONLY"

    @property
    def required_columns(self) -> list[str]:
        """Extra columns (beyond OHLCV) this strategy requires. Default: none."""
        return []

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

    def get_params(self) -> dict:
        """Return current strategy parameters as a dict.

        Override in subclasses to expose tunable parameters
        for walk-forward optimization.
        """
        return {}

    def set_params(self, **kwargs) -> None:
        """Update strategy parameters.

        Override in subclasses. The name is automatically updated
        to reflect new parameter values.
        """
        pass

    def copy(self) -> "Strategy":
        """Return an independent copy with the same parameters.

        Used by walk-forward and bias guards so grid search operates
        on throwaway copies instead of mutating the shared instance.
        """
        clone = self.__class__.__new__(self.__class__)
        clone.__init__(**self.get_params())
        return clone

    def confidence(self, data: pd.DataFrame, row_index: int) -> float:
        """Return signal confidence at a given row (0.0 to 1.0).

        Override in subclasses to provide signal-strength information
        for ensemble weighting and recommendation confidence.
        Default returns 1.0 (fully confident).
        """
        return 1.0

    def __repr__(self) -> str:
        return f"{self.name}"
