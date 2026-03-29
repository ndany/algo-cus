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

4. **Data Fetching: On-demand** — Fetch from yfinance when user clicks "Analyze" (2-5s wait). Chosen over daily cache and hybrid approaches for simplicity. See `docs/DEPLOYMENT.md` for progressive caching roadmap.

5. **Theme: Dark Trader Workstation** — Deep navy background (#0a0e17), cyan primary accent (#00d4ff), green buy / red sell signals, JetBrains Mono for data, glassmorphic panels.

### yfinance Rate Limits
No official documented limits (~2,000 requests/hour per IP). One request per analysis. Not a concern for our use case.

### Deployment Scaling Roadmap
Created a 5-stage progressive scaling plan (see `docs/DEPLOYMENT.md`):
- Stage 1: Free (Render + Supabase + UptimeRobot to avoid cold starts)
- Stage 2: $7/month (always-on + in-memory cache)
- Stage 3: $14/month (Supabase DB cache + background refresh)
- Stage 4: ~$30/month (Redis + more compute)
- Stage 5: ~$40/month (separated React frontend + Python API)

### GitHub Default Branch
Was incorrectly set to `claude/trading-algorithm-basics-wtmEM`. User changed it back to `main` manually.

---

## 6-Phase Plan (see `docs/PLAN.md` for full details)

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
- `README.md` — Project landing page (root)
- `CLAUDE.md` — Project context for future Claude sessions (root)
- `docs/PLAN.md` — Full implementation plan with phase status
- `docs/GETTING_STARTED.md` — Step-by-step validation guide with visual checklists
- `docs/DEPLOYMENT.md` — Progressive 5-stage deployment scaling roadmap
- `docs/SESSION_SUMMARY.md` — This document
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

When resuming, start with Pre-Phase 3 refactors (#29-#31), then Phase 3.
See updated `docs/PLAN.md` for full sequence and dependency graph.

---

# Session 2 — Architecture Review, Retrospective Issues, and LBO Modeling

**Date**: 2026-03-29
**Branch**: `claude/retrospective-issues-AmFsi`
**Model**: Claude Opus 4.6 (1M context)

---

## What We Did

### 1. Retrospective Issue Backlog

Created 26 GitHub issues (#3-#28) to capture all planned and completed work as a formal backlog. Each issue has testable acceptance criteria (checkboxes). Issues are grouped by phase using GitHub labels:
- **Phase 1: Real Market Data** — #3-#7 (all closed, AC verified)
- **Phase 2: Walk-Forward + Bias Guards** — #8-#11 (all closed, AC verified)
- **Web Dashboard** — #12-#17 (all closed, AC verified)
- **Phase 3: Ensemble + Regime** — #18-#21 (open, backlog)
- **Phase 4: Recommendations + Paper Trading** — #22-#25 (open, backlog)
- **Phase 5: FRED Macro Data** — #26-#28 (open, backlog)

Closed issues had all acceptance criteria verified against the codebase before closing. Checkbox status updated to checked on all closed issues.

Note: GitHub milestones could not be created via available MCP tools — labels used as grouping mechanism instead.

### 2. Architecture Review

Conducted a thorough review of the codebase design. Key findings:

**Strengths:**
- Clean DataFrame contract (`Date, Open, High, Low, Close, Volume` + `Signal`) — the backbone of composability
- Strategy pattern is minimal and well-executed (ABC, `get_params()`/`set_params()`)
- Standalone `calculate_metrics()` extraction was the right call
- Composable `go.Figure` visualization factories
- Lookahead bias detection via truncation comparison
- Auth at WSGI layer, not Dash callbacks

**Weaknesses identified:**
1. `dashboard/app.py` is an 807-line monolith (layout + charts + callbacks + auth + serialization)
2. Strategy mutation during optimization (`set_params()` on shared instance, save/restore pattern x3)
3. `analysis.py` hardcodes strategy list — no registry or discovery
4. Row-by-row `iterrows()` backtest loop (slow for grid search)
5. Fragile win rate calculation (paired-index assumption)
6. No position/portfolio abstraction (all-in or all-out only)
7. Brittle JSON serialization with inline `WFProxy` hack in dashboard
8. Config as module-level constants (not injectable for testing)
9. No signal validation (strategies could return invalid values)
10. No cache TTL (stale data served silently)

### 3. LBO Modeling Decision

A trading expert recommended including LBO (Leveraged Buyout) modeling. Key decisions:

- **Scope**: Start with a screening heuristic (implied equity IRR as buy signal), designed so a future subclass can extend to a full LBO model (multi-tranche debt, cash flow projections, sensitivity tables)
- **Data**: Requires financial statement data (EBITDA, debt, capex, enterprise value) — fundamentally different from OHLCV
- **Data source**: Free APIs first (yfinance fundamentals, SEC EDGAR); interface supports swapping to paid providers later
- **Architecture impact**: Drives the need for `DataProvider` ABC, `DataEnricher` (multi-frequency merge), and `required_columns` on strategy base class

### 4. Architectural Refactor Issues

Created 14 additional issues (#29-#42) capturing all architectural recommendations, prioritized by phase:

**Pre-Phase 3 Refactors** (blockers):
- #29: Split dashboard monolith into focused modules
- #30: Strategy registry with auto-discovery + `data_requirement` metadata
- #31: Immutable strategy optimization (copy-on-optimize)

**Phase 3 Additions:**
- #32: Data provider abstraction + enrichment layer
- #33: Value strategy category
- #34: LBO screening strategy (extensible to full model)
- #35: Visualization overlays (MA curves, return comparison)
- #36: Signal validation

**Phase 4:**
- #37: Domain model for analysis results (dataclasses replacing flat dicts)
- #38: Position and portfolio abstraction
- #39: Fix win rate calculation with trade-ID matching

**Phase 5 / As-Needed:**
- #40: Vectorize backtest loop
- #41: Cache TTL for data providers
- #42: Redesign dashboard UI layout

### 5. Plan Updates

Updated `docs/PLAN.md`:
- Added "Pre-Phase 3: Architecture Refactors" section
- Expanded Phase 3 to include data abstraction, value strategies, LBO screening
- Expanded Phase 4 to include domain model, position management, win rate fix
- Updated dependency graph with new phase
- Updated constraints (free APIs to start, paid later)
- Added known risks for fundamental data availability and LBO model sensitivity
- Updated final directory structure with all new files

---

## Key Design Decisions (This Session)

11. **DataProvider ABC**: All data sources (OHLCV, fundamentals, FRED) will share a common interface with `fetch()` and `data_contract()`. `DataEnricher` merges multi-frequency data via forward-fill.

12. **Strategy declares its data needs**: `data_requirement` and `required_columns` properties on the base class. OHLCV-only is the default (backward compatible). The system filters strategies by available data.

13. **LBO as screening heuristic first**: Start simple (entry multiple → debt capacity → implied IRR → signal). Design for subclassing into a full model later. Don't build the full model until the data infrastructure and simpler value strategies are proven.

14. **Pre-Phase 3 refactors are prerequisites**: Dashboard split, strategy registry, and immutable optimization must happen before Phase 3 adds complexity. They're small refactors with high leverage.

15. **UI layout redesign deferred to post-Phase 3**: The current progressive disclosure works for 3 strategies. Wait until regime, ensemble, value, and LBO content exists before redesigning.

---

## Next Steps

Start with Pre-Phase 3 refactors:
1. #29: Split `dashboard/app.py` into charts, layouts, callbacks, serialization
2. #30: Strategy registry + `data_requirement`/`required_columns` on base class
3. #31: `copy()`/`with_params()` for immutable optimization

Then proceed to Phase 3 (see updated `docs/PLAN.md` for full sequence).
