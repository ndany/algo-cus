# CLAUDE.md

## Project Overview

Educational trading algorithm project evolving into a full recommendation engine with real market data, walk-forward validation, ensemble strategies, and interactive visualization. See `PLAN.md` for the full 6-phase roadmap.

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

## Key Directories

```
config.py           Central configuration (tickers, slippage, commission, paths)
backtest/           Engine, walk-forward, bias guards
data/               Sample data generator, yfinance provider, FRED stub
strategies/         Base class + MA crossover, RSI, Bollinger Bands
visualization/      Plotly chart modules
tests/              pytest suite (88% coverage target)
output/             Gitignored — HTML charts, coverage reports, paper trade logs
```

## Conventions

- Tests use synthetic data by default (fast, deterministic, seed=42)
- Integration tests hitting external APIs are marked `@pytest.mark.integration`
- Slippage defaults to 0.3% (manual execution estimate), configurable in `config.py`
- Cache files go in `data/cache/` (gitignored, parquet format)
- No database — JSON persistence for paper trading logs
