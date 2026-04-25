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
- **Strategy pattern**: All strategies extend `strategies/base.py:Strategy` and implement `generate_signals()`. They must also implement `get_params()`/`set_params()` for walk-forward optimization. Strategies use `@register` from `strategies/registry.py` for auto-discovery, declare `data_requirement`/`required_columns` for filtering, and `copy()` for immutable optimization.
- **Backtest engine**: `backtest/engine.py` — the `calculate_metrics()` standalone function is reused by walk-forward; don't fold it back into the class.
- **Visualization**: All chart functions in `visualization/` return `plotly.graph_objects.Figure` objects. They're composable — usable in Jupyter, saved as HTML, or embedded in the Dash dashboard.
- **Telemetry**: `dashboard/telemetry.py` provides fire-and-forget logging to `usage_log` (login, analyze, analyze_error) and `access_attempts` (no_code, invalid_code, auth_failed) tables. All calls swallow errors — telemetry never blocks users.
- **Reporting**: `dashboard/reporting.py` provides shared query functions (active users, top tickers, expressed interest, login frequency) backed by Supabase RPC functions. Used by both the dashboard Reports page and `scripts/report.py`.

## Running the Dashboard

```bash
SKIP_AUTH=1 python -m dashboard.app        # Local dev (no auth)
gunicorn dashboard.app:server              # Production
```

The dashboard is a Dash app with modular architecture:
- `dashboard/app.py` — app init, layout shell, entry point (85 lines)
- `dashboard/middleware.py` — WSGI auth middleware (`AuthAndProxyMiddleware`)
- `dashboard/charts.py` — dark-themed chart builders (compose `visualization/*.py` + `apply_dark_theme()`)
- `dashboard/layouts.py` — summary view, detail view, empty state, metric tiles, reports view
- `dashboard/callbacks.py` — analyze, render, navigation callbacks
- `dashboard/serialization.py` — JSON round-trip for `dcc.Store` (WFProxy, serialize/deserialize)
- Supabase for auth (Google OAuth + invitation codes)
- On-demand yfinance data fetching
- Dark trader workstation theme (`dashboard/theme.py` + `dashboard/assets/style.css`)
- Progressive disclosure UX: summary → strategy detail drill-down
- Admin-only Reports page (tabbed: Active Users, Top Tickers, Expressed Interest, Login Frequency)

Auth flow: Google sign-in is always required. Invitation codes are only needed for first-time users — returning authorized users skip the code check. Auth is handled entirely at the WSGI middleware layer; unauthenticated users see plain HTML (no Dash involvement). User roles (`admin`/`user`) are stored in `authorized_users.role`.

## Running Reports (CLI)

```bash
python scripts/report.py              # All reports
python scripts/report.py active-users # Active users (7 days)
python scripts/report.py tickers      # Most analyzed tickers
python scripts/report.py interest     # Expressed interest (unregistered attempts)
python scripts/report.py logins       # Login frequency
```

Requires `SUPABASE_URL` and `SUPABASE_KEY` env vars (or `.env` file).

Environment variables for production:
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_KEY` — Supabase anon/public key
- `SKIP_AUTH` — Set to `1` to bypass auth in development
- `DASH_DEBUG` — Set to `1` for hot reload
- `PORT` — Server port (default 8050)

## Key Directories

```
algo-cus/
├── config.py                  Central configuration (tickers, slippage, commission, paths)
├── backtest/
│   ├── engine.py              Backtest class + standalone calculate_metrics()
│   ├── walk_forward.py        WalkForwardEngine (rolling/anchored, grid search)
│   └── bias_guards.py         Lookahead detection, parameter stability, benchmarks
├── data/
│   ├── sample_data.py         Synthetic data generator (deterministic, seed=42)
│   ├── market_data.py         MarketDataProvider (yfinance + parquet caching)
│   ├── fred_data.py           FRED macro data stub (Phase 5)
│   └── cache/                 Parquet cache (gitignored)
├── strategies/
│   ├── base.py                Strategy ABC (data_requirement, required_columns, copy())
│   ├── registry.py            @register decorator, filtering by data needs
│   ├── moving_average_crossover.py
│   ├── rsi_strategy.py
│   └── bollinger_bands.py
├── visualization/
│   ├── charts.py              Candlestick, signals, portfolio comparison, drawdown
│   └── walk_forward.py        Walk-forward split timeline, in-vs-out-sample, sensitivity
├── dashboard/
│   ├── app.py                 App init, layout shell, entry point (85 lines)
│   ├── middleware.py          WSGI auth middleware + login page
│   ├── charts.py              Dark-themed chart builders
│   ├── layouts.py             Views, metric tiles, reports
│   ├── callbacks.py           Analyze, render, navigation
│   ├── serialization.py       JSON round-trip for dcc.Store
│   ├── analysis.py            Data fetch → strategies → backtest orchestration
│   ├── auth.py                Supabase Google OAuth (PKCE) + invitation codes
│   ├── telemetry.py           Fire-and-forget usage logging
│   ├── reporting.py           Shared query functions for admin reports
│   ├── theme.py               Dark color palette, Plotly template
│   └── assets/style.css       Trader workstation CSS
├── scripts/
│   └── report.py              CLI reporting tool for usage telemetry
├── sql/migrations/            Supabase SQL migrations (001-004)
├── tests/                     pytest suite (88% coverage target; currently 92%, 156 tests)
├── docs/                      Plan, deployment guide, getting started, telemetry, session notes
└── output/                    Gitignored — HTML charts, coverage reports, paper trade logs
```

## Test Coverage

- **Project target**: 88% overall (no PR should drop below this)
- **Per-module minimum**: 60% — modules below this need a documented justification or a plan to address
- **Per-issue coverage**: When creating issues that add or modify code, include file-level coverage targets in the Acceptance Criteria (e.g., "new `strategies/registry.py` must have 88%+ coverage", "modified files must not drop below current coverage"). Exceptions may be made with a note citing which phase completes the implementation and brings code coverage within defined targets.

## Conventions

- Tests use synthetic data by default (fast, deterministic, seed=42)
- Integration tests hitting external APIs are marked `@pytest.mark.integration`
- Slippage defaults to 0.3% (manual execution estimate), configurable in `config.py`
- Cache files go in `data/cache/` (gitignored, parquet format)
- Supabase for auth, invitation codes, usage telemetry, and reporting; no other database
- Dashboard chart builders live in `dashboard/charts.py` and use `dashboard/theme.py` for dark styling
- All `visualization/*.py` charts remain standalone (return `go.Figure`) — the dashboard composes them
- New strategies register via `@register` decorator and appear in the dashboard automatically

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)
