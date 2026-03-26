# AlgoStation — Trading Algorithm Analysis Platform

A trading analysis platform that backtests strategies against real market data, validates them with walk-forward analysis, and presents results through an interactive dark-mode dashboard.

## Quick Start

```bash
# Setup
git clone https://github.com/ndany/algo-cus.git
cd algo-cus
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Launch the dashboard
SKIP_AUTH=1 python dashboard/app.py
# Open http://localhost:8050
```

Enter a ticker (e.g., `AMZN`) and click **ANALYZE** to run all strategies.

## What It Does

1. **Fetches real market data** from Yahoo Finance (AMZN, GOOG, JPM, MSFT or any ticker)
2. **Backtests three strategies** — Moving Average Crossover, RSI, Bollinger Bands
3. **Validates with walk-forward analysis** — train/test splits that prevent overfitting
4. **Compares against benchmarks** — buy-and-hold and random baselines
5. **Visualizes everything** in an interactive dark-mode trader workstation

## Dashboard

Progressive disclosure UX: summary overview → click a strategy → detailed analysis.

- Candlestick charts with volume
- Buy/sell signal overlays
- Portfolio value comparison across strategies
- Walk-forward in-sample vs out-of-sample with degradation ratio
- Drawdown visualization

## CLI Alternative

```bash
python examples/run_backtest.py                      # Synthetic data
python examples/run_backtest.py --ticker AMZN        # Single ticker
python examples/run_backtest.py --ticker AMZN GOOG   # Multiple tickers
```

Generates interactive HTML charts in `output/`.

## Project Structure

```
config.py              Tickers, slippage (0.3%), commission (0.1%), paths
backtest/              Engine, walk-forward validation, bias guards
data/                  yfinance provider with caching, synthetic generator
strategies/            MA Crossover, RSI, Bollinger Bands (extensible base class)
visualization/         Standalone plotly chart modules
dashboard/             Dash web app (dark theme, Supabase auth)
tests/                 75 tests, 88% coverage
docs/                  Plan, deployment guide, getting started, session notes
```

## Testing

```bash
python -m pytest tests/ -m "not integration" -q    # Unit tests (no network)
python -m pytest tests/ -m integration -q           # Integration tests
```

## Deployment

Deployed on Render with Supabase for Google OAuth + invitation codes. See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the full scaling roadmap.

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) | Hands-on setup and validation guide with checklists |
| [`docs/PLAN.md`](docs/PLAN.md) | Implementation roadmap (phases, dependencies, status) |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Progressive deployment scaling (free → $40/month) |
| [`docs/SESSION_SUMMARY.md`](docs/SESSION_SUMMARY.md) | Design decisions, rationale, and project history |

## Tech Stack

Python 3.11+ · Pandas · Plotly · Dash · yfinance · Supabase · Gunicorn · pytest
