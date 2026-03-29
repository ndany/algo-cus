"""
Moving Average Crossover Strategy

This is the "hello world" of trading algorithms. The idea:
- Compute a fast (short-term) and slow (long-term) moving average.
- When the fast MA crosses ABOVE the slow MA → BUY (uptrend starting).
- When the fast MA crosses BELOW the slow MA → SELL (downtrend starting).

Why it works (sometimes): Moving averages smooth out noise. A short-term
average reacts quickly to price changes, while a long-term average captures
the broader trend. A crossover suggests the trend direction is shifting.

Common parameter choices:
- 10/50 day (aggressive, more trades)
- 20/50 day (moderate)
- 50/200 day (conservative "golden cross / death cross")
"""

import pandas as pd

from strategies.base import Strategy
from strategies.registry import register


@register
class MovingAverageCrossover(Strategy):
    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        super().__init__(name=f"MA_Crossover({fast_period},{slow_period})")
        self.fast_period = fast_period
        self.slow_period = slow_period

    def get_params(self) -> dict:
        return {"fast_period": self.fast_period, "slow_period": self.slow_period}

    def set_params(self, **kwargs) -> None:
        if "fast_period" in kwargs:
            self.fast_period = kwargs["fast_period"]
        if "slow_period" in kwargs:
            self.slow_period = kwargs["slow_period"]
        self.name = f"MA_Crossover({self.fast_period},{self.slow_period})"

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()

        # Calculate moving averages
        df["MA_Fast"] = df["Close"].rolling(window=self.fast_period).mean()
        df["MA_Slow"] = df["Close"].rolling(window=self.slow_period).mean()

        # Generate signals based on crossover
        # We compare current and previous positions of fast vs slow MA
        df["Signal"] = 0
        df.loc[df["MA_Fast"] > df["MA_Slow"], "Signal"] = 1   # Fast above slow → bullish
        df.loc[df["MA_Fast"] <= df["MA_Slow"], "Signal"] = -1  # Fast below slow → bearish

        # We only want the *change* points (crossovers), not continuous signals
        # diff() gives us: 2 = crossed to buy, -2 = crossed to sell, 0 = no change
        df["Signal"] = df["Signal"].diff().apply(
            lambda x: 1 if x > 0 else (-1 if x < 0 else 0)
        )

        return df
