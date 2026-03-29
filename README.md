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
SKIP_AUTH=1 python -m dashboard.app
# Open http://localhost:8050
```

Enter a ticker (e.g., `AMZN`) and click **ANALYZE** to run all strategies.

## What It Does

1. **Fetches real market data** from Yahoo Finance (AMZN, GOOG, JPM, MSFT or any ticker)
2. **Backtests three strategies** — Moving Average Crossover, RSI, Bollinger Bands
3. **Validates with walk-forward analysis** — train/test splits that prevent overfitting
4. **Compares against benchmarks** — buy-and-hold and random baselines
5. **Visualizes everything** in an interactive dark-mode trader workstation
6. **Tracks usage telemetry** — admin reports (dashboard + CLI) for active users, top tickers, expressed interest, and login frequency

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

### Usage Reports (CLI)

```bash
python scripts/report.py              # All reports
python scripts/report.py active-users # Active users (7 days)
python scripts/report.py tickers      # Most analyzed tickers
python scripts/report.py interest     # Expressed interest (unregistered attempts)
python scripts/report.py logins       # Login frequency
```

Requires `SUPABASE_URL` and `SUPABASE_KEY` env vars (or a `.env` file). See [`docs/TELEMETRY.md`](docs/TELEMETRY.md) for telemetry details.

## Project Structure

```
config.py              Tickers, slippage (0.3%), commission (0.1%), paths
backtest/              Engine, walk-forward validation, bias guards
data/                  yfinance provider with caching, synthetic generator
strategies/            MA Crossover, RSI, Bollinger Bands (extensible base class)
visualization/         Standalone plotly chart modules
dashboard/             Dash web app (dark theme, Supabase auth, admin reports)
scripts/               CLI tools (report.py for usage telemetry)
sql/                   Supabase SQL migrations (auth tables, telemetry, roles, reporting functions)
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
| [`docs/TELEMETRY.md`](docs/TELEMETRY.md) | Usage telemetry architecture, tables, and reporting |

## Tech Stack

Python 3.11+ · Pandas · Plotly · Dash · yfinance · Supabase · Gunicorn · pytest
