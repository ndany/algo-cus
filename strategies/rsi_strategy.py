"""
RSI (Relative Strength Index) Strategy

RSI measures how "overbought" or "oversold" an asset is on a scale of 0-100.

The logic:
- RSI < 30 → Oversold → BUY (price dropped too fast, likely to bounce)
- RSI > 70 → Overbought → SELL (price rose too fast, likely to pull back)

RSI Formula:
  RSI = 100 - (100 / (1 + RS))
  RS  = Average Gain over N periods / Average Loss over N periods

This is a "mean reversion" strategy — it bets that extreme moves will reverse.
It works best in range-bound (sideways) markets, and poorly in strong trends.
"""

import pandas as pd
import numpy as np

from strategies.base import Strategy
from strategies.registry import register


@register
class RSIStrategy(Strategy):
    def __init__(
        self,
        period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
    ):
        super().__init__(name=f"RSI({period})")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def get_params(self) -> dict:
        return {
            "period": self.period,
            "oversold": self.oversold,
            "overbought": self.overbought,
        }

    def set_params(self, **kwargs) -> None:
        if "period" in kwargs:
            self.period = kwargs["period"]
        if "oversold" in kwargs:
            self.oversold = kwargs["oversold"]
        if "overbought" in kwargs:
            self.overbought = kwargs["overbought"]
        self.name = f"RSI({self.period})"

    def _calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """Compute RSI using the standard Wilder smoothing method."""
        delta = prices.diff()

        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        # Use exponential moving average (Wilder's smoothing)
        avg_gain = gain.ewm(alpha=1 / self.period, min_periods=self.period).mean()
        avg_loss = loss.ewm(alpha=1 / self.period, min_periods=self.period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["RSI"] = self._calculate_rsi(df["Close"])

        df["Signal"] = 0
        df.loc[df["RSI"] < self.oversold, "Signal"] = 1    # Oversold → buy
        df.loc[df["RSI"] > self.overbought, "Signal"] = -1  # Overbought → sell

        # Only signal on the first bar that crosses the threshold
        df["Signal"] = df["Signal"].diff().apply(
            lambda x: 1 if x > 0 else (-1 if x < 0 else 0)
        )

        return df
