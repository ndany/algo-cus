# Trading Algorithm Innovation - Implementation Plan

## Overview

Evolve this educational trading algorithm project into a full recommendation engine with:
- Real market data (free APIs)
- Honest validation (walk-forward backtesting)
- Intelligent strategy combination (ensemble + regime detection)
- Explainable recommendations with paper trading
- Rich interactive visualization throughout

## Constraints

- **Data**: Free APIs to start (yfinance, FRED, SEC EDGAR); paid providers (IEX Cloud, Intrinio) may be explored later for additional coverage
- **Execution**: Manual (system is a recommendation engine, not auto-trader)
- **Purpose**: Learning about markets and algorithmic trading
- **Validation**: Must be able to verify recommendation quality and correctness
- **Visualization**: First-class concern throughout, not bolted on at the end

## Configuration

| Parameter | Default | Notes |
|-----------|---------|-------|
| Tickers | AMZN, GOOG, JPM, MSFT | Configurable list in `config.py` |
| Commission | 0.1% | Per trade |
| Slippage | 0.3% | Manual execution estimate |
| Initial Capital | $10,000 | Per backtest |

---

## Phase 1: Real Market Data + Core Visualization — DONE

**Goal**: Replace synthetic data with real yfinance data; establish plotly-based interactive charts.

### New Files
- `config.py` — Central configuration (tickers, slippage, paths)
- `data/__init__.py` — Package exports
- `data/market_data.py` — `MarketDataProvider` wrapping yfinance
  - Local parquet cache in `data/cache/` (gitignored)
  - NaN handling, gap detection, validation
  - Output matches existing DataFrame contract: `Date, Open, High, Low, Close, Volume`
- `data/fred_data.py` — Stub for Phase 5 (interface only)
- `visualization/__init__.py` — Package exports
- `visualization/charts.py` — Plotly interactive charts
  - Candlestick + volume
  - Strategy signal overlays (buy/sell markers)
  - Multi-strategy equity curve comparison
  - All functions return `plotly.Figure` (dashboard, Jupyter, or HTML)

### Modified Files
- `requirements.txt` — Add yfinance, plotly, dash, pytest, pytest-cov
- `.gitignore` — Add data/cache/, output/, .pytest_cache/
- `strategies/base.py` — Add `get_params()`, `set_params()`, `confidence()`
- All 3 strategy files — Implement `get_params()`/`set_params()`
- `examples/run_backtest.py` — Accept `--ticker` arg, use interactive charts

### Design Decisions
- DataFrame column contract (`Date, Open, High, Low, Close, Volume`) is sacred — zero changes to existing strategy/engine interfaces
- Parquet cache avoids rate limits and enables offline development
- Synthetic data remains as fallback for testing (deterministic, fast)

---

## Phase 2: Walk-Forward Backtesting + Bias Guards — DONE

**Goal**: Honest validation framework that prevents overfitting.

### New Files
- `backtest/walk_forward.py` — `WalkForwardEngine`
  - Sequential train/test splits preserving time order
  - Configurable: `n_splits`, `train_ratio`, `gap_days`
  - `WalkForwardResult` with per-fold metrics
  - `degradation_ratio` = out-of-sample / in-sample Sharpe (measures overfitting)
- `backtest/bias_guards.py`
  - Lookahead bias detection
  - Parameter stability testing
  - Buy-and-hold benchmark comparison
- `visualization/walk_forward.py`
  - Train/test window timeline on price chart
  - In-sample vs out-of-sample bar charts per fold
  - Parameter sensitivity heatmap

### Modified Files
- `backtest/engine.py`
  - Extract `calculate_metrics()` as standalone function
  - Add `start_date`/`end_date` slicing support
  - Add configurable `slippage` parameter (default 0.3%)

### Design Decisions
- Grid search for parameter optimization (transparent, not opaque ML)
- `gap_days` prevents information leakage at train/test boundaries
- `degradation_ratio` teaches overfitting visually

---

## Pre-Phase 3: Architecture Refactors

**Goal**: Address architectural debt identified in the architecture review before adding complexity. These are prerequisites for Phases 3-5.

### Dashboard Decomposition (#29)
- Split `dashboard/app.py` (807 lines) into focused modules:
  - `dashboard/charts.py` — dark-themed chart builders (compose `visualization/*.py` + `apply_dark_theme()`)
  - `dashboard/layouts.py` — summary view, detail view, empty state, metric tiles
  - `dashboard/callbacks.py` — analyze, render, navigation callbacks
  - `dashboard/serialization.py` — JSON round-trip logic
  - `dashboard/app.py` — app init, middleware wiring, entry point only (~100 lines)

