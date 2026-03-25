"""
Backtesting Engine

A backtester simulates how a strategy would have performed on historical data.
It's the most important tool for evaluating a trading algorithm before risking
real money.

How it works:
1. Feed historical OHLCV data through a strategy to get buy/sell signals.
2. Simulate executing those trades with a starting cash balance.
3. Track the portfolio value over time.
4. Calculate performance metrics (return, Sharpe ratio, max drawdown, etc.).

Important limitations of backtesting:
- Past performance does NOT guarantee future results.
- Backtests can be "overfit" — tuned to work perfectly on historical data
  but fail on new data. Always test on out-of-sample data.
- Real trading has slippage, commissions, and market impact not fully
  captured here.
"""

import pandas as pd
import numpy as np

from strategies.base import Strategy
from config import COMMISSION, SLIPPAGE, INITIAL_CAPITAL, POSITION_SIZE


def calculate_metrics(
    portfolio_values: pd.Series,
    trades: pd.DataFrame,
    initial_capital: float,
    strategy_name: str = "Strategy",
) -> dict:
    """Calculate standard performance metrics from backtest results.

    This is a standalone function so it can be reused by the walk-forward
    engine without instantiating a full Backtest object.

    Args:
        portfolio_values: Series of daily portfolio values.
        trades: DataFrame of executed trades (Action, Price, Shares, Value).
        initial_capital: Starting capital.
        strategy_name: Name for the metrics dict.

    Returns:
        Dict of performance metrics.
    """
    total_return = (
        (portfolio_values.iloc[-1] - initial_capital) / initial_capital * 100
    )

    daily_returns = portfolio_values.pct_change().dropna()
    sharpe = 0.0
    if daily_returns.std() != 0:
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)

    cummax = portfolio_values.cummax()
    drawdown = (portfolio_values - cummax) / cummax
    max_drawdown = drawdown.min() * 100

    win_rate = 0.0
    num_trades = 0
    if not trades.empty:
        sells = trades[trades["Action"] == "SELL"]
        buys = trades[trades["Action"] == "BUY"]
        num_trades = len(sells)
        if num_trades > 0 and len(buys) >= num_trades:
            wins = sum(
                sells.iloc[i]["Value"] > buys.iloc[i]["Value"]
                for i in range(num_trades)
            )
            win_rate = wins / num_trades * 100

    return {
        "Strategy": strategy_name,
        "Total Return (%)": round(total_return, 2),
        "Sharpe Ratio": round(sharpe, 2),
        "Max Drawdown (%)": round(max_drawdown, 2),
        "Number of Trades": num_trades,
        "Win Rate (%)": round(win_rate, 2),
        "Final Value ($)": round(portfolio_values.iloc[-1], 2),
    }


class Backtest:
    def __init__(
        self,
        strategy: Strategy,
        initial_capital: float = INITIAL_CAPITAL,
        commission: float = COMMISSION,
        slippage: float = SLIPPAGE,
        position_size: float = POSITION_SIZE,
    ):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.position_size = position_size
        self.results: pd.DataFrame | None = None
        self.trades: pd.DataFrame = pd.DataFrame()

    def run(
        self,
        data: pd.DataFrame,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Execute the backtest on historical data.

        Simulates a simple long-only strategy:
        - Buy signal -> buy shares with available capital
        - Sell signal -> sell all shares

        Args:
            data: OHLCV DataFrame.
            start_date: Optional start date filter (inclusive).
            end_date: Optional end date filter (inclusive).
        """
        df = data.copy()

        # Apply date slicing if requested
        if start_date is not None:
            df = df[df["Date"] >= pd.Timestamp(start_date)]
        if end_date is not None:
            df = df[df["Date"] <= pd.Timestamp(end_date)]
        df = df.reset_index(drop=True)

        df = self.strategy.generate_signals(df)

        cash = self.initial_capital
        shares = 0.0
        portfolio_values = []
        trades = []

        # Combined friction: commission + slippage
        buy_friction = self.commission + self.slippage
        sell_friction = self.commission + self.slippage

        for i, row in df.iterrows():
            price = row["Close"]
            signal = row.get("Signal", 0)

            if signal == 1 and cash > 0:
                available = cash * self.position_size
                invest_amount = available / (1 + buy_friction)
                friction_cost = invest_amount * buy_friction
                total_cost = invest_amount + friction_cost
                if total_cost <= cash:
                    shares = invest_amount / price
                    cash -= total_cost
                    trades.append(
                        {"Date": row["Date"], "Action": "BUY", "Price": price,
                         "Shares": shares, "Value": invest_amount}
                    )

            elif signal == -1 and shares > 0:
                proceeds = shares * price * (1 - sell_friction)
                trades.append(
                    {"Date": row["Date"], "Action": "SELL", "Price": price,
                     "Shares": shares, "Value": proceeds}
                )
                cash += proceeds
                shares = 0.0

            portfolio_value = cash + shares * price
            portfolio_values.append(portfolio_value)

        df["Portfolio_Value"] = portfolio_values
        df["Daily_Return"] = df["Portfolio_Value"].pct_change()

        self.results = df
        self.trades = pd.DataFrame(trades) if trades else pd.DataFrame()
        return df

    def get_metrics(self) -> dict:
        """Calculate key performance metrics."""
        if self.results is None:
            raise ValueError("Run the backtest first with .run()")

        return calculate_metrics(
            portfolio_values=self.results["Portfolio_Value"],
            trades=self.trades,
            initial_capital=self.initial_capital,
            strategy_name=self.strategy.name,
        )

    def summary(self) -> str:
        """Print a human-readable performance summary."""
        metrics = self.get_metrics()
        lines = [f"\n{'='*50}", f"  Backtest Results: {metrics['Strategy']}", f"{'='*50}"]
        for key, value in metrics.items():
            if key != "Strategy":
                lines.append(f"  {key:<25} {value:>10}")
        lines.append(f"{'='*50}\n")
        return "\n".join(lines)
