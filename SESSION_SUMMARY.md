# Session Summary — Trading Algorithm Innovation

**Date**: 2026-03-26
**Branch**: `claude/trading-algorithm-innovation-llYOL`
**Model**: Claude Opus 4.6 (1M context)

---

## What We Discussed

### Starting Point
The user asked: "If trading algorithms are well known, how do people innovate in this space?" This led to a discussion covering six areas of innovation: signal combination/ensembles, alternative data, adaptive parameters, execution/microstructure, risk management, and ML for non-linear patterns.

### User Constraints Established
- **Data**: Free, publicly accessible APIs only (no budget for premium data)
- **Execution**: Manual trade entry (system is a recommendation engine, not auto-trader)
- **Purpose**: Learning about markets and algorithmic trading
- **Validation**: Must verify recommendation quality and correctness
- **Visualization**: First-class concern — user is a visual learner and data enthusiast
- **Testing**: Automated tests with coverage reporting from the start

### Ticker Universe
AMZN, GOOG, JPM, MSFT — configurable in `config.py`

### Slippage Decision
0.3% per trade on top of 0.1% commission. Rationale: reasonable for manually-entered orders on liquid large-caps. Configurable in `config.py`.

---

## Key Discussions and Decisions

### Web App Architecture
We discussed turning the project into a deployed web app. Key decisions:

1. **UX Pattern: Progressive Disclosure** — Start with a summary (metrics + price chart + portfolio comparison), then drill down into strategy detail (signals, drawdown, walk-forward). Chosen over tabbed dashboard, single scrolling report, and configurable grid.

2. **Deployment: Render** — Chosen over Vercel because Dash is a Python server-side framework requiring a long-running process. Vercel is optimized for serverless/Node.js. Cost: free tier with optional $7/month for always-on.

3. **Auth: Supabase** — Google OAuth + invitation codes. Chosen over Auth0, Firebase, and custom Flask auth. Supabase gives us auth + PostgreSQL in one free service. Invitation code flow: sign in with Google → if first login, enter code → code consumed → access granted.

4. **Data Fetching: On-demand** — Fetch from yfinance when user clicks "Analyze" (2-5s wait). Chosen over daily cache and hybrid approaches for simplicity. See DEPLOYMENT.md for progressive caching roadmap.

