# Trading Algorithm Basics

A learning project for building trading algorithms from scratch in Python.

## Structure

```
strategies/          - Trading strategy implementations
backtest/            - Backtesting engine
data/                - Sample market data and data utilities
examples/            - Runnable examples
```

## Getting Started

```bash
pip install -r requirements.txt
python examples/run_backtest.py
```

## Key Concepts Covered

1. **Market Data Handling** - Loading and processing OHLCV price data
2. **Technical Indicators** - Moving averages, RSI, Bollinger Bands
3. **Strategy Design** - Signal generation with entry/exit rules
4. **Backtesting** - Simulating strategy performance on historical data
5. **Risk Management** - Position sizing and stop losses
6. **Performance Metrics** - Sharpe ratio, max drawdown, win rate