### Strategy Registry (#30)
- Replace hardcoded `get_strategies()` with a registry pattern in `strategies/__init__.py`
- Add `data_requirement` and `required_columns` properties to `Strategy` base class
- Strategies declare what data they need; the system filters to compatible strategies
- Default: `OHLCV_ONLY` — existing strategies work unchanged

### Immutable Optimization (#31)
- Add `copy()` or `with_params()` to `Strategy` base class
- Walk-forward and bias guards use copies during grid search instead of mutating shared state
- Eliminates 3 save/restore boilerplate blocks and prevents concurrency bugs

### Test Coverage (#45)
- Push unit test coverage to 90%+ by covering edge cases in `backtest/bias_guards.py` and `backtest/walk_forward.py`

---

## Phase 3: Ensemble Framework + Regime Detection + New Strategy Types

**Goal**: Combine strategies intelligently based on market conditions. Expand beyond momentum-based strategies to include value models and LBO screening. Establish the data abstraction layer for multi-source data.

### Data Provider Abstraction (#32)
- `data/base_provider.py` — `DataProvider` ABC with `fetch()` and `data_contract()`
- `MarketDataProvider` inherits from `DataProvider` (backward compatible)
- `data/enricher.py` — `DataEnricher` merges multi-frequency data (daily OHLCV + quarterly fundamentals via forward-fill)
- `data/fundamental_provider.py` — stub declaring the fundamental data contract (PERatio, EBITDA, DebtToEquity, TotalDebt, FreeCashFlow, EnterpriseValue, MarketCap)
- Start with free APIs (yfinance fundamentals, SEC EDGAR); interface supports swapping to paid providers later

