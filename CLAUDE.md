# CLAUDE.md

## Project Overview

Educational trading algorithm project evolving into a full recommendation engine with real market data, walk-forward validation, ensemble strategies, and interactive visualization. See `docs/PLAN.md` for the full roadmap.

## Quick Reference

- **Language**: Python 3.11+
- **Branch**: develop on feature branches, PR to `main`
- **Tickers**: AMZN, GOOG, JPM, MSFT (configurable in `config.py`)
- **Config**: All tunable parameters live in `config.py`

## Running Tests

```bash
python -m pytest tests/ -m "not integration" -q    # Fast tests (no network)
python -m pytest tests/ -m integration -q           # yfinance/FRED integration tests
python -m pytest tests/ -q                           # All tests
```

Coverage reports are generated automatically to `output/coverage/` (HTML) and terminal.

## Running the Backtest

```bash
python examples/run_backtest.py                      # Synthetic data
python examples/run_backtest.py --ticker AMZN        # Single real ticker
python examples/run_backtest.py --ticker AMZN GOOG   # Multiple tickers
```

Charts are saved as interactive HTML files in `output/`.

## Architecture

- **DataFrame contract**: All data flows as DataFrames with columns `Date, Open, High, Low, Close, Volume`. Strategies add a `Signal` column (1=buy, -1=sell, 0=hold). Do not break this contract.
- **Strategy pattern**: All strategies extend `strategies/base.py:Strategy` and implement `generate_signals()`. They must also implement `get_params()`/`set_params()` for walk-forward optimization.
- **Backtest engine**: `backtest/engine.py` — the `calculate_metrics()` standalone function is reused by walk-forward; don't fold it back into the class.
- **Visualization**: All chart functions in `visualization/` return `plotly.graph_objects.Figure` objects. They're composable — usable in Jupyter, saved as HTML, or embedded in the Dash dashboard.

## Running the Dashboard

```bash
SKIP_AUTH=1 python dashboard/app.py        # Local dev (no auth)
gunicorn dashboard.app:server              # Production
```

The dashboard is a Dash app at `dashboard/app.py`. It uses:
- Supabase for auth (Google OAuth + invitation codes)
- On-demand yfinance data fetching
- Dark trader workstation theme (`dashboard/theme.py` + `dashboard/assets/style.css`)
- Progressive disclosure UX: summary → strategy detail drill-down

Environment variables for production:
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_KEY` — Supabase anon/public key
- `SKIP_AUTH` — Set to `1` to bypass auth in development
- `DASH_DEBUG` — Set to `1` for hot reload
- `PORT` — Server port (default 8050)

## Key Directories

```
config.py           Central configuration (tickers, slippage, commission, paths)
backtest/           Engine, walk-forward, bias guards
data/               Sample data generator, yfinance provider, FRED stub
strategies/         Base class + MA crossover, RSI, Bollinger Bands
visualization/      Plotly chart modules (standalone, composable)
dashboard/          Dash web app (dark theme, auth, deployment)
tests/              pytest suite (88% coverage target)
docs/               Plan, deployment guide, getting started, session notes
output/             Gitignored — HTML charts, coverage reports, paper trade logs
```

## Conventions

- Tests use synthetic data by default (fast, deterministic, seed=42)
- Integration tests hitting external APIs are marked `@pytest.mark.integration`
- Slippage defaults to 0.3% (manual execution estimate), configurable in `config.py`
- Cache files go in `data/cache/` (gitignored, parquet format)
- Supabase for auth and invitation codes; no other database
- Dashboard chart builders live in `dashboard/app.py` and use `dashboard/theme.py` for dark styling
- All `visualization/*.py` charts remain standalone (return `go.Figure`) — the dashboard composes them
