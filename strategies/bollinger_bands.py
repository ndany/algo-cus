"""
Bollinger Bands Strategy

Bollinger Bands create a price "envelope" around a moving average:
- Middle Band = 20-day Simple Moving Average
- Upper Band  = Middle + 2 standard deviations
- Lower Band  = Middle - 2 standard deviations

Trading logic:
- Price touches Lower Band → BUY  (price is unusually low)
- Price touches Upper Band → SELL (price is unusually high)

The bands widen in volatile markets and narrow in calm ones. About 95% of
price action falls within 2 standard deviations, so touching a band
suggests an extreme move that may revert.

Like RSI, this is a mean-reversion strategy.
"""

import pandas as pd

from strategies.base import Strategy
from strategies.registry import register


@register
class BollingerBandsStrategy(Strategy):
    def __init__(self, period: int = 20, num_std: float = 2.0):
        super().__init__(name=f"Bollinger({period},{num_std})")
        self.period = period
        self.num_std = num_std

    def get_params(self) -> dict:
        return {"period": self.period, "num_std": self.num_std}

    def set_params(self, **kwargs) -> None:
        if "period" in kwargs:
            self.period = kwargs["period"]
        if "num_std" in kwargs:
            self.num_std = kwargs["num_std"]
        self.name = f"Bollinger({self.period},{self.num_std})"

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()

        df["BB_Middle"] = df["Close"].rolling(window=self.period).mean()
        rolling_std = df["Close"].rolling(window=self.period).std()
        df["BB_Upper"] = df["BB_Middle"] + (self.num_std * rolling_std)
        df["BB_Lower"] = df["BB_Middle"] - (self.num_std * rolling_std)

        df["Signal"] = 0
        df.loc[df["Close"] <= df["BB_Lower"], "Signal"] = 1   # At lower band → buy
        df.loc[df["Close"] >= df["BB_Upper"], "Signal"] = -1  # At upper band → sell

        df["Signal"] = df["Signal"].diff().apply(
            lambda x: 1 if x > 0 else (-1 if x < 0 else 0)
        )

        return df