### New Strategy Types
- `strategies/regime_detector.py` — Market regime classification (#18)
  - Regimes: `TRENDING_UP`, `TRENDING_DOWN`, `MEAN_REVERTING`, `HIGH_VOLATILITY`
  - Methods: ADX (trend strength), volatility ratio, Hurst exponent
- `strategies/ensemble.py` — `EnsembleStrategy(Strategy)` (#19)
  - Weighted vote based on current regime and strategy affinity
  - `SimpleVoteEnsemble` for equal-weight majority vote
- `strategies/value_strategy.py` — Value-based strategy (#33)
  - P/E ratio screen or composite value score
  - Declares `required_columns` for fundamental data
  - Produces signals: undervalued=buy, overvalued=sell
- `strategies/lbo_strategy.py` — LBO screening strategy (#34)
  - Screening heuristic: entry EV/EBITDA, debt capacity, implied equity IRR
  - Signal: IRR > threshold = undervalued = buy
  - Designed for subclassing into a full LBO model (multi-tranche debt, cash flow projections, sensitivity tables)

### New Visualizations
- `visualization/regime.py` (#20)
  - Price chart with regime-colored background
  - Ensemble attribution (stacked area)
  - Strategy correlation heatmap
- `visualization/overlays.py` (#35)
  - MA curves overlaid on candlestick chart
  - Model return vs market return normalized comparison

### Signal Validation (#36)
- Automatic validation that Signal column only contains {-1, 0, 1}
- Catches bugs in new strategy implementations early

### Dashboard Additions (#21)
- Regime overlay on price chart
- Ensemble attribution view
- Strategy cards for value/LBO strategies

---

## Phase 4: Recommendation & Validation Layer

**Goal**: Explainable, actionable recommendations with paper trading. Introduce domain model and position management.

### Architecture Improvements
- `backtest/models.py` — Domain model dataclasses (#37)
  - `AnalysisResult`, `StrategyResult`, `BenchmarkResult`
  - Replace flat dicts in `run_analysis()` with typed, serializable objects
  - Carries regime, recommendation, and confidence fields (nullable until populated)
- `backtest/portfolio.py` — Position and portfolio abstraction (#38)
  - `Position` (entry price, size, P&L, trade ID)
  - `Portfolio` (multiple positions, allocation rules)
  - Confidence-based position sizing
- Fix win rate calculation with trade-ID matching (#39)

### New Files
- `recommendations/engine.py` — `RecommendationEngine` (#22)
  - Confidence score (0-1): strategy agreement + regime clarity + historical accuracy
  - Plain-English reasoning for every recommendation
  - Risk level and suggested position size
- `recommendations/paper_trading.py` — `PaperTradingLog` (#24)
  - Log recommendations, record outcomes
  - Compare paper results vs backtest predictions
  - JSON persistence in `output/paper_trades.json`
- `recommendations/explainability.py` (#23)
  - Per-signal breakdown: indicator value, threshold, distance, historical context
- `visualization/recommendations.py` (#25)
  - Confidence gauge, reasoning panel
  - Paper trade timeline with P&L
  - Confidence calibration plot
  - Backtest-vs-paper overlay

---

## Phase 5: FRED Macro Data Integration

**Goal**: Add economic context to regime detection and recommendations.

### Modified Files
- `data/fred_data.py` — Complete implementation (#26)
  - Series: Fed Funds rate, yield curve, VIX, unemployment, CPI
  - Inherits from `DataProvider` ABC; integrates with `DataEnricher`
  - Forward-fill to align with daily price data
- `strategies/regime_detector.py` — Add `detect_with_macro()` (#27)
  - Inverted yield curve = risk-off
  - VIX spike = high-volatility regime
- `visualization/macro.py` (#28)
  - Macro indicator dashboard
  - Regime-macro correlation chart

### Performance & Infrastructure
- Vectorize backtest loop (#40) — replace `iterrows()` with numpy when grid search performance becomes a bottleneck
- Add cache TTL to data providers (#41) — especially important for multi-frequency FRED data

---

## Post-Phase 3

**Goal**: Improvements and tech debt to address after Phase 3 is complete.

- Redesign dashboard UI layout (#42) — wait until Phase 3 content exists to inform the design

---

## Web Dashboard — DONE (built early, before Phase 3)

**Goal**: Deployable web app with dark trader workstation UX.

### What Was Built
- `dashboard/app.py` — Dash app with progressive disclosure (summary → strategy drill-down)
- `dashboard/auth.py` — Supabase Google OAuth (PKCE) + invitation codes
- `dashboard/telemetry.py` — Fire-and-forget usage logging to `usage_log` and `access_attempts` tables
- `dashboard/reporting.py` — Shared query functions for admin reports (used by dashboard + CLI)
- `dashboard/theme.py` — Dark color palette, custom plotly `trader_dark` template
- `dashboard/assets/style.css` — Trader workstation CSS (JetBrains Mono, cyan/green/red accents)
- `dashboard/analysis.py` — Orchestrates data fetch → strategies → backtests → walk-forward
- `scripts/report.py` — CLI tool for querying usage telemetry from desktop
- `sql/migrations/` — Versioned SQL migrations (001-004: auth, telemetry, roles, reporting functions)
- `Procfile` + `render.yaml` — Render deployment config

### Auth
- Google sign-in always required; invitation code only for first-time registration
- Auth handled at WSGI middleware layer (plain HTML login page, no Dash involvement)
- User roles (admin/user) in `authorized_users` table — controls access to reports

### UX Flow
1. Enter ticker → ANALYZE
2. Summary: metrics tiles, candlestick, portfolio comparison, strategy cards
3. Click strategy → detail: signals, drawdown, walk-forward
4. Back to summary
5. Reports (admin only): Active Users, Top Tickers, Expressed Interest, Login Frequency

### Telemetry
- Logs: `login`, `analyze`, `analyze_error` to `usage_log`
- Tracks: `no_code`, `invalid_code`, `auth_failed` to `access_attempts` (expressed interest)
- See `docs/TELEMETRY.md` for details

### Deployment
- Render free tier (with UptimeRobot to avoid cold starts)
- Supabase for auth, invitation codes, telemetry, and reporting
- See `docs/DEPLOYMENT.md` for progressive scaling roadmap (5 stages, free → $40/month)

### Future Dashboard Additions (as phases complete)
- Phase 3: Regime overlay on price chart, ensemble attribution view
- Phase 4: Recommendations tab, paper trading log
- Phase 5: Macro context panel on summary view

---

## Dependency Graph

```
Phase 1 (Data + Viz + Tests)       ✅ DONE
  |
  v
Phase 2 (Walk-Forward)             ✅ DONE
  |
  v
Web Dashboard                      ✅ DONE (built early)
  |
  v
Pre-Phase 3 (Refactors)           ← current
  |  - Dashboard decomposition (#29)
  |  - Strategy registry (#30)
  |  - Immutable optimization (#31)
  |  - Test coverage to 90% (#45)
  |
  v
Phase 3 (Ensemble + Regime + Value/LBO + Data Abstraction)
  |  - Data provider abstraction (#32)
  |  - Value strategy (#33), LBO screening (#34)
  |  - Regime (#18), Ensemble (#19)
  |  - Viz overlays (#35), Signal validation (#36)
  |
  +------> Phase 5 (FRED Macro + Performance)
  |              |
  v              v
Phase 4 (Recommendations + Architecture)
  |  - Domain model (#37)
  |  - Position/portfolio (#38)
  |  - Win rate fix (#39)
  |  - Recommendations (#22-#25)
  |
  v
Post-Phase 3
  |  - UI layout redesign (#42)
```

## Review Checkpoints

1. After Phases 1-2 + Web Dashboard (foundation) — **done**
2. After Pre-Phase 3 refactors (architecture readiness) ← **current**
3. After Phase 3 (core innovation + new strategy types)
4. After Phases 4-5 (recommendations + macro)

## Testing Strategy

- `pytest` with `pytest-cov` for coverage reporting
- Tests use synthetic data by default (fast, deterministic)
- Integration tests for yfinance/FRED marked with `@pytest.mark.integration`
- Coverage reports in `output/coverage/`
- **Project target**: 88% overall — no PR should drop below this
- **Per-module minimum**: 60% — modules below need documented justification
- **Per-issue coverage**: issues that add/modify code include file-level coverage targets in ACs
- Tests must never write to production databases — mock all external service clients

## Final Directory Structure

```
algo-cus/
  config.py              Central configuration
  Procfile               Render deployment start command
  render.yaml            Render service configuration
  backtest/
    engine.py            Backtest class + standalone calculate_metrics()
    walk_forward.py      WalkForwardEngine
    bias_guards.py       Lookahead detection, parameter stability, benchmarks
    portfolio.py         Position + Portfolio abstractions (Phase 4)
    models.py            AnalysisResult, StrategyResult dataclasses (Phase 4)
  data/
    base_provider.py     DataProvider ABC (Phase 3)
    sample_data.py       Synthetic data generator
    market_data.py       MarketDataProvider (yfinance + caching)
    fundamental_provider.py  FundamentalDataProvider stub (Phase 3)
    enricher.py          DataEnricher — multi-frequency merge (Phase 3)
    fred_data.py         FRED macro data (Phase 5)
    cache/               Parquet cache (gitignored)
  strategies/
    base.py              Strategy ABC (with registry, data_requirement, copy())
    moving_average_crossover.py
    rsi_strategy.py
    bollinger_bands.py
    value_strategy.py    Value-based strategy (Phase 3)
    lbo_strategy.py      LBO screening strategy (Phase 3)
    regime_detector.py   Market regime classification (Phase 3)
    ensemble.py          Ensemble strategy (Phase 3)
  recommendations/       (Phase 4)
    engine.py            RecommendationEngine
    paper_trading.py     PaperTradingLog
    explainability.py    Per-signal breakdown
  visualization/
    charts.py            Core Plotly charts
    overlays.py          MA overlay, return comparison (Phase 3)
    walk_forward.py      Walk-forward visualizations
    regime.py            Regime + ensemble visualizations (Phase 3)
    recommendations.py   Recommendation visualizations (Phase 4)
    macro.py             Macro indicator charts (Phase 5)
  dashboard/
    app.py               App init, WSGI auth middleware, entry point
    charts.py            Dark-themed chart builders (Phase: Pre-Phase 3 #29)
    layouts.py           Summary view, detail view, metric tiles (Phase: Pre-Phase 3 #29)
    callbacks.py         Dash callbacks (Phase: Pre-Phase 3 #29)
    serialization.py     JSON round-trip for dcc.Store (Phase: Pre-Phase 3 #29)
    auth.py              Supabase Google OAuth (PKCE) + invitation codes
    telemetry.py         Fire-and-forget usage logging
    reporting.py         Shared query functions for admin reports
    theme.py             Dark color palette, Plotly template
    analysis.py          Orchestration layer
    assets/style.css     Trader workstation CSS
  scripts/
    report.py            CLI reporting tool for desktop usage queries
    keep-alive.sh        Cron script to prevent Render cold starts
  sql/
    migrations/          Versioned Supabase schema migrations (001-004)
    README.md            Migration instructions
  tests/                 Mirroring each module
  examples/              run_backtest.py, run_recommendation.py
  docs/                  PLAN.md, SESSION_SUMMARY.md, GETTING_STARTED.md, DEPLOYMENT.md, TELEMETRY.md
  output/                (gitignored: HTML charts, paper trade logs, coverage)
```

## Known Risks

1. **yfinance fragility** — scrapes Yahoo Finance, can break. Mitigated by caching + synthetic fallback.
2. **Regime detection lag** — regimes easier to see in hindsight. Use only lagged indicators, visualize delay.
3. **FRED API key** — `fredapi` needs free key. Support env var with CSV fallback.
4. **Slippage realism** — 0.3% is an estimate. Configurable, paper trading will validate.
5. **Fundamental data availability** — free APIs have gaps, especially for smaller companies or international stocks. LBO screening may only work for large/mid-cap US equities initially.
6. **LBO model sensitivity** — screening heuristic is rough (single-point estimate of IRR). Flag confidence level in UI; sensitivity analysis planned for full model extension.