5. **Theme: Dark Trader Workstation** — Deep navy background (#0a0e17), cyan primary accent (#00d4ff), green buy / red sell signals, JetBrains Mono for data, glassmorphic panels.

### yfinance Rate Limits
No official documented limits (~2,000 requests/hour per IP). One request per analysis. Not a concern for our use case.

### Deployment Scaling Roadmap
Created a 5-stage progressive scaling plan (see DEPLOYMENT.md):
- Stage 1: Free (Render + Supabase + UptimeRobot to avoid cold starts)
- Stage 2: $7/month (always-on + in-memory cache)
- Stage 3: $14/month (Supabase DB cache + background refresh)
- Stage 4: ~$30/month (Redis + more compute)
- Stage 5: ~$40/month (separated React frontend + Python API)

### GitHub Default Branch
Was incorrectly set to `claude/trading-algorithm-basics-wtmEM`. User changed it back to `main` manually.

---

## 6-Phase Plan (see PLAN.md for full details)

| Phase | What | Status |
|-------|------|--------|
| 1 | Real market data (yfinance) + interactive plotly charts | Done |
| 2 | Walk-forward backtesting + bias guards | Done |
| Web | Dashboard with dark theme, auth, deployment config | Done |
| 3 | Ensemble framework + regime detection | Not started |
| 4 | Recommendation engine + paper trading | Not started |
| 5 | FRED macro data integration | Not started |

**Review checkpoints**: After 1-2+Web (now), after 3, after 4-5.

---

## What Was Built

### Phase 1 — Real Market Data + Core Visualization

| File | What It Does |
|------|-------------|
| `config.py` | Central config: tickers, slippage (0.3%), commission (0.1%), paths |
| `data/market_data.py` | `MarketDataProvider` wrapping yfinance with parquet caching in `data/cache/`. `get_data("AMZN")` or `get_data("synthetic")` |
| `data/fred_data.py` | Stub for Phase 5 — interface only, raises `NotImplementedError` |
| `visualization/charts.py` | Plotly charts: `plot_candlestick`, `plot_strategy_signals`, `plot_portfolio_comparison`, `plot_drawdown`, `plot_metrics_table`. All return `go.Figure` |
| `strategies/base.py` | Extended with `get_params()`, `set_params()`, `confidence()` |
| All 3 strategies | Updated with `get_params()`/`set_params()` implementations |
| `examples/run_backtest.py` | Accepts `--ticker AMZN GOOG` CLI arg, generates interactive HTML charts |

### Phase 2 — Walk-Forward Backtesting + Bias Guards

| File | What It Does |
|------|-------------|
| `backtest/engine.py` | Refactored: extracted `calculate_metrics()` as standalone function, added configurable `slippage`, added `start_date`/`end_date` slicing |
| `backtest/walk_forward.py` | `WalkForwardEngine` with rolling/anchored windows, `gap_days`, grid-search optimization. `WalkForwardResult` with `degradation_ratio` |
| `backtest/bias_guards.py` | `detect_lookahead_bias()`, `parameter_stability_test()`, `benchmark_buy_and_hold()`, `benchmark_random()` |
| `visualization/walk_forward.py` | `plot_walk_forward_splits`, `plot_in_vs_out_sample`, `plot_parameter_sensitivity`, `plot_degradation_summary` |

### Web Dashboard — AlgoStation

| File | What It Does |
|------|-------------|
| `dashboard/app.py` | Main Dash app with progressive disclosure UX (summary → strategy drill-down) |
| `dashboard/auth.py` | Supabase Google OAuth + invitation code validation |
| `dashboard/theme.py` | Dark color palette, custom plotly `trader_dark` template, CSS style constants |
| `dashboard/assets/style.css` | Full trader workstation CSS: dark theme, custom scrollbars, strategy cards, loading spinners |
| `dashboard/analysis.py` | Orchestrates data fetch → strategies → backtests → walk-forward |
| `Procfile` | Render deployment start command |
| `render.yaml` | Render service configuration (env vars, Python version) |

### Testing
- 75 tests passing, 88% coverage
- `pytest-cov` with HTML reports in `output/coverage/`
- Integration tests marked `@pytest.mark.integration` (require network)
- All unit tests use synthetic data (deterministic, seed=42)

### Project Artifacts
- `PLAN.md` — Full 6-phase implementation plan
- `CLAUDE.md` — Project context for future Claude sessions
- `GETTING_STARTED.md` — Step-by-step validation guide with visual checklists
- `SESSION_SUMMARY.md` — This document
- `DEPLOYMENT.md` — Progressive 5-stage deployment scaling roadmap
- `pyproject.toml` — pytest + coverage configuration

---

## Key Design Decisions and Rationale

1. **DataFrame contract is sacred**: All data flows as `Date, Open, High, Low, Close, Volume`. Strategies add `Signal` (1/−1/0). New data sources or strategies require zero changes to the engine.

2. **`calculate_metrics()` is standalone**: Extracted from the `Backtest` class so the walk-forward engine can reuse it. Don't fold it back in.

3. **Grid search, not Bayesian optimization**: For parameter tuning. Transparent and educational.

4. **Degradation ratio as the key overfitting metric**: `OOS Sharpe / IS Sharpe`. Close to 1.0 = generalizes well. Near 0 = overfit.

5. **`gap_days` in walk-forward**: Skips N days between train and test sets to prevent information leakage. Default 5 days.

6. **Visualization returns `go.Figure`**: Composable — works in Jupyter, as HTML, or in the Dash dashboard.

7. **Parquet caching for market data**: Avoids yfinance rate limits. Cached in `data/cache/` (gitignored).

8. **Slippage modeled separately from commission**: Both configurable. Combined as "friction" in the engine.

9. **Dashboard chart builders are separate from `visualization/`**: `dashboard/app.py` has its own dark-themed chart builders that use the `trader_dark` plotly template. The `visualization/*.py` modules remain standalone and composable for CLI/Jupyter use.

10. **Auth bypass for development**: `SKIP_AUTH=1` env var bypasses Supabase entirely. Auth module is only imported when `SKIP_AUTH` is not set.

---

## Environment Notes

- **yfinance installation**: The `multitasking` dependency has a build issue with modern setuptools. Desktop environments with a proper venv should install cleanly.

- **Default branch**: Was set to `claude/trading-algorithm-basics-wtmEM`. User changed it back to `main`.

---

## Next Steps

When resuming, start Phase 3 (Ensemble Framework + Regime Detection):
1. `strategies/regime_detector.py` — ADX, volatility ratio, Hurst exponent
2. `strategies/ensemble.py` — Weighted vote based on regime affinity
3. `visualization/regime.py` — Regime-colored price chart, attribution, correlation
4. Add regime/ensemble views to the dashboard
5. Tests for all new modules
6. Commit, push, review checkpoint
