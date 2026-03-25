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


class Backtest:
    def __init__(
        self,
        strategy: Strategy,
        initial_capital: float = 10_000.0,
        commission: float = 0.001,  # 0.1% per trade (typical for stocks)
        position_size: float = 1.0,  # fraction of capital to use per trade
    ):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission = commission
        self.position_size = position_size
        self.results: pd.DataFrame | None = None

    def run(self, data: pd.DataFrame) -> pd.DataFrame:
        """Execute the backtest on historical data.

        Simulates a simple long-only strategy:
        - Buy signal → buy shares with available capital
        - Sell signal → sell all shares
        """
        df = self.strategy.generate_signals(data)

        cash = self.initial_capital
        shares = 0.0
        portfolio_values = []
        trades = []

        for i, row in df.iterrows():
            price = row["Close"]
            signal = row.get("Signal", 0)

            if signal == 1 and cash > 0:
                # BUY: spend a fraction of cash on shares
                # Reserve enough for commission so we don't exceed cash
                available = cash * self.position_size
                invest_amount = available / (1 + self.commission)
                commission_cost = invest_amount * self.commission
                total_cost = invest_amount + commission_cost
                if total_cost <= cash:
                    shares = invest_amount / price
                    cash -= total_cost
                    trades.append(
                        {"Date": row["Date"], "Action": "BUY", "Price": price,
                         "Shares": shares, "Value": invest_amount}
                    )

            elif signal == -1 and shares > 0:
                # SELL: liquidate all shares
                proceeds = shares * price * (1 - self.commission)
                trades.append(
                    {"Date": row["Date"], "Action": "SELL", "Price": price,
                     "Shares": shares, "Value": proceeds}
                )
                cash += proceeds
                shares = 0.0

            # Track total portfolio value each day
            portfolio_value = cash + shares * price
            portfolio_values.append(portfolio_value)

        df["Portfolio_Value"] = portfolio_values
        df["Daily_Return"] = df["Portfolio_Value"].pct_change()

        self.results = df
        self.trades = pd.DataFrame(trades) if trades else pd.DataFrame()
        return df

    def get_metrics(self) -> dict:
        """Calculate key performance metrics.

        These are the standard metrics every quant looks at:
        - Total Return: overall profit/loss percentage
        - Sharpe Ratio: risk-adjusted return (higher is better, >1 is good)
        - Max Drawdown: worst peak-to-trough decline (how bad can it get?)
        - Win Rate: percentage of profitable trades
        """
        if self.results is None:
            raise ValueError("Run the backtest first with .run()")

        df = self.results
        total_return = (
            (df["Portfolio_Value"].iloc[-1] - self.initial_capital)
            / self.initial_capital
            * 100
        )

        # Sharpe Ratio: annualized (risk-free rate assumed 0 for simplicity)
        daily_returns = df["Daily_Return"].dropna()
        sharpe = 0.0
        if daily_returns.std() != 0:
            sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)

        # Max Drawdown: largest drop from a peak
        cumulative = df["Portfolio_Value"]
        rolling_max = cumulative.cummax()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100

        # Win rate from trades
        win_rate = 0.0
        num_trades = 0
        if not self.trades.empty:
            sells = self.trades[self.trades["Action"] == "SELL"]
            buys = self.trades[self.trades["Action"] == "BUY"]
            num_trades = len(sells)
            if num_trades > 0 and len(buys) >= num_trades:
                wins = sum(
                    sells.iloc[i]["Value"] > buys.iloc[i]["Value"]
                    for i in range(num_trades)
                )
                win_rate = wins / num_trades * 100

        return {
            "Strategy": self.strategy.name,
            "Total Return (%)": round(total_return, 2),
            "Sharpe Ratio": round(sharpe, 2),
            "Max Drawdown (%)": round(max_drawdown, 2),
            "Number of Trades": num_trades,
            "Win Rate (%)": round(win_rate, 2),
            "Final Value ($)": round(df["Portfolio_Value"].iloc[-1], 2),
        }

    def summary(self) -> str:
        """Print a human-readable performance summary."""
        metrics = self.get_metrics()
        lines = [f"\n{'='*50}", f"  Backtest Results: {metrics['Strategy']}", f"{'='*50}"]
        for key, value in metrics.items():
            if key != "Strategy":
                lines.append(f"  {key:<25} {value:>10}")
        lines.append(f"{'='*50}\n")
        return "\n".join(lines)
